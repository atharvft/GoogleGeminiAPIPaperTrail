"""
Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
from datetime import datetime


class FormUploadResponse(BaseModel):
    """Response model for form upload."""
    success: bool
    message: str
    form_id: Optional[str] = None
    form_type: Optional[str] = None
    department: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    confidence_scores: Optional[Dict[str, float]] = None
    verification_flags: Optional[Dict[str, bool]] = None
    classification_confidence: Optional[float] = None
    ocr_confidence: Optional[float] = None
    ocr_method: Optional[str] = None


class FormVerificationRequest(BaseModel):
    """Request model for form verification."""
    form_id: str = Field(..., description="Form document ID")
    department: str = Field(..., description="Department collection name")
    corrected_data: Dict[str, Any] = Field(..., description="Human-verified field values")
    allow_duplicate: bool = Field(default=False, description="Allow save even when potential duplicates are found")


class DuplicateCheckRequest(BaseModel):
    """Request model for duplicate screening."""
    form_id: str = Field(..., description="Form document ID")
    department: str = Field(..., description="Department collection name")
    corrected_data: Dict[str, Any] = Field(..., description="Current field values to check")


class FormVerificationResponse(BaseModel):
    """Response model for form verification."""
    success: bool
    message: str
    form_id: Optional[str] = None


class FormRecord(BaseModel):
    """Model for form record."""
    id: str = Field(..., alias="_id")
    department: str
    form_type: str
    image_path: str
    extracted_data: Dict[str, Any]
    confidence_scores: Dict[str, float]
    corrected_data: Dict[str, Any]
    status: str
    created_at: str
    updated_at: str
    
    class Config:
        populate_by_name = True


class FormsListResponse(BaseModel):
    """Response model for forms list."""
    success: bool
    total: int
    forms: list[FormRecord]


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    detail: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    database_connected: bool
    upload_folder_exists: bool
