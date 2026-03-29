"""
Verification routes for human correction of OCR results.
Allows frontend to submit verified/corrected form data.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from ..database import update_form_verification, get_form_by_id, find_potential_duplicates
from ..models import DuplicateCheckRequest, FormVerificationRequest, FormVerificationResponse

router = APIRouter(prefix="/api", tags=["verification"])


def _get_duplicate_matches(form_id: str, department: str, corrected_data: Dict[str, Any]):
    """Resolve duplicate matches for a form payload."""
    form = get_form_by_id(form_id, department)

    if not form:
        raise HTTPException(
            status_code=404,
            detail=f"Form not found: {form_id} in department: {department}"
        )

    potential_duplicates = find_potential_duplicates(
        form.get("form_type", ""),
        corrected_data,
        exclude_form_id=form_id
    )

    return form, potential_duplicates


@router.post("/check-duplicates")
async def check_duplicates(request: DuplicateCheckRequest):
    """Check for likely duplicates without saving the form."""
    try:
        form, potential_duplicates = _get_duplicate_matches(
            request.form_id,
            request.department,
            request.corrected_data
        )

        return {
            "success": True,
            "form_type": form.get("form_type"),
            "has_duplicates": bool(potential_duplicates),
            "duplicate_matches": potential_duplicates,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Duplicate check failed: {str(e)}"
        )


@router.post("/verify-form", response_model=FormVerificationResponse)
async def verify_form(request: FormVerificationRequest):
    """
    Submit human-verified corrections for a form.
    
    Updates the form record with corrected data and marks it as verified.
    Creates an audit log entry for traceability.
    
    Args:
        request: Verification request with form_id, department, and corrected_data
        
    Returns:
        FormVerificationResponse: Success status and message
    """
    try:
        _, potential_duplicates = _get_duplicate_matches(
            request.form_id,
            request.department,
            request.corrected_data
        )

        if potential_duplicates and not request.allow_duplicate:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Potential duplicate records found. Please review before creating a new record.",
                    "duplicate_matches": potential_duplicates,
                }
            )
        
        # Update form with corrected data
        success = update_form_verification(
            request.form_id,
            request.department,
            request.corrected_data
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update form verification"
            )
        
        return FormVerificationResponse(
            success=True,
            message="Form verified and updated successfully",
            form_id=request.form_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )


@router.get("/pending-verification")
async def get_pending_verification_forms(limit: int = 50):
    """
    Get list of forms pending human verification.
    
    Returns forms with low confidence scores that need review.
    
    Args:
        limit: Maximum number of forms to return
        
    Returns:
        List of forms pending verification
    """
    try:
        from ..database import get_collection
        from ..config import config
        
        # Query both collections for pending forms
        civil_collection = get_collection(config.CIVIL_RECORDS_COLLECTION)
        citizen_collection = get_collection(config.CITIZEN_SERVICES_COLLECTION)
        
        civil_pending = list(
            civil_collection.find({"status": "pending_verification"})
            .sort("created_at", -1)
            .limit(limit // 2)
        )
        
        citizen_pending = list(
            citizen_collection.find({"status": "pending_verification"})
            .sort("created_at", -1)
            .limit(limit // 2)
        )
        
        # Combine and format results
        all_pending = civil_pending + citizen_pending
        
        for form in all_pending:
            form["_id"] = str(form["_id"])
            form["created_at"] = form["created_at"].isoformat()
            form["updated_at"] = form["updated_at"].isoformat()
        
        return {
            "success": True,
            "total": len(all_pending),
            "forms": all_pending
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch pending forms: {str(e)}"
        )


@router.get("/form/{form_id}")
async def get_form_details(form_id: str, department: str):
    """
    Get detailed information about a specific form.
    
    Args:
        form_id: Form document ID
        department: Department collection name
        
    Returns:
        Form details including extracted and corrected data
    """
    try:
        form = get_form_by_id(form_id, department)
        
        if not form:
            raise HTTPException(
                status_code=404,
                detail=f"Form not found: {form_id}"
            )
        
        return {
            "success": True,
            "form": form
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch form: {str(e)}"
        )
