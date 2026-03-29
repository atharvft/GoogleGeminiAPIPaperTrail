"""
Database module for MongoDB operations.
Handles connection, document storage, and retrieval.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import re
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from bson import ObjectId
from .config import config


class DatabaseManager:
    """Manages MongoDB connections and operations."""
    
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None
    
    @classmethod
    def get_db_connection(cls) -> Database:
        """
        Get or create MongoDB database connection.
        Uses connection pooling for efficiency.
        
        Returns:
            Database: MongoDB database instance
        """
        if cls._client is None:
            cls._client = MongoClient(config.MONGO_URI)
            cls._db = cls._client[config.MONGO_DB_NAME]
            print(f"✓ Connected to MongoDB: {config.MONGO_DB_NAME}")
        
        return cls._db
    
    @classmethod
    def close_connection(cls) -> None:
        """Close MongoDB connection."""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            print("✓ MongoDB connection closed")


def get_collection(collection_name: str) -> Collection:
    """
    Get MongoDB collection by name.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Collection: MongoDB collection instance
    """
    db = DatabaseManager.get_db_connection()
    return db[collection_name]


def save_birth_certificate(
    image_path: str,
    extracted_data: Dict[str, Any],
    confidence_scores: Dict[str, float]
) -> str:
    """
    Save birth certificate data to civil_records_department collection.
    
    Args:
        image_path: Path to uploaded image
        extracted_data: Extracted field values
        confidence_scores: OCR confidence scores for each field
        
    Returns:
        str: Inserted document ID
    """
    collection = get_collection(config.CIVIL_RECORDS_COLLECTION)
    
    document = {
        "department": "civil_records_department",
        "form_type": "birth_certificate",
        "image_path": image_path,
        "extracted_data": extracted_data,
        "confidence_scores": confidence_scores,
        "corrected_data": {},
        "status": "pending_verification",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = collection.insert_one(document)
    form_id = str(result.inserted_id)
    
    # Log the action
    save_audit_log(form_id, "FORM_PROCESSED", {"form_type": "birth_certificate"})
    
    return form_id


def save_residence_certificate(
    image_path: str,
    extracted_data: Dict[str, Any],
    confidence_scores: Dict[str, float]
) -> str:
    """
    Save residence certificate data to citizen_services_department collection.
    
    Args:
        image_path: Path to uploaded image
        extracted_data: Extracted field values
        confidence_scores: OCR confidence scores for each field
        
    Returns:
        str: Inserted document ID
    """
    collection = get_collection(config.CITIZEN_SERVICES_COLLECTION)
    
    document = {
        "department": "citizen_services_department",
        "form_type": "residence_certificate",
        "image_path": image_path,
        "extracted_data": extracted_data,
        "confidence_scores": confidence_scores,
        "corrected_data": {},
        "status": "pending_verification",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = collection.insert_one(document)
    form_id = str(result.inserted_id)
    
    # Log the action
    save_audit_log(form_id, "FORM_PROCESSED", {"form_type": "residence_certificate"})
    
    return form_id


def save_audit_log(form_id: str, action: str, metadata: Optional[Dict] = None) -> str:
    """
    Save audit log entry for traceability.
    
    Args:
        form_id: Form document ID
        action: Action performed
        metadata: Additional metadata
        
    Returns:
        str: Audit log ID
    """
    collection = get_collection(config.AUDIT_LOGS_COLLECTION)
    
    log_entry = {
        "form_id": form_id,
        "action": action,
        "metadata": metadata or {},
        "timestamp": datetime.utcnow()
    }
    
    result = collection.insert_one(log_entry)
    return str(result.inserted_id)


def get_all_forms(limit: int = 100, skip: int = 0) -> List[Dict]:
    """
    Retrieve all processed forms from both departments.
    
    Args:
        limit: Maximum number of documents to return
        skip: Number of documents to skip (for pagination)
        
    Returns:
        List[Dict]: List of form documents
    """
    civil_collection = get_collection(config.CIVIL_RECORDS_COLLECTION)
    citizen_collection = get_collection(config.CITIZEN_SERVICES_COLLECTION)
    
    # Get forms from both collections
    civil_forms = list(civil_collection.find().sort("created_at", -1).skip(skip).limit(limit // 2))
    citizen_forms = list(citizen_collection.find().sort("created_at", -1).skip(skip).limit(limit // 2))
    
    # Combine and convert ObjectId to string
    all_forms = civil_forms + citizen_forms
    for form in all_forms:
        form["_id"] = str(form["_id"])
        form["created_at"] = form["created_at"].isoformat()
        form["updated_at"] = form["updated_at"].isoformat()
    
    return all_forms


def get_form_by_id(form_id: str, department: str) -> Optional[Dict]:
    """
    Retrieve a specific form by ID from a department.
    
    Args:
        form_id: Form document ID
        department: Department collection name
        
    Returns:
        Optional[Dict]: Form document or None
    """
    try:
        collection = get_collection(department)
        form = collection.find_one({"_id": ObjectId(form_id)})
        
        if form:
            form["_id"] = str(form["_id"])
            form["created_at"] = form["created_at"].isoformat()
            form["updated_at"] = form["updated_at"].isoformat()
        
        return form
    except Exception:
        return None


def update_form_verification(
    form_id: str,
    department: str,
    corrected_data: Dict[str, Any]
) -> bool:
    """
    Update form with human-verified corrections.
    
    Args:
        form_id: Form document ID
        department: Department collection name
        corrected_data: Human-verified field values
        
    Returns:
        bool: True if update successful
    """
    try:
        collection = get_collection(department)
        
        result = collection.update_one(
            {"_id": ObjectId(form_id)},
            {
                "$set": {
                    "corrected_data": corrected_data,
                    "status": "verified",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            save_audit_log(form_id, "FORM_VERIFIED", {"corrected_fields": list(corrected_data.keys())})
            return True
        
        return False
    except Exception:
        return False


def _normalize_text(value: Any) -> str:
    """Normalize text for duplicate comparison."""
    if value is None:
        return ""

    normalized = re.sub(r"[^a-z0-9\s]", " ", str(value).strip().lower())
    return " ".join(normalized.split())


def _normalize_date(value: Any) -> str:
    """Normalize common date formats into YYYY-MM-DD where possible."""
    if value is None:
        return ""

    raw_value = str(value).strip()
    if not raw_value:
        return ""

    for fmt in (
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%d/%m/%y", "%d-%m-%y",
    ):
        try:
            parsed = datetime.strptime(raw_value, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return _normalize_text(raw_value)


def _preferred_record_data(form: Dict[str, Any]) -> Dict[str, Any]:
    """Use corrected data when present; otherwise fall back to extracted data."""
    corrected = form.get("corrected_data") or {}
    if corrected:
        return corrected
    return form.get("extracted_data") or {}


def _duplicate_keys_for_form(form_type: str, data: Dict[str, Any]) -> Dict[str, str]:
    """Build normalized duplicate-comparison keys for a form."""
    if form_type == "birth_certificate":
        return {
            "name": _normalize_text(data.get("name")),
            "date": _normalize_date(data.get("date_of_birth")),
        }

    return {
        "name": _normalize_text(data.get("full_name") or data.get("name")),
        "date": _normalize_date(data.get("date") or data.get("date_of_birth")),
    }


def find_potential_duplicates(
    form_type: str,
    corrected_data: Dict[str, Any],
    exclude_form_id: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Find likely duplicate records by matching normalized name and date fields.

    Args:
        form_type: Form type being verified
        corrected_data: Current human-verified field values
        exclude_form_id: Existing draft/form to exclude from results
        limit: Maximum number of duplicate matches to return

    Returns:
        List of matching record summaries
    """
    target_keys = _duplicate_keys_for_form(form_type, corrected_data)
    if not target_keys["name"] or not target_keys["date"]:
        return []

    collections = [
        get_collection(config.CIVIL_RECORDS_COLLECTION),
        get_collection(config.CITIZEN_SERVICES_COLLECTION),
    ]
    matches: List[Dict[str, Any]] = []

    for collection in collections:
        for form in collection.find({"form_type": form_type}).sort("created_at", -1):
            form_id = str(form.get("_id"))
            if exclude_form_id and form_id == exclude_form_id:
                continue

            source_data = _preferred_record_data(form)
            candidate_keys = _duplicate_keys_for_form(form_type, source_data)
            if candidate_keys != target_keys:
                continue

            matches.append({
                "form_id": form_id,
                "department": form.get("department"),
                "form_type": form.get("form_type"),
                "status": form.get("status"),
                "created_at": form.get("created_at").isoformat() if form.get("created_at") else None,
                "matched_name": source_data.get("name") or source_data.get("full_name") or "",
                "matched_date": source_data.get("date_of_birth") or source_data.get("date") or "",
            })

            if len(matches) >= limit:
                return matches

    return matches
