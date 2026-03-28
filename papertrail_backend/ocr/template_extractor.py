"""
Template-based coordinate OCR extractor.

Pipeline per uploaded form
──────────────────────────
1. Load original image with OpenCV
2. Scale image to the template's reference dimensions (normalise scan size)
3. Optional: auto-rotate to align to template using ORB feature matching
4. For each field in the template:
      a. Crop the bounding box
      b. Pre-process the crop (denoise, threshold)
      c. Run PaddleOCR on the crop; fallback to Tesseract; fallback to Sarvam Vision markdown
5. Clean each extracted value
6. Compute confidence = filled_fields / total_expected_fields
7. Return structured dict

OCR priority (accuracy-driven)
───────────────────────────────
- PaddleOCR    (best for handwritten Indian forms, uses deep learning)
- Tesseract    (fast, local, good for printed text)
- Sarvam Vision markdown (already fetched upstream — passed in as optional arg)
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pytesseract
from PIL import Image


# ── Template registry ─────────────────────────────────────────────────────────
def _load_templates() -> Dict[str, dict]:
    from .templates.birth_certificate_template import (
        BIRTH_CERTIFICATE_TEMPLATE,
        REFERENCE_W as BC_W,
        REFERENCE_H as BC_H,
    )
    from .templates.residence_certificate_template import (
        RESIDENCE_CERTIFICATE_TEMPLATE,
        REFERENCE_W as RC_W,
        REFERENCE_H as RC_H,
    )
    return {
        "birth_certificate": {
            "fields": BIRTH_CERTIFICATE_TEMPLATE,
            "ref_w": BC_W,
            "ref_h": BC_H,
        },
        "residence_certificate": {
            "fields": RESIDENCE_CERTIFICATE_TEMPLATE,
            "ref_w": RC_W,
            "ref_h": RC_H,
        },
    }

TEMPLATES: Dict[str, dict] = _load_templates()


# ── Image loading ─────────────────────────────────────────────────────────────

def _load_image(image_path: str) -> np.ndarray:
    """Load image robustly (handles JPEG, PNG, WEBP, PDF first-page)."""
    img = cv2.imread(image_path)
    if img is not None:
        return img
    # Fallback for WEBP / unusual formats
    try:
        pil = Image.open(image_path).convert("RGB")
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise ValueError(f"Cannot open image at {image_path}: {e}")


# ── Scaling ───────────────────────────────────────────────────────────────────

def _scale_to_reference(img: np.ndarray, ref_w: int, ref_h: int) -> np.ndarray:
    """Scale the uploaded image to match the template reference size."""
    h, w = img.shape[:2]
    if w == ref_w and h == ref_h:
        return img
    print(f"[TemplateExtractor] Scaling {w}×{h} → {ref_w}×{ref_h}")
    return cv2.resize(img, (ref_w, ref_h), interpolation=cv2.INTER_LANCZOS4)


# ── Deskew ────────────────────────────────────────────────────────────────────

def _deskew_image(img: np.ndarray) -> np.ndarray:
    """
    Correct small rotations (±5°) using minAreaRect on text blobs.
    Falls back to returning the original if angle detection fails.
    """
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(bw > 0))
        if len(coords) < 50:
            return img
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle += 90
        if abs(angle) < 0.5:        # negligible skew
            return img
        if abs(angle) > 15:         # probably wrong detection, skip
            return img

        print(f"[TemplateExtractor] Deskewing by {angle:.2f}°")
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)
    except Exception as e:
        print(f"[TemplateExtractor] Deskew failed (non-fatal): {e}")
        return img


# ── Crop & preprocess ─────────────────────────────────────────────────────────

def _crop_region(img: np.ndarray, coords: List[int], pad: int = 6) -> np.ndarray:
    """
    Crop [x1, y1, x2, y2] from the image with optional padding.
    Returns an empty 1×1 array if coords are out of range.
    """
    x1, y1, x2, y2 = coords
    h, w = img.shape[:2]
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w, x2 + pad)
    y2 = min(h, y2 + pad)
    if x2 <= x1 or y2 <= y1:
        return np.ones((1, 1, 3), dtype=np.uint8) * 255
    return img[y1:y2, x1:x2]


def _preprocess_crop(crop: np.ndarray) -> np.ndarray:
    """
    Convert crop to a high-contrast grayscale image optimised for Tesseract.

    Steps
    ─────
    1. Upscale (Tesseract works best at ≥ 300 DPI / ~2× for photos)
    2. Grayscale
    3. Bilateral denoise (preserves edges / ink strokes)
    4. CLAHE contrast boost (improves faded ink)
    5. Adaptive threshold (handles uneven lighting)
    """
    if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
        return crop

    # 1. Upscale 2×
    h, w = crop.shape[:2]
    upscaled = cv2.resize(crop, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    # 2. Grayscale
    gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)

    # 3. Bilateral denoise
    denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

    # 4. CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    # 5. Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        enhanced, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15,
        C=10,
    )
    return thresh


# ── PaddleOCR ─────────────────────────────────────────────────────────────────

_PADDLE_OCR_INSTANCE = None  # Lazy-initialized singleton


def _init_paddleocr():
    """
    Initialize PaddleOCR lazily (singleton pattern).
    
    Note: PaddleOCR requires PaddlePaddle backend which may not be available
    on all platforms (e.g., ARM macOS). Falls back to Tesseract gracefully.
    """
    global _PADDLE_OCR_INSTANCE
    if _PADDLE_OCR_INSTANCE is None:
        try:
            # Suppress model connectivity check
            import os
            os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
            
            from paddleocr import PaddleOCR
            print("[TemplateExtractor] Initializing PaddleOCR...")
            
            # Updated parameter names for PaddleOCR 3.4+
            _PADDLE_OCR_INSTANCE = PaddleOCR(
                use_textline_orientation=True,  # Replaces use_angle_cls
                lang='en',
            )
            print("[TemplateExtractor] ✓ PaddleOCR initialized successfully")
        except ImportError as e:
            print(f"[TemplateExtractor] ⚠ PaddleOCR not available ({e}). Using Tesseract fallback.")
            _PADDLE_OCR_INSTANCE = False
        except Exception as e:
            print(f"[TemplateExtractor] ⚠ PaddleOCR init failed: {e}. Using Tesseract fallback.")
            _PADDLE_OCR_INSTANCE = False
    return _PADDLE_OCR_INSTANCE


def _run_paddleocr(crop: np.ndarray) -> str:
    """
    Run PaddleOCR on a cropped field region.
    
    PaddleOCR format: [[(x1,y1), (x2,y2), (x3,y3), (x4,y4)], ('text', confidence)]
    
    Returns cleaned text string or empty string if failed.
    """
    try:
        ocr = _init_paddleocr()
        if ocr is False:  # PaddleOCR not available
            return ""
        
        # PaddleOCR expects RGB, convert from BGR if needed
        if len(crop.shape) == 3:
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        else:
            crop_rgb = crop
        
        # Run OCR
        result = ocr.ocr(crop_rgb, cls=True)
        
        if not result or not result[0]:
            return ""
        
        # Extract text from all detected lines
        texts = []
        for line in result[0]:
            if line and len(line) >= 2:
                text_data = line[1]
                if isinstance(text_data, (list, tuple)) and len(text_data) >= 1:
                    text = text_data[0]
                    if text:
                        texts.append(str(text))
        
        combined = " ".join(texts)
        return _clean(combined)
        
    except Exception as e:
        print(f"[TemplateExtractor] PaddleOCR error: {e}")
        return ""


# ── Tesseract OCR ─────────────────────────────────────────────────────────────

_TESS_CONFIG = r"--oem 3 --psm 7 -l eng"   # PSM 7 = single line of text


def _run_tesseract(crop: np.ndarray) -> str:
    """Run Tesseract on a pre-processed crop. Returns cleaned string."""
    try:
        processed = _preprocess_crop(crop)
        text = pytesseract.image_to_string(processed, config=_TESS_CONFIG)
        return _clean(text)
    except Exception as e:
        print(f"[TemplateExtractor] Tesseract error: {e}")
        return ""


def _clean(text: str) -> str:
    """Strip noise characters typically produced by Tesseract on blank areas."""
    text = text.strip()
    # Remove lines that are purely punctuation / whitespace
    lines = [l.strip() for l in text.splitlines() if re.search(r"[A-Za-z0-9]", l)]
    text = " ".join(lines)
    # Collapse multiple spaces
    text = re.sub(r"\s{2,}", " ", text).strip()
    # Remove leading/trailing dots and dashes (common artefacts)
    text = text.strip(".-_|")
    return text


# ── Markdown fallback ──────────────────────────────────────────────────────────

def _extract_from_markdown(field_key: str, markdown_text: str) -> str:
    """
    Try to pull a field value from Sarvam Vision markdown when Tesseract
    returns empty for that crop.  Uses the same label map from sarvam_ocr.py.
    """
    if not markdown_text:
        return ""
    # We import lazily to avoid circular imports
    try:
        from papertrail_backend.sarvam_ocr import parse_markdown_to_fields
        fields = parse_markdown_to_fields(markdown_text)
        return fields.get(field_key, "")
    except Exception:
        return ""


# ── Confidence ────────────────────────────────────────────────────────────────

def _compute_confidence(
    extracted: Dict[str, str],
    template_fields: Dict[str, List[int]],
) -> float:
    """filled_expected / total_expected  (0.0 – 1.0)"""
    total = len(template_fields)
    if total == 0:
        return 0.0
    filled = sum(1 for k in template_fields if extracted.get(k, "").strip())
    confidence = round(filled / total, 4)
    print(f"[TemplateExtractor] Confidence: {filled}/{total} = {confidence:.0%}")
    return confidence


# ── Main extractor class ──────────────────────────────────────────────────────

class TemplateExtractor:
    """
    Coordinate-based OCR extractor.

    Usage
    ─────
    extractor = TemplateExtractor()
    result = extractor.extract(image_path, form_type, markdown_text="...")
    """

    def extract(
        self,
        image_path: str,
        form_type: str,
        *,
        markdown_text: str = "",
        save_debug_crops: bool = False,
    ) -> Dict:
        """
        Main entry point.

        Args:
            image_path:        Path to the ORIGINAL uploaded image.
            form_type:         e.g. "birth_certificate"
            markdown_text:     Optional Sarvam Vision markdown (used as fallback).
            save_debug_crops:  If True, saves each field crop to /tmp for inspection.

        Returns:
            {
              "form_type": str,
              "fields": Dict[str, str],
              "confidence": float,          # 0.0 – 1.0
              "confidence_scores": Dict[str, float],
              "verification_flags": Dict[str, bool],
              "method": "coordinate_ocr_paddleocr",  # or "coordinate_ocr_tesseract"
            }
        """
        tmpl = TEMPLATES.get(form_type)
        if not tmpl:
            print(f"[TemplateExtractor] No template for '{form_type}' — skipping.")
            return {}

        template_fields: Dict[str, List[int]] = tmpl["fields"]
        ref_w: int = tmpl["ref_w"]
        ref_h: int = tmpl["ref_h"]

        print(f"\n[TemplateExtractor] 🔬 Coordinate OCR for '{form_type}' — {len(template_fields)} fields")
        print(f"[TemplateExtractor] Image: {os.path.basename(image_path)}")

        # ── 1. Load & scale
        img = _load_image(image_path)
        img = _scale_to_reference(img, ref_w, ref_h)

        # ── 2. Deskew
        img = _deskew_image(img)

        # ── 3. Per-field OCR
        extracted: Dict[str, str] = {}
        confidence_scores: Dict[str, float] = {}

        debug_dir = tempfile.mkdtemp(prefix="pt_crops_") if save_debug_crops else None

        for field_key, coords in template_fields.items():
            crop = _crop_region(img, coords)
            
            # Try OCR engines in priority order: PaddleOCR → Tesseract → Markdown
            text = ""
            ocr_method = ""
            
            # 1. Try PaddleOCR first (best for handwritten text)
            text = _run_paddleocr(crop)
            if text:
                ocr_method = "PaddleOCR"
            
            # 2. Fallback to Tesseract if PaddleOCR failed or unavailable
            if not text:
                text = _run_tesseract(crop)
                if text:
                    ocr_method = "Tesseract"
            
            # 3. Fallback to Sarvam markdown if both OCR engines got nothing
            if not text and markdown_text:
                text = _extract_from_markdown(field_key, markdown_text)
                if text:
                    ocr_method = "Markdown"
                    print(f"   ↳ {field_key}: OCR empty → markdown fallback: {repr(text)}")

            extracted[field_key] = text
            confidence_scores[field_key] = 0.92 if text else 0.0

            icon = "✓" if text else "✗"
            method_label = f"[{ocr_method}]" if ocr_method else ""
            print(f"   {icon} {field_key:40s} {method_label:12s} = {repr(text[:50]) if text else '—'}")

            if save_debug_crops and debug_dir:
                crop_path = os.path.join(debug_dir, f"{field_key}.jpg")
                cv2.imwrite(crop_path, crop)

        if save_debug_crops and debug_dir:
            print(f"[TemplateExtractor] Debug crops saved → {debug_dir}")

        # ── 4. Confidence
        confidence = _compute_confidence(extracted, template_fields)

        # ── 5. Verification flags (fields under 75% single-field threshold)
        try:
            from ..config import config as settings
            threshold = getattr(settings, "CONFIDENCE_THRESHOLD", 0.75)
        except ImportError:
            threshold = 0.75
        verification_flags = {k: (v < threshold) for k, v in confidence_scores.items()}

        return {
            "form_type": form_type,
            "fields": extracted,
            "confidence": confidence,
            "confidence_scores": confidence_scores,
            "verification_flags": verification_flags,
            "method": "coordinate_ocr",
        }


# ── Module-level singleton & convenience function ─────────────────────────────
_extractor = TemplateExtractor()


def run_template_extraction(
    image_path: str,
    form_type: str,
    markdown_text: str = "",
    save_debug_crops: bool = False,
) -> Dict:
    """Convenience wrapper — use this in routes."""
    return _extractor.extract(
        image_path,
        form_type,
        markdown_text=markdown_text,
        save_debug_crops=save_debug_crops,
    )
