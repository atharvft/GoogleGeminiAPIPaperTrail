"""
Routes for auto-generating blank templates and digital form rendering.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from typing import Dict, Any

from ..config import config
from ..template_engine import template_engine
from ..database import DatabaseManager
from bson.objectid import ObjectId

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.post("/auto-create/{form_id}")
async def auto_create_template(form_id: str):
    """
    Takes an existing filled form record, runs the Smart Eraser
    to blank out handwriting, and saves it as the master template.
    """
    db = DatabaseManager.get_db_connection()
    
    # Check both collections
    try:
        obj_id = ObjectId(form_id)
        record = db[config.CIVIL_RECORDS_COLLECTION].find_one({"_id": obj_id})
        if not record:
            record = db[config.CITIZEN_SERVICES_COLLECTION].find_one({"_id": obj_id})
    except:
        record = db[config.CIVIL_RECORDS_COLLECTION].find_one({"_id": form_id})
        if not record:
            record = db[config.CITIZEN_SERVICES_COLLECTION].find_one({"_id": form_id})
        
    if not record:
        raise HTTPException(status_code=404, detail="Form not found")
        
    form_type = record.get("form_type")
    image_path = record.get("image_path")
    # Use corrected data if available, otherwise raw extracted data (since it matches the handwriting)
    extracted_data = record.get("extracted_data", {})
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"Image file missing: {image_path}")
        
    try:
        template_path, coords_path = template_engine.auto_create_template(
            image_path=image_path,
            extracted_data=extracted_data,
            form_type=form_type
        )
        return {
            "success": True, 
            "message": f"Blank template auto-generated for {form_type}",
            "template_path": template_path
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
        

@router.get("/generate-digital/{form_id}")
async def generate_digital_form(form_id: str):
    """
    Overlays a form's structured data onto the master blank template
    to generate a clean, final digital form. Returns the image file.
    """
    db = DatabaseManager.get_db_connection()
    
    try:
        obj_id = ObjectId(form_id)
        record = db[config.CIVIL_RECORDS_COLLECTION].find_one({"_id": obj_id})
        if not record:
            record = db[config.CITIZEN_SERVICES_COLLECTION].find_one({"_id": obj_id})
    except:
        record = db[config.CIVIL_RECORDS_COLLECTION].find_one({"_id": form_id})
        if not record:
            record = db[config.CITIZEN_SERVICES_COLLECTION].find_one({"_id": form_id})
        
    if not record:
        raise HTTPException(status_code=404, detail="Form not found")
        
    form_type = record.get("form_type")
    
    # Merge extracted data with human-corrected data
    final_data = record.get("extracted_data", {})
    if "corrected_data" in record:
        final_data.update(record["corrected_data"])
        
    try:
        output_filename = template_engine.generate_digital_form(
            form_type=form_type,
            extracted_data=final_data
        )
        
        if not output_filename:
            raise HTTPException(
                status_code=400, 
                detail="Master template not found. Please auto-create a template first."
            )
            
        file_path = os.path.join(config.UPLOAD_FOLDER, output_filename)
        return FileResponse(file_path, media_type="image/jpeg", filename=output_filename)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
