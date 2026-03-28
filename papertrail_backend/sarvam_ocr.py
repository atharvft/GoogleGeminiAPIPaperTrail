"""
Sarvam Vision OCR integration with Tesseract fallback.

Pipeline:
  Image → Sarvam Vision (primary) → page_1.md markdown
       ↓ (if empty)
  Tesseract OCR (fallback)
       ↓
  parse_markdown_to_fields() — 4-strategy markdown parser
       ↓
  Template-based field extraction (per form type)
       ↓
  Confidence scoring (filled / expected fields)
"""

import json
import os
import re
import tempfile
import zipfile
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import requests
from sarvamai import SarvamAI

from .config import config as settings


# ── Form templates: canonical expected fields per form type ───────────────────
FORM_TEMPLATES: Dict[str, List[str]] = {
    "birth_certificate": [
        "name",
        "sex",
        "date_of_birth",
        "place_of_birth",
        "name_of_mother",
        "name_of_father",
        "address_of_parents_at_birth",
        "permanent_address_of_parents",
        "registration_number",
        "date_of_registration",
        "date_of_issue",
        "remarks",
    ],
    "residence_certificate": [
        "full_name",
        "father_husband_name",
        "residential_address",
        "mobile_number",
        "purpose_of_certificate",
        "duration_of_residence_years",
        "date",
        "place",
    ],
    # Extensible: add more form types here
}


# ── Label → canonical field name mapping ─────────────────────────────────────
FIELD_LABEL_MAP: Dict[str, str] = {
    # Birth Certificate
    "name": "name",
    "applicant name": "name",
    "child name": "name",
    "child's name": "name",
    "sex": "sex",
    "gender": "sex",
    "date of birth": "date_of_birth",
    "dob": "date_of_birth",
    "place of birth": "place_of_birth",
    "birth place": "place_of_birth",
    "name of mother": "name_of_mother",
    "mother's name": "name_of_mother",
    "mother name": "name_of_mother",
    "name of father": "name_of_father",
    "father's name": "name_of_father",
    "father name": "name_of_father",
    "address of parents at birth": "address_of_parents_at_birth",
    "address at time of birth": "address_of_parents_at_birth",
    "address at birth": "address_of_parents_at_birth",
    "permanent address of parents": "permanent_address_of_parents",
    "permanent address": "permanent_address_of_parents",
    "registration number": "registration_number",
    "reg no": "registration_number",
    "registration no": "registration_number",
    "date of registration": "date_of_registration",
    "date of issue": "date_of_issue",
    "remarks": "remarks",
    # Residence Certificate
    "full name": "full_name",
    "applicant": "full_name",
    "father / husband name": "father_husband_name",
    "father/husband name": "father_husband_name",
    "father or husband name": "father_husband_name",
    "residential address": "residential_address",
    "address": "residential_address",
    "mobile number": "mobile_number",
    "mobile no": "mobile_number",
    "phone": "mobile_number",
    "purpose of certificate": "purpose_of_certificate",
    "purpose": "purpose_of_certificate",
    "duration of residence": "duration_of_residence_years",
    "duration of residence (years)": "duration_of_residence_years",
    "duration": "duration_of_residence_years",
    "date": "date",
    "place": "place",
}


# ── Module-level helpers ──────────────────────────────────────────────────────

def _canonical(label: str) -> Optional[str]:
    """Map a label string to a canonical field key, return None if unrecognised."""
    clean = re.sub(r'\s+', ' ', label.strip().lower())
    clean = re.sub(r'^\d+\.\s*', '', clean)  # strip leading "1. "
    return FIELD_LABEL_MAP.get(clean)


