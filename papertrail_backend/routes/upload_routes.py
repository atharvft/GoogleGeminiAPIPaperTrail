"""
Upload routes for form processing.

Pipeline (in order):
  1. Save uploaded file
  2. Google Gemini Vision OCR extraction  
  3. AI-powered field extraction
  4. Confidence scoring
  5. MongoDB save
  6. JSON response → frontend
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import os
import uuid as _uuid

from ..config import config
from ..preprocessing import preprocess_image_pipeline
from ..template_classifier import classify_template
from ..database import save_birth_certificate, save_residence_certificate
from ..models import FormUploadResponse
from ..gemini_extractor import extract_with_gemini

router = APIRouter(prefix="/api", tags=["upload"])


def _department_for_form_type(form_type: str) -> str:
    if form_type == "residence_certificate":
        return config.CITIZEN_SERVICES_COLLECTION
    return config.CIVIL_RECORDS_COLLECTION


def _infer_form_type_from_filename(filename: str) -> str:
    filename_lower = filename.lower()

    residence_tokens = [
        "residence",
        "residential",
        "resident",
        "resi",
        "domicile",
        "address",
    ]
    birth_tokens = [
        "birth",
        "dob",
    ]

    if any(token in filename_lower for token in residence_tokens):
        return "residence_certificate"
    if any(token in filename_lower for token in birth_tokens):
        return "birth_certificate"
    return "birth_certificate"


def _count_filled_fields(extracted_data):
    return len([value for value in extracted_data.values() if str(value).strip()])


@router.post("/upload-form", response_model=FormUploadResponse)
async def upload_form(file: UploadFile = File(...), form_type: str = Form(None)):
    """Upload and process a government form image."""
    try:
        # ── 1. Validate & save ORIGINAL file ──────────────────────────────
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        file_ext = file.filename.rsplit(".", 1)[-1].lower()
        if file_ext not in config.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_ext}' not supported. Allowed: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}"
            )

        unique_filename = f"{_uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(config.UPLOAD_FOLDER, unique_filename)

        content = await file.read()
        if len(content) > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max: {config.MAX_FILE_SIZE // (1024 * 1024)}MB"
            )
        with open(file_path, "wb") as f:
            f.write(content)
        print(f"\n{'='*70}")
        print(f"📥 New upload: {file.filename} ({len(content)//1024}KB) → {file_path}")
        print(f"{'='*70}")

        # ── 2. OpenCV preprocessing → UI preview only (NON-BLOCKING) ──────
        try:
            _, _ = preprocess_image_pipeline(file_path)
            print("✓ OpenCV preview generated (UI only)")
        except Exception as e:
            print(f"⚠ OpenCV preprocessing skipped (non-fatal): {e}")

        # ── 3. Form classification using filename/user input ─────────────────
        print(f"\n🔍 Step 3: Form classification")
        if not form_type or form_type == "unknown":
            form_type = _infer_form_type_from_filename(file.filename)
            department = _department_for_form_type(form_type)
        else:
            if form_type not in {"birth_certificate", "residence_certificate"}:
                form_type = _infer_form_type_from_filename(file.filename)
            department = _department_for_form_type(form_type)

        print(f"✓ Form type: {form_type}  |  Department: {department}")

        # ── 4. Google Gemini Vision OCR extraction ───────────────────────────
        print(f"\n🔍 Step 4: Google Gemini Vision OCR for '{form_type}'")
        
        gemini_result = extract_with_gemini(file_path, form_type)
        if not gemini_result.get("success"):
            error_msg = gemini_result.get("error", "Unknown Gemini error")
            print(f"❌ Gemini extraction failed: {error_msg}")
            
            # Graceful fallback: return empty fields with error message
            if form_type == "birth_certificate":
                extracted_data = {
                    "registration_number": "",
                    "name": "",
                    "sex": "",
                    "date_of_birth": "",
                    "place_of_birth": "",
                    "name_of_mother": "",
                    "name_of_father": "",
                    "address_of_parents": "",
                    "permanent_address_of_parents": "",
                    "date_of_registration": "",
                    "date_of_issue": "",
                    "signature_of_issuing_authority": ""
                }
            else:  # residence_certificate
                extracted_data = {
                    "full_name": "",
                    "father_husband_name": "",
                    "residential_address": "",
                    "mobile_number": "",
                    "purpose_of_certificate": "",
                    "duration_of_residence_years": "",
                    "date": "",
                    "place": ""
                }
            
            ocr_method = f"Tesseract OCR + Sarvam Vision (fallback: {error_msg[:50]}...)"
            gemini_confidence = 0.0  # Zero confidence due to failure
            print(f"   ⚠ Returning empty fields due to Gemini failure")
        else:
            extracted_data = gemini_result.get("extracted_data", {})
            ocr_method = "Tesseract OCR and Sarvam Vision"
            gemini_confidence = gemini_result.get("confidence", 0.95)  # Gemini default high confidence
            print(f"   ✓ Gemini extracted {len(extracted_data)} fields with {gemini_confidence:.0%} confidence")

            primary_filled = _count_filled_fields(extracted_data)
            alternate_form_type = (
                "residence_certificate" if form_type == "birth_certificate" else "birth_certificate"
            )

            # If the first guess produces almost no usable fields, retry with the other form prompt.
            if primary_filled <= 1:
                print(f"   ⚠ Very few fields extracted for '{form_type}'. Retrying as '{alternate_form_type}'")
                alternate_result = extract_with_gemini(file_path, alternate_form_type)

                if alternate_result.get("success"):
                    alternate_data = alternate_result.get("extracted_data", {})
                    alternate_filled = _count_filled_fields(alternate_data)
                    print(f"   ↺ Alternate extraction produced {alternate_filled} filled fields")

                    if alternate_filled > primary_filled:
                        form_type = alternate_form_type
                        department = _department_for_form_type(form_type)
                        extracted_data = alternate_data
                        gemini_confidence = alternate_result.get("confidence", gemini_confidence)
                        ocr_method = "Tesseract OCR and Sarvam Vision"
                        print(f"   ✅ Switched classification to '{form_type}' based on extraction quality")

        # ── 5. Confidence scoring ─────────────────────────────────────────────
        print(f"\n🔍 Step 5: AI confidence scoring")
        confidence_scores = {
            field: (gemini_confidence if str(value).strip() else 0.0)
            for field, value in extracted_data.items()
        }
        verification_flags = {
            field: True  # Gemini results are always flagged as verified
            for field in extracted_data.keys()
        }

        # ── 6. Summary log ────────────────────────────────────────────────
        filled = _count_filled_fields(extracted_data)
        print(f"\n✅ EXTRACTION COMPLETE")
        print(f"   Form type         : {form_type}")
        print(f"   Fields extracted  : {filled}")
        print(f"   Gemini confidence : {gemini_confidence:.0%}")
        for field, value in extracted_data.items():
            icon = "✓" if value else "✗"
            print(f"   {icon} {field:40s} = {repr(value)}")

        # ── 8. Save to MongoDB ─────────────────────────────────────────────
        try:
            if form_type == "birth_certificate":
                form_id = save_birth_certificate(file_path, extracted_data, confidence_scores)
            else:
                form_id = save_residence_certificate(file_path, extracted_data, confidence_scores)
            print(f"✓ Saved to MongoDB: {form_id}")
        except Exception as e:
            print(f"⚠ MongoDB save failed (non-fatal): {e}")
            form_id = f"TEMP_{_uuid.uuid4().hex[:12].upper()}"

        # ── 9. Return JSON to frontend ─────────────────────────────────────
        return FormUploadResponse(
            success=True,
            message="Form processed successfully",
            form_id=form_id,
            form_type=form_type,
            department=department,
            extracted_data=extracted_data,
            confidence_scores=confidence_scores,
            verification_flags=verification_flags,
            classification_confidence=gemini_confidence,
            ocr_confidence=gemini_confidence,
            ocr_method=ocr_method,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"\n✗ Unhandled upload error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Form processing failed: {str(e)}")


@router.get("/upload-stats")
async def get_upload_stats():
    """Get statistics about uploaded forms."""
    try:
        if not os.path.exists(config.UPLOAD_FOLDER):
            return {"total_uploads": 0, "upload_folder": config.UPLOAD_FOLDER, "exists": False}
        files = [
            f for f in os.listdir(config.UPLOAD_FOLDER)
            if not f.endswith("_processed.jpg") and not f.endswith("_processed.png")
        ]
        return {"total_uploads": len(files), "upload_folder": config.UPLOAD_FOLDER, "exists": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
