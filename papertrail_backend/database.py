"""
Database module for MongoDB operations.
Handles connection, document storage, and retrieval.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
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