def parse_markdown_to_fields(markdown_text: str) -> Dict[str, str]:
    """
    Parse Sarvam Vision markdown (page_1.md) into key-value pairs.

    Tries four strategies in order:
    1. **Label:** Value  (bold key-value)
    2. | Label | Value | (markdown table row)
    3. 1. Label : Value  (numbered fields)
    4. Label: Value      (plain colon line)
    """
    fields: Dict[str, str] = {}

    # Strategy 1 — **Label:** Value
    for raw_label, raw_value in re.findall(
        r'\*\*([^*\n]+?)\**\s*:?\s*\**\s*:?\s*([^\n*|]{2,120})',
        markdown_text, re.IGNORECASE
    ):
        label = raw_label.strip().strip('*').strip(':').lower()
        value = raw_value.strip().strip('*').strip('|').strip()
        if label and value and not re.match(r'^[-:=\s]+$', value):
            key = _canonical(label)
            if key and key not in fields:
                fields[key] = value

    # Strategy 2 — | Label | Value |
    for raw_label, raw_value in re.findall(
        r'\|\s*([^|\n]+?)\s*\|\s*([^|\n]+?)\s*\|',
        markdown_text, re.IGNORECASE
    ):
        if re.match(r'^[\s\-:]+$', raw_value):
            continue
        label = raw_label.strip().strip('*').lower()
        value = raw_value.strip().strip('*')
        if label and value:
            key = _canonical(label)
            if key and key not in fields:
                fields[key] = value

    # Strategy 3 — Numbered "1. Full Name : Value"
    for raw_label, raw_value in re.findall(
        r'^\s*\d+\.\s*([A-Za-z /()]+?)\s*[:\-]\s*(.{2,120})',
        markdown_text, re.MULTILINE | re.IGNORECASE
    ):
        label = raw_label.strip().lower()
        value = raw_value.strip().strip('*').strip('|').strip()
        if label and value:
            key = _canonical(label)
            if key and key not in fields:
                fields[key] = value

    # Strategy 4 — plain "Label: Value"
    for raw_label, raw_value in re.findall(
        r'^([A-Za-z][A-Za-z /()\']{2,50}?)\s*:\s*(.{2,120})$',
        markdown_text, re.MULTILINE | re.IGNORECASE
    ):
        label = raw_label.strip().lower()
        value = raw_value.strip().strip('*').strip('|').strip()
        if label and value and not re.match(r'^[-:=\s]+$', value):
            key = _canonical(label)
            if key and key not in fields:
                fields[key] = value

    print(f"[MarkdownParser] Found {len(fields)} fields: {list(fields.keys())}")
    return fields


def infer_form_type_from_fields(fields: Dict[str, str]) -> str:
    """Infer form type by scoring which template fields were found."""
    found = set(fields.keys())
    scores = {
        form_type: len(found & set(template_fields))
        for form_type, template_fields in FORM_TEMPLATES.items()
    }
    print(f"[FormTypeInference] Scores: {scores}")
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "unknown"


def score_extraction_confidence(
    extracted: Dict[str, str],
    form_type: str,
) -> Tuple[float, Dict[str, float], Dict[str, bool]]:
    """
    Compute per-field confidence scores and overall classification confidence.

    Classification confidence = filled_expected_fields / total_expected_fields

    Args:
        extracted: dict of field_key → value
        form_type: e.g. "birth_certificate"

    Returns:
        (classification_confidence, confidence_scores, verification_flags)
    """
    expected = FORM_TEMPLATES.get(form_type, list(extracted.keys()))

    # Per-field confidence: 0.92 if value present, 0.0 if empty
    confidence_scores: Dict[str, float] = {}
    for field in expected:
        confidence_scores[field] = 0.92 if extracted.get(field) else 0.0

    # Also include extra fields found outside the template
    for field, value in extracted.items():
        if field not in confidence_scores:
            confidence_scores[field] = 0.92 if value else 0.0

    verification_flags: Dict[str, bool] = {
        field: score < settings.CONFIDENCE_THRESHOLD
        for field, score in confidence_scores.items()
    }

    # Overall confidence = proportion of expected fields that are filled
    filled = sum(1 for f in expected if extracted.get(f))
    classification_confidence = round(filled / len(expected), 4) if expected else 0.0

    print(
        f"[Confidence] {filled}/{len(expected)} expected fields filled → "
        f"classification_confidence={classification_confidence:.0%}"
    )
    return classification_confidence, confidence_scores, verification_flags


# ── OCR fallback using Tesseract ──────────────────────────────────────────────

