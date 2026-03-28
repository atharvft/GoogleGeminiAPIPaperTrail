"""
Upload routes for form processing.

Pipeline (in order):
  1. Save ORIGINAL file
  2. OpenCV preprocessing
  3. Full-page OCR (Sarvam Vision / Tesseract fallback)
  4. Text parsing using keywords
  5. Fields extracted
  6. Confidence from OCR engine
  7. MongoDB save
  8. JSON response → frontend
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import uuid as _uuid

from ..config import config
from ..preprocessing import preprocess_image_pipeline
from ..sarvam_ocr import (
    run_sarvam_ocr,
    parse_markdown_to_fields,
    infer_form_type_from_fields,
)
from ..template_classifier import classify_template
from ..database import save_birth_certificate, save_residence_certificate
from ..models import FormUploadResponse

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload-form", response_model=FormUploadResponse)
async def upload_form(file: UploadFile = File(...)):
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
        # We ALWAYS send the ORIGINAL file_path to Sarvam.
        # The processed image is only for the frontend preview panel.
        try:
            _, _ = preprocess_image_pipeline(file_path)
            print("✓ OpenCV preview generated (UI only — Sarvam uses original)")
        except Exception as e:
            print(f"⚠ OpenCV preprocessing skipped (non-fatal): {e}")

        # ── 3. OCR: Sarvam Vision on ORIGINAL → Tesseract fallback ────────
        print(f"\n🔍 Step 3: OCR — sending ORIGINAL to Sarvam Vision")
        try:
            ocr_result = run_sarvam_ocr(file_path)   # ← always file_path, never processed
            full_text = ocr_result.get("text", "")
            text_blocks = ocr_result.get("text_blocks", [])
            ocr_source = ocr_result.get("ocr_source", "sarvam")
            print(f"✓ OCR ({ocr_source}): {len(full_text)} chars extracted")
        except Exception as e:
            import traceback; traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")

        # ── 4. Form classification (text → keywords → field names) ─────────
        print("\n🔍 Step 4: Form classification")
        classification = classify_template(full_text)
        form_type = classification["form_type"]
        department = classification["department"]

        if form_type == "unknown":
            # Try markdown extraction first, then infer type from found fields
            pre_fields = parse_markdown_to_fields(full_text)
            if pre_fields:
                form_type = infer_form_type_from_fields(pre_fields)
                if form_type == "birth_certificate":
                    department = config.CIVIL_RECORDS_COLLECTION
                elif form_type == "residence_certificate":
                    department = config.CITIZEN_SERVICES_COLLECTION

        # Safety net — never fail due to unknown form type
        if form_type == "unknown":
            print("⚠ Unable to classify — defaulting to birth_certificate")
            form_type = "birth_certificate"
            department = config.CIVIL_RECORDS_COLLECTION

        print(f"✓ Form type: {form_type}  |  Department: {department}")

        # ── 5. Text parsing using keywords ─────────────────────────────────
        print(f"\n🔍 Step 5: Keyword-based text parsing for '{form_type}'")
        extracted_data = parse_markdown_to_fields(full_text)

        # ── 6. Confidence from OCR engine ─────────────────────────────────
        print(f"\n🔍 Step 6: OCR engine confidence")
        ocr_confidence = round(float(ocr_result.get("average_confidence", 0.0)), 4)
        confidence_scores = {
            field: (ocr_confidence if str(value).strip() else 0.0)
            for field, value in extracted_data.items()
        }
        verification_flags = {
            field: (score < config.CONFIDENCE_THRESHOLD)
            for field, score in confidence_scores.items()
        }

        # ── 7. Summary log ────────────────────────────────────────────────
        filled = len([v for v in extracted_data.values() if str(v).strip()])
        print(f"\n✅ EXTRACTION COMPLETE")
        print(f"   Form type         : {form_type}")
        print(f"   Fields extracted  : {filled}")
        print(f"   OCR confidence    : {ocr_confidence:.0%}")
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
            classification_confidence=ocr_confidence,
            ocr_confidence=ocr_confidence,
            ocr_method=f"Full-page OCR ({ocr_source}) + keyword parser",
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
