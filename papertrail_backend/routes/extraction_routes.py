"""
extraction_routes.py
--------------------
Standalone FastAPI router for simplified full-page OCR + keyword parsing extraction.

POST /api/extract-template-fields
  • Receives an uploaded form image (multipart/form-data)
  • Runs full-page OCR on the uploaded image
  • Parses extracted text using keyword mappings
  • Returns structured JSON with fields + confidence

This endpoint is the direct interface to the simplified OCR pipeline.
"""

from __future__ import annotations

import os
import uuid as _uuid

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from ..config import config
from ..sarvam_ocr import run_sarvam_ocr, parse_markdown_to_fields, infer_form_type_from_fields

router = APIRouter(prefix="/api", tags=["extraction"])


# ── Confidence-level helper (spec: High 80-100, Medium 50-80, Low <50) ─────────
def _confidence_level(score: float) -> str:
    pct = score * 100
    if pct >= 80:
        return "high"
    elif pct >= 50:
        return "medium"
    return "low"


@router.post("/extract-template-fields")
async def extract_template_fields(
    file: UploadFile = File(...),
    form_type: str | None = Query(
        default=None,
        description="Override auto-detected form type. "
                    "Accepted values: birth_certificate | residence_certificate",
    ),
    debug_crops: bool = Query(
        default=False,
        description="If true, saves per-field debug crops to /tmp for inspection.",
    ),
):
    """
    Simplified full-page OCR + keyword parsing extraction endpoint.

    ## Pipeline
    1. Save uploaded file to uploads folder  
    2. Run full-page OCR
    3. Parse text using keyword mapping
    4. Infer form type from extracted fields (or use `form_type` override)
    5. Compute confidence from OCR engine
    7. Return structured JSON  

    ## Response
    ```json
    {
      "success": true,
      "form_type": "birth_certificate",
      "fields": {"name": "Raju Sharma", "date_of_birth": "01/01/2000", ...},
      "confidence": 0.92,
      "confidence_level": "high",
      "ocr_full_text": "...",
      "confidence_scores": {"name": 0.92, "date_of_birth": 0.92, "...": 0.92},
      "verification_flags": {"name": false, ...},
      "method": "full_page_ocr_keyword_parsing",
      "ocr_engine": "sarvam"
    }
    ```
    """
    # ── 1. Validate & save file ────────────────────────────────────────────────
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    file_ext = file.filename.rsplit(".", 1)[-1].lower()
    if file_ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File type '{file_ext}' not supported. "
                f"Allowed: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}"
            ),
        )

    content = await file.read()
    if len(content) > config.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max: {config.MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    unique_filename = f"extract_{_uuid.uuid4().hex[:12]}_{file.filename}"
    file_path = os.path.join(config.UPLOAD_FOLDER, unique_filename)
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

    with open(file_path, "wb") as fh:
        fh.write(content)

    print(f"\n[ExtractionRoute] ▶ {file.filename} → {file_path}")

    # ── 2. Validate form type override ────────────────────────────────────────
    SUPPORTED_TYPES = {"birth_certificate", "residence_certificate"}

    if form_type:
        if form_type not in SUPPORTED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown form_type '{form_type}'. Supported: {sorted(SUPPORTED_TYPES)}",
            )
        print(f"[ExtractionRoute] form_type override: {form_type}")

    # ── 3–5. Run full-page OCR + keyword parsing ─────────────────────────────
    try:
        ocr_result = run_sarvam_ocr(file_path)
    except Exception as exc:
        print(f"[ExtractionRoute] ❌ OCR failed: {exc}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}")

    full_text = ocr_result.get("text", "")
    fields = parse_markdown_to_fields(full_text)
    inferred_form_type = infer_form_type_from_fields(fields)
    detected_form_type = form_type or (inferred_form_type if inferred_form_type != "unknown" else "birth_certificate")
    confidence = round(float(ocr_result.get("average_confidence", 0.0)), 4)
    confidence_scores = {k: confidence for k, v in fields.items() if str(v).strip()}
    verification_flags = {
        k: (score < config.CONFIDENCE_THRESHOLD)
        for k, score in confidence_scores.items()
    }
    method = "full_page_ocr_keyword_parsing"

    ocr_engine = ocr_result.get("ocr_source", "sarvam")

    total_fields = len(fields)
    filled_fields = sum(1 for v in fields.values() if v and str(v).strip())

    print(
        f"[ExtractionRoute] ✅ Done — {filled_fields}/{total_fields} fields filled, "
        f"confidence={confidence:.0%}"
    )

    return JSONResponse(
        content={
            "success": True,
            "form_type": detected_form_type,
            "form_type_display": _form_type_display(detected_form_type),
            "fields": fields,
            "confidence": round(confidence, 4),
            "confidence_pct": round(confidence * 100, 1),
            "confidence_level": _confidence_level(confidence),
            "confidence_scores": {k: round(v, 4) for k, v in confidence_scores.items()},
            "verification_flags": verification_flags,
            "method": method,
            "ocr_engine": ocr_engine,
            "ocr_full_text": full_text,
            "stats": {
                "total_fields": total_fields,
                "filled_fields": filled_fields,
                "empty_fields": total_fields - filled_fields,
            },
            "file_saved_as": unique_filename,
        }
    )


def _form_type_display(form_type: str) -> str:
    _map = {
        "birth_certificate": "Birth Certificate",
        "residence_certificate": "Residence Certificate",
    }
    return _map.get(form_type, form_type.replace("_", " ").title())