def run_tesseract_ocr(image_path: str) -> str:
    """
    Tesseract OCR fallback when Sarvam Vision returns empty output.
    Applies gentle cv2 preprocessing before running Tesseract.
    """
    try:
        import pytesseract
        from PIL import Image

        # Load and preprocess for Tesseract
        img = cv2.imread(image_path)
        if img is None:
            # Try PIL for non-standard formats (webp, etc.)
            pil_img = Image.open(image_path).convert("RGB")
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Mild denoising + adaptive threshold for handwriting
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        thresh = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2,
        )
        # Tesseract config: OEM 3 (LSTM), PSM 6 (assume uniform block of text)
        config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(thresh, lang="eng", config=config)
        print(f"[TesseractFallback] Extracted {len(text)} characters")
        return text.strip()

    except ImportError:
        print("[TesseractFallback] pytesseract not installed — skipping fallback")
        return ""
    except Exception as e:
        print(f"[TesseractFallback] ❌ Error: {e}")
        return ""


# ── Sarvam Vision main class ──────────────────────────────────────────────────

class SarvamVisionOCR:
    """
    Sarvam Vision Document Intelligence wrapper.
    Sends ORIGINAL file to Sarvam, extracts page_1.md from ZIP,
    falls back to Tesseract if Sarvam returns empty text.
    """

    def __init__(self) -> None:
        self.api_key = settings.SARVAM_API_KEY
        self.language = settings.SARVAM_VISION_LANGUAGE
        self.output_format = settings.SARVAM_VISION_OUTPUT_FORMAT
        self.poll_interval = settings.SARVAM_VISION_POLL_INTERVAL
        self.timeout = settings.SARVAM_VISION_TIMEOUT
        self.client = SarvamAI(api_subscription_key=self.api_key)
        self.chat_url = "https://api.sarvam.ai/api/extra/llms/v1/chat"

    # ── Public ───────────────────────────────────────────────────────────────

    def run_ocr(self, image_path: str) -> Dict:
        """
        Run Sarvam Vision OCR on the ORIGINAL image file.
        Falls back to Tesseract if Sarvam returns empty text.

        Args:
            image_path: Absolute path to the ORIGINAL (unsaved) saved file

        Returns:
            {"text": str, "average_confidence": float, "text_blocks": list}
        """
        # ── Primary: Sarvam Vision ────────────────────────────────────────
        raw_text = ""
        ocr_source = "sarvam"
        try:
            raw_text = self._run_document_intelligence(image_path)
        except Exception as e:
            print(f"[SarvamVisionOCR] ❌ Sarvam failed: {e}")

        print(f"\n{'='*70}\n📄 SARVAM MARKDOWN (first 1200 chars):\n{'='*70}")
        print(raw_text[:1200] if raw_text else "(empty)")
        print(f"{'='*70}\n")

        # ── Fallback: Tesseract ───────────────────────────────────────────
        if not raw_text.strip():
            print("⚠ Sarvam returned empty text — running Tesseract fallback...")
            raw_text = run_tesseract_ocr(image_path)
            ocr_source = "tesseract"
            if raw_text:
                print(f"✓ Tesseract fallback produced {len(raw_text)} characters")
            else:
                print("❌ Both Sarvam and Tesseract returned empty text")

        print(f"[OCR] Source: {ocr_source} | Length: {len(raw_text)} chars")
        text_blocks = self._build_text_blocks(raw_text)
        return {
            "text": raw_text,
            "average_confidence": 0.92 if ocr_source == "sarvam" else 0.70,
            "text_blocks": text_blocks,
            "ocr_source": ocr_source,
        }

    def parse_with_sarvam_llm(self, ocr_text: str, form_type: str) -> Dict:
        """
        Optional: use Sarvam LLM to fill in fields the markdown parser missed.
        Returns {} on any failure — caller continues with what it already has.
        """
        if not ocr_text.strip():
            return {}

        fields = FORM_TEMPLATES.get(form_type, [])
        if not fields:
            print(f"[SarvamLLM] No template for '{form_type}' — skipping.")
            return {}

        prompt = self._build_llm_prompt(form_type, fields, ocr_text)
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self.api_key,
        }
        payload = {
            "model": "s2-large",
            "messages": [
                {"role": "system", "content": "You are an OCR extraction assistant. Respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "max_output_tokens": 800,
        }

        try:
            print(f"[SarvamLLM] Calling chat endpoint for '{form_type}'...")
            response = requests.post(self.chat_url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            raw = response.json()

            if "choices" not in raw or not raw["choices"]:
                return {}

            content = raw["choices"][0].get("message", {}).get("content", "")
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )

            print(f"[SarvamLLM] Response preview: {str(content)[:300]}")
            json_str = self._extract_json_string(str(content))
            result = json.loads(json_str)
            filled = len([v for v in result.values() if v])
            print(f"[SarvamLLM] ✅ {filled}/{len(result)} fields from LLM.")
            return result

        except requests.exceptions.RequestException as e:
            print(f"[SarvamLLM] ❌ HTTP: {e}")
        except json.JSONDecodeError as e:
            print(f"[SarvamLLM] ❌ JSON: {e}")
        except Exception as e:
            print(f"[SarvamLLM] ❌ Error: {e}")
        return {}

    # ── Sarvam Vision job ─────────────────────────────────────────────────────

    def _run_document_intelligence(self, image_path: str) -> str:
        print(f"[SarvamVisionOCR] Creating job for: {image_path}")
        job = self.client.document_intelligence.create_job(
            language=self.language,
            output_format=self.output_format,
        )
        print(f"[SarvamVisionOCR] Job ID: {job.job_id}")
        job.upload_file(image_path)
        job.start()
        print(f"[SarvamVisionOCR] Waiting for completion...")
        status = job.wait_until_complete()
        state = getattr(status, "job_state", None)
        print(f"[SarvamVisionOCR] Job state: {state}")

        if state not in {"COMPLETED", "PARTIALLY_COMPLETED"}:
            raise RuntimeError(f"Sarvam Vision job ended with state: {state}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, f"{job.job_id}.zip")
            print(f"[SarvamVisionOCR] Downloading ZIP → {zip_path}")
            job.download_output(zip_path)
            return self._read_markdown_from_zip(zip_path)

    def _read_markdown_from_zip(self, zip_path: str) -> str:
        """
        Extract text from the Sarvam output ZIP.
        Priority: page_1.md > any .md > any .html > first file.
        """
        with zipfile.ZipFile(zip_path, "r") as zf:
            all_files = zf.namelist()
            print(f"[SarvamVisionOCR] ZIP contents: {all_files}")

            # Find best candidate file
            candidate = None
            for name in all_files:
                if name.lower() == "page_1.md":
                    candidate = name
                    break
            if not candidate:
                for name in all_files:
                    if name.lower().endswith(".md"):
                        candidate = name
                        break
            if not candidate:
                for name in all_files:
                    if name.lower().endswith(".html"):
                        candidate = name
                        break
            if not candidate and all_files:
                candidate = all_files[0]

            if not candidate:
                raise ValueError("Sarvam output ZIP is empty")

            print(f"[SarvamVisionOCR] Reading: {candidate}")
            with zf.open(candidate) as f:
                content = f.read().decode("utf-8", errors="ignore")

        if candidate.lower().endswith(".html"):
            return self._html_to_text(content)
        return content  # Return raw markdown — structure preserved for parsing

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_llm_prompt(self, form_type: str, fields: List[str], ocr_text: str) -> str:
        field_lines = "\n".join(f"- {f}" for f in fields)
        return (
            "You are digitizing an Indian government form. OCR output (markdown) is below.\n"
            "Extract each field. Return ONLY a valid JSON object.\n"
            "Use empty string for missing values.\n\n"
            f"Form type: {form_type}\nExpected fields:\n{field_lines}\n\n"
            "MARKDOWN:\n"
            f"{ocr_text[:3000]}"
        )

    def _extract_json_string(self, text: str) -> str:
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence:
            return fence.group(1).strip()
        brace = re.search(r"\{[\s\S]*\}", text)
        return brace.group(0) if brace else text.strip()

    def _html_to_text(self, html: str) -> str:
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()

    def _build_text_blocks(self, text: str) -> List[Dict]:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return [
            {"id": i, "text": line, "left": 0, "top": i * 20,
             "width": 100, "height": 18, "confidence": 0.92}
            for i, line in enumerate(lines)
        ]


# ── Module-level singletons ───────────────────────────────────────────────────
_ocr = SarvamVisionOCR()


def run_sarvam_ocr(image_path: str) -> Dict:
    """Run OCR on the ORIGINAL image. Tesseract fallback if Sarvam returns empty."""
    return _ocr.run_ocr(image_path)


def parse_with_sarvam_llm(ocr_text: str, form_type: str) -> Dict:
    """Optional LLM enhancement to fill missing fields."""
    return _ocr.parse_with_sarvam_llm(ocr_text, form_type)
