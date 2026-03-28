"""
Records routes for querying processed forms.
Provides endpoints to retrieve and search form records.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..database import get_all_forms, get_collection
from ..config import config
from ..models import FormsListResponse

router = APIRouter(prefix="/api", tags=["records"])


@router.get("/forms")
async def get_forms(
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    department: Optional[str] = None,
    form_type: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Retrieve processed forms from both departments.
    
    Supports filtering by department, form_type, and status.
    Includes pagination with limit and skip parameters.
    
    Args:
        limit: Maximum number of forms to return (1-500)
        skip: Number of forms to skip for pagination
        department: Filter by department collection
        form_type: Filter by form type (birth_certificate or residence_certificate)
        status: Filter by status (pending_verification or verified)
        
    Returns:
        List of form records
    """
    try:
        # Build query filter
        query_filter = {}
        
        if form_type:
            query_filter["form_type"] = form_type
        
        if status:
            query_filter["status"] = status
        
        # If department specified, query only that collection
        if department:
            collection = get_collection(department)
            forms = list(
                collection.find(query_filter)
                .sort("created_at", -1)
                .skip(skip)
                .limit(limit)
            )
        else:
            # Query both collections
            civil_collection = get_collection(config.CIVIL_RECORDS_COLLECTION)
            citizen_collection = get_collection(config.CITIZEN_SERVICES_COLLECTION)
            
            civil_forms = list(
                civil_collection.find(query_filter)
                .sort("created_at", -1)
                .skip(skip)
                .limit(limit // 2)
            )
            
            citizen_forms = list(
                citizen_collection.find(query_filter)
                .sort("created_at", -1)
                .skip(skip)
                .limit(limit // 2)
            )
            
            forms = civil_forms + citizen_forms
        
        # Format results
        for form in forms:
            form["_id"] = str(form["_id"])
            form["created_at"] = form["created_at"].isoformat()
            form["updated_at"] = form["updated_at"].isoformat()
        
        return {
            "success": True,
            "total": len(forms),
            "forms": forms,
            "filters": {
                "department": department,
                "form_type": form_type,
                "status": status,
                "limit": limit,
                "skip": skip
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch forms: {str(e)}"
        )


@router.get("/departments/{department}/forms")
async def get_department_forms(
    department: str,
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0)
):
    """
    Get all forms from a specific department.
    
    Args:
        department: Department collection name
        limit: Maximum number of forms to return
        skip: Number of forms to skip
        
    Returns:
        List of forms from the specified department
    """
    try:
        # Validate department
        valid_departments = [
            config.CIVIL_RECORDS_COLLECTION,
            config.CITIZEN_SERVICES_COLLECTION
        ]
        
        if department not in valid_departments:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid department. Must be one of: {', '.join(valid_departments)}"
            )
        
        collection = get_collection(department)
        forms = list(
            collection.find()
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        
        # Format results
        for form in forms:
            form["_id"] = str(form["_id"])
            form["created_at"] = form["created_at"].isoformat()
            form["updated_at"] = form["updated_at"].isoformat()
        
        # Get total count
        total_count = collection.count_documents({})
        
        return {
            "success": True,
            "department": department,
            "total": len(forms),
            "total_in_department": total_count,
            "forms": forms
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch department forms: {str(e)}"
        )


@router.get("/search")
async def search_forms(
    query: str = Query(..., min_length=1),
    field: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200)
):
    """
    Search forms by text query.
    
    Searches across extracted_data and corrected_data fields.
    
    Args:
        query: Search query string
        field: Specific field to search in (optional)
        limit: Maximum number of results
        
    Returns:
        List of matching forms
    """
    try:
        # Build search filter
        if field:
            # Search specific field
            search_filter = {
                "$or": [
                    {f"extracted_data.{field}": {"$regex": query, "$options": "i"}},
                    {f"corrected_data.{field}": {"$regex": query, "$options": "i"}}
                ]
            }
        else:
            # Search all text fields
            search_filter = {
                "$or": [
                    {"extracted_data": {"$regex": query, "$options": "i"}},
                    {"corrected_data": {"$regex": query, "$options": "i"}}
                ]
            }
        
        # Search both collections
        civil_collection = get_collection(config.CIVIL_RECORDS_COLLECTION)
        citizen_collection = get_collection(config.CITIZEN_SERVICES_COLLECTION)
        
        civil_results = list(
            civil_collection.find(search_filter)
            .sort("created_at", -1)
            .limit(limit // 2)
        )
        
        citizen_results = list(
            citizen_collection.find(search_filter)
            .sort("created_at", -1)
            .limit(limit // 2)
        )
        
        results = civil_results + citizen_results
        
        # Format results
        for form in results:
            form["_id"] = str(form["_id"])
            form["created_at"] = form["created_at"].isoformat()
            form["updated_at"] = form["updated_at"].isoformat()
        
        return {
            "success": True,
            "query": query,
            "field": field,
            "total": len(results),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/stats")
async def get_statistics():
    """
    Get overall statistics about processed forms.
    
    Returns:
        Statistics including counts by department, form type, and status
    """
    try:
        civil_collection = get_collection(config.CIVIL_RECORDS_COLLECTION)
        citizen_collection = get_collection(config.CITIZEN_SERVICES_COLLECTION)
        
        # Get counts
        civil_total = civil_collection.count_documents({})
        citizen_total = citizen_collection.count_documents({})
        
        civil_pending = civil_collection.count_documents({"status": "pending_verification"})
        citizen_pending = citizen_collection.count_documents({"status": "pending_verification"})
        
        civil_verified = civil_collection.count_documents({"status": "verified"})
        citizen_verified = citizen_collection.count_documents({"status": "verified"})
        
        return {
            "success": True,
            "statistics": {
                "total_forms": civil_total + citizen_total,
                "by_department": {
                    "civil_records": civil_total,
                    "citizen_services": citizen_total
                },
                "by_status": {
                    "pending_verification": civil_pending + citizen_pending,
                    "verified": civil_verified + citizen_verified
                },
                "by_department_and_status": {
                    "civil_records": {
                        "total": civil_total,
                        "pending": civil_pending,
                        "verified": civil_verified
                    },
                    "citizen_services": {
                        "total": citizen_total,
                        "pending": citizen_pending,
                        "verified": citizen_verified
                    }
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch statistics: {str(e)}"
        )
