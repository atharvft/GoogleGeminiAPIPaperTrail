"""
Field extraction module.
Extracts structured attributes from OCR text based on template type.
Supports both plain-text (Tesseract-style) and markdown (Sarvam Vision) output.
"""

import re
from typing import Dict, List, Any, Tuple, Optional
from .config import config


class FieldExtractor:
    """Extracts structured fields from OCR text based on form template."""

    def __init__(self):
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD

    # ------------------------------------------------------------------
    # Core helper: try multiple patterns, return first match
    # ------------------------------------------------------------------
    def _try_patterns(self, text: str, patterns: List[str], default: str = "") -> str:
        """Try a list of regex patterns in order; return first match or default."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.group(1).strip()
                # Strip trailing markdown/punctuation noise
                value = re.sub(r"\s*\|.*$", "", value).strip()
                value = re.sub(r"\*+$", "", value).strip()
                if value:
                    return value
        return default

    def _extract_date(self, text: str, patterns: List[str]) -> str:
        """Extract and normalise a date from multiple candidate patterns."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip().rstrip("*| ")
                date_str = re.sub(r"[\/\.]", "-", date_str)
                if date_str:
                    return date_str
        return ""

    def _create_confidence_map(self, text_blocks: List[Dict[str, Any]]) -> Dict[str, float]:
        confidence_map = {}
        for block in text_blocks:
            text = block.get("text", "").strip()
            confidence = block.get("confidence", 0.0)
            if text:
                confidence_map[text.lower()] = confidence
        return confidence_map

    def _get_field_confidence(self, field_value: str, confidence_map: Dict[str, float]) -> float:
        if not field_value:
            return 0.0
        field_lower = field_value.lower()
        if field_lower in confidence_map:
            return confidence_map[field_lower]
        confidences = [
            conf for text, conf in confidence_map.items()
            if field_lower in text or text in field_lower
        ]
        return sum(confidences) / len(confidences) if confidences else 0.5

    # ------------------------------------------------------------------
    # Birth Certificate
    # ------------------------------------------------------------------
    def extract_birth_certificate_fields(
        self,
        ocr_text: str,
        text_blocks: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, str], Dict[str, float], Dict[str, bool]]:
        """
        Extract fields from West Bengal Birth Certificate.
        Handles both markdown (Sarvam Vision) and plain-text (Tesseract) output.
        """
        extracted_data: Dict[str, str] = {}
        confidence_scores: Dict[str, float] = {}
        verification_flags: Dict[str, bool] = {}

        confidence_map = self._create_confidence_map(text_blocks)
        print(f"\n🔍 Searching for Birth Certificate fields...")

        # ---- name ----
        name = self._try_patterns(ocr_text, [
            # Markdown: **Name:** John Doe  or  | Name | John Doe |
            r"\*\*Name\*\*\s*[:\|]?\s*\*?\*?([A-Za-z][A-Za-z\s]{2,40})",
            r"\|\s*Name\s*\|\s*([A-Za-z][A-Za-z\s]{2,40})\s*\|",
            # Plain text
            r"(?:^|\n)\s*Name[\s:_]+([A-Za-z][A-Za-z\s]+?)(?=[\"']?\s*Sex|[\"']?\s*\(|\s*$|\n)",
            r"Name[\s:_]+([A-Za-z][A-Za-z\s]{2,40}?)(?=\n|\s*[\"']|$)",
        ])
        # Filter label fragments
        if name and not any(x in name.lower() for x in ["mother", "father", "parent", "sex"]):
            extracted_data["name"] = name.strip()
        else:
            extracted_data["name"] = ""
        confidence_scores["name"] = self._get_field_confidence(extracted_data["name"], confidence_map)
        verification_flags["name"] = confidence_scores["name"] < self.confidence_threshold

        # ---- sex / gender ----
        sex = self._try_patterns(ocr_text, [
            r"\*\*Sex\*\*\s*[:\|]?\s*\*?\*?([Mm]ale|[Ff]emale|[Mm]|[Ff])",
            r"\|\s*Sex\s*\|\s*([Mm]ale|[Ff]emale)\s*\|",
            r"Sex[\s:_'\"]*([Mm]ale|[Ff]emale)",
            r"Gender[\s:_'\"]*([Mm]ale|[Ff]emale)",
        ])
        extracted_data["sex"] = sex.strip().title() if sex else ""
        confidence_scores["sex"] = self._get_field_confidence(sex, confidence_map)
        verification_flags["sex"] = confidence_scores["sex"] < self.confidence_threshold

        # ---- date of birth ----
        dob = self._extract_date(ocr_text, [
            r"\*\*Date\s*of\s*Birth\*\*\s*[:\|]?\s*\*?\*?([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})",
            r"\|\s*Date\s*of\s*Birth\s*\|\s*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})\s*\|",
            r"Date\s*of\s*Birth[\s:_]+([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})",
            r"D\.?O\.?B\.?[\s:_]+([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})",
        ])
        extracted_data["date_of_birth"] = dob
        confidence_scores["date_of_birth"] = self._get_field_confidence(dob, confidence_map)
        verification_flags["date_of_birth"] = confidence_scores["date_of_birth"] < self.confidence_threshold

        # ---- place of birth ----
        place_of_birth = self._try_patterns(ocr_text, [
            r"\*\*Place\s*of\s*Birth\*\*\s*[:\|]?\s*\*?\*?([A-Za-z][A-Za-z\s,\-]+?)(?=\n|\*\*|\|)",
            r"\|\s*Place\s*of\s*Birth\s*\|\s*([A-Za-z][A-Za-z\s,\-]+?)\s*\|",
            r"Place\s*of\s*Birth[\s:_]+([A-Za-z][A-Za-z\s,]+?)(?=\s*\(|\s*Name|\s*Date|\s*$|\n)",
            r"([A-Z][a-z]+)\s+Date\s*of\s*Birth",  # OCR reversal heuristic
        ])
        extracted_data["place_of_birth"] = place_of_birth.strip()
        confidence_scores["place_of_birth"] = self._get_field_confidence(place_of_birth, confidence_map)
        verification_flags["place_of_birth"] = confidence_scores["place_of_birth"] < self.confidence_threshold

        # ---- name of mother ----
        mother_name = self._try_patterns(ocr_text, [
            r"\*\*(?:Name\s*of\s*Mother|Mother'?s?\s*Name)\*\*\s*[:\|]?\s*\*?\*?([A-Za-z][A-Za-z\s]+?)(?=\n|\*\*|\|)",
            r"\|\s*(?:Name\s*of\s*Mother|Mother)\s*\|\s*([A-Za-z][A-Za-z\s]+?)\s*\|",
            r"Name\s*of\s*Mother[\s:_]+([A-Za-z][A-Za-z\s]+?)(?=\s*\(|\s*Name\s*of\s*Father|\s*$|\n)",
            r"Mother'?s?\s*Name[\s:_]+([A-Za-z][A-Za-z\s]+?)(?=\n|\s*Father)",
        ])
        extracted_data["name_of_mother"] = mother_name.strip()
        confidence_scores["name_of_mother"] = self._get_field_confidence(mother_name, confidence_map)
        verification_flags["name_of_mother"] = confidence_scores["name_of_mother"] < self.confidence_threshold

        # ---- name of father ----
        father_name = self._try_patterns(ocr_text, [
            r"\*\*(?:Name\s*of\s*Father|Father'?s?\s*Name)\*\*\s*[:\|]?\s*\*?\*?([A-Za-z][A-Za-z\s]+?)(?=\n|\*\*|\|)",
            r"\|\s*(?:Name\s*of\s*Father|Father)\s*\|\s*([A-Za-z][A-Za-z\s]+?)\s*\|",
            r"Name\s*of\s*Father[\s:_]+([A-Za-z][A-Za-z\s]+?)(?=\s*\(|\s*Address|\s*$|\n)",
            r"Father'?s?\s*Name[\s:_]+([A-Za-z][A-Za-z\s]+?)(?=\n|\s*Address)",
        ])
        extracted_data["name_of_father"] = father_name.strip()
        confidence_scores["name_of_father"] = self._get_field_confidence(father_name, confidence_map)
        verification_flags["name_of_father"] = confidence_scores["name_of_father"] < self.confidence_threshold

        # ---- address of parents at time of birth ----
        address_at_birth = self._try_patterns(ocr_text, [
            r"\*\*Address.*?Birth.*?\*\*\s*[:\|]?\s*([A-Za-z0-9][A-Za-z0-9\s,\-\.]+?)(?=\n\n|\*\*|Permanent)",
            r"\|\s*Address.*?Birth\s*\|\s*([A-Za-z0-9][A-Za-z0-9\s,\-\.]+?)\s*\|",
            r"Address\s*of\s*(?:the\s*)?Parents.*?Birth.*?Child[\s:_]+([A-Za-z0-9][A-Za-z0-9\s,\-\.]+?)(?=\s*Permanent|\s*$|\n\n)",
        ])
        extracted_data["address_of_parents_at_birth"] = address_at_birth.strip()
        confidence_scores["address_of_parents_at_birth"] = self._get_field_confidence(address_at_birth, confidence_map)
        verification_flags["address_of_parents_at_birth"] = confidence_scores["address_of_parents_at_birth"] < self.confidence_threshold

        # ---- permanent address of parents ----
        permanent_address = self._try_patterns(ocr_text, [
            r"\*\*Permanent\s*Address.*?\*\*\s*[:\|]?\s*([A-Za-z0-9][A-Za-z0-9\s,\-\.]+?)(?=\n\n|\*\*|Registration)",
            r"\|\s*Permanent\s*Address\s*\|\s*([A-Za-z0-9][A-Za-z0-9\s,\-\.]+?)\s*\|",
            r"Permanent\s*Address\s*of\s*(?:the\s*)?Parents[\s:_]+([A-Za-z0-9][A-Za-z0-9\s,\-\.]+?)(?=\s*\(|\s*Registration|\s*$|\n\n)",
        ])
        extracted_data["permanent_address_of_parents"] = permanent_address.strip()
        confidence_scores["permanent_address_of_parents"] = self._get_field_confidence(permanent_address, confidence_map)
        verification_flags["permanent_address_of_parents"] = confidence_scores["permanent_address_of_parents"] < self.confidence_threshold

        # ---- registration number ----
        reg_number = self._try_patterns(ocr_text, [
            r"\*\*Registration\s*No\.?\*\*\s*[:\|]?\s*\*?\*?([0-9]+[0-9A-Z\-\/]*)",
            r"\|\s*Registration\s*No\.?\s*\|\s*([0-9A-Z][0-9A-Z\-\/]+?)\s*\|",
            r"Registration\s*No[.\s:_]+([0-9]+[0-9A-Z\-\/]*|[A-Z]+[0-9][0-9A-Z\-\/]*)",
            r"Reg\.?\s*No[.\s:_]+([0-9]+[0-9A-Z\-\/]*)",
        ])
        extracted_data["registration_number"] = reg_number.strip()
        confidence_scores["registration_number"] = self._get_field_confidence(reg_number, confidence_map)
        verification_flags["registration_number"] = confidence_scores["registration_number"] < self.confidence_threshold

        # ---- date of registration ----
        date_of_reg = self._extract_date(ocr_text, [
            r"\*\*Date\s*of\s*Registration\*\*\s*[:\|]?\s*\*?\*?([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})",
            r"\|\s*Date\s*of\s*Registration\s*\|\s*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})\s*\|",
            r"Date\s*of\s*Registration[\s:_]+([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})",
        ])
        extracted_data["date_of_registration"] = date_of_reg
        confidence_scores["date_of_registration"] = self._get_field_confidence(date_of_reg, confidence_map)
        verification_flags["date_of_registration"] = confidence_scores["date_of_registration"] < self.confidence_threshold

        # ---- date of issue ----
        date_of_issue = self._extract_date(ocr_text, [
            r"\*\*Date\s*of\s*Issue\*\*\s*[:\|]?\s*\*?\*?([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})",
            r"\|\s*Date\s*of\s*Issue\s*\|\s*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})\s*\|",
            r"Date\s*of\s*Issu[e]{1,2}[\s:_]+([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})",
        ])
        extracted_data["date_of_issue"] = date_of_issue
        confidence_scores["date_of_issue"] = self._get_field_confidence(date_of_issue, confidence_map)
        verification_flags["date_of_issue"] = confidence_scores["date_of_issue"] < self.confidence_threshold

        # ---- remarks ----
        remarks = self._try_patterns(ocr_text, [
            r"\*\*Remarks\*\*\s*[:\|]?\s*\*?\*?([^\n\|]+)",
            r"\|\s*Remarks\s*\|\s*([^\|]+?)\s*\|",
            r"Remarks[\s:_]+([^\n]+)",
        ])
        extracted_data["remarks"] = remarks.strip()
        confidence_scores["remarks"] = self._get_field_confidence(remarks, confidence_map)
        verification_flags["remarks"] = confidence_scores["remarks"] < self.confidence_threshold

        return extracted_data, confidence_scores, verification_flags

    # ------------------------------------------------------------------
    # Residence Certificate
    # ------------------------------------------------------------------
    def extract_residence_certificate_fields(
        self,
        ocr_text: str,
        text_blocks: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, str], Dict[str, float], Dict[str, bool]]:
        """
        Extract fields from Maharashtra Residence Certificate.
        Handles both markdown (Sarvam Vision) and plain-text (Tesseract) output.
        """
        extracted_data: Dict[str, str] = {}
        confidence_scores: Dict[str, float] = {}
        verification_flags: Dict[str, bool] = {}

        confidence_map = self._create_confidence_map(text_blocks)
        print(f"\n🔍 Searching for Residence Certificate fields...")

        # ---- full name ----
        full_name = self._try_patterns(ocr_text, [
            r"\*\*(?:1\.\s*)?Full\s*Name\*\*\s*[:\|]?\s*\*?\*?([A-Za-z][A-Za-z\s]+?)(?=\n|\*\*|\|)",
            r"\|\s*(?:1\.\s*)?Full\s*Name\s*\|\s*([A-Za-z][A-Za-z\s]+?)\s*\|",
            r"(?:1\.\s*Full\s*Name|Full\s*Name)[\s:_]+([A-Za-z\s]+?)(?:\n|2\.|Father|Husband)",
        ])
        extracted_data["full_name"] = full_name.strip()
        confidence_scores["full_name"] = self._get_field_confidence(full_name, confidence_map)
        verification_flags["full_name"] = confidence_scores["full_name"] < self.confidence_threshold

        # ---- father / husband name ----
        father_husband = self._try_patterns(ocr_text, [
            r"\*\*(?:2\.\s*)?Father\s*/\s*Husband(?:\s*Name)?\*\*\s*[:\|]?\s*\*?\*?([A-Za-z][A-Za-z\s]+?)(?=\n|\*\*|\|)",
            r"\|\s*(?:2\.\s*)?Father\s*/\s*Husband(?:\s*Name)?\s*\|\s*([A-Za-z][A-Za-z\s]+?)\s*\|",
            r"(?:2\.\s*Father\s*/\s*Husband\s*Name|Father.*Husband.*Name)[\s:_]+([A-Za-z\s]+?)(?:\n|3\.|Residential)",
        ])
        extracted_data["father_husband_name"] = father_husband.strip()
        confidence_scores["father_husband_name"] = self._get_field_confidence(father_husband, confidence_map)
        verification_flags["father_husband_name"] = confidence_scores["father_husband_name"] < self.confidence_threshold

        # ---- residential address ----
        address = self._try_patterns(ocr_text, [
            r"\*\*(?:3\.\s*)?Residential\s*Address\*\*\s*[:\|]?\s*\*?\*?([A-Za-z0-9][A-Za-z0-9\s,\-\.\n]+?)(?=\n\n|\*\*(?:4\.|Mobile)|\|4\.)",
            r"\|\s*(?:3\.\s*)?Residential\s*Address\s*\|\s*([A-Za-z0-9][A-Za-z0-9\s,\-\.]+?)\s*\|",
            r"(?:3\.\s*Residential\s*Address|Residential\s*Address)[\s:_]+([A-Za-z0-9\s,\-\.\n]+?)(?:4\.|Mobile\s*Number)",
        ])
        extracted_data["residential_address"] = address.strip()
        confidence_scores["residential_address"] = self._get_field_confidence(address, confidence_map)
        verification_flags["residential_address"] = confidence_scores["residential_address"] < self.confidence_threshold

        # ---- mobile number ----
        mobile = self._try_patterns(ocr_text, [
            r"\*\*(?:4\.\s*)?Mobile\s*(?:Number|No\.?)\*\*\s*[:\|]?\s*\*?\*?([0-9\+\-\s]{7,15})",
            r"\|\s*(?:4\.\s*)?Mobile\s*(?:Number|No\.?)\s*\|\s*([0-9\+\-\s]{7,15}?)\s*\|",
            r"(?:4\.\s*Mobile\s*Number|Mobile\s*Number)[\s:_]+([0-9\+\-\s]+?)(?:\n|5\.|Purpose)",
        ])
        extracted_data["mobile_number"] = re.sub(r"\s+", "", mobile).strip() if mobile else ""
        confidence_scores["mobile_number"] = self._get_field_confidence(mobile, confidence_map)
        verification_flags["mobile_number"] = confidence_scores["mobile_number"] < self.confidence_threshold

        # ---- purpose of certificate ----
        purpose = self._try_patterns(ocr_text, [
            r"\*\*(?:5\.\s*)?Purpose\s*of\s*Certificate\*\*\s*[:\|]?\s*\*?\*?([A-Za-z][A-Za-z\s]+?)(?=\n|\*\*|\|)",
            r"\|\s*(?:5\.\s*)?Purpose\s*of\s*Certificate\s*\|\s*([A-Za-z][A-Za-z\s]+?)\s*\|",
            r"(?:5\.\s*Purpose\s*of\s*Certificate|Purpose\s*of\s*Certificate)[\s:_]+([A-Za-z\s]+?)(?:\n|6\.|Duration)",
        ])
        extracted_data["purpose_of_certificate"] = purpose.strip()
        confidence_scores["purpose_of_certificate"] = self._get_field_confidence(purpose, confidence_map)
        verification_flags["purpose_of_certificate"] = confidence_scores["purpose_of_certificate"] < self.confidence_threshold

        # ---- duration of residence (years) ----
        duration = self._try_patterns(ocr_text, [
            r"\*\*(?:6\.\s*)?Duration\s*of\s*Residence.*?\*\*\s*[:\|]?\s*\*?\*?([0-9]+\s*(?:years?)?)",
            r"\|\s*(?:6\.\s*)?Duration\s*of\s*Residence.*?\|\s*([0-9]+\s*(?:years?)?)\s*\|",
            r"(?:6\.\s*Duration\s*of\s*Residence.*?\(Years\)|Duration\s*of\s*Residence\s*\(Years\))[\s:_]+([0-9]+\s*years?|[0-9]+)",
            r"Duration\s*of\s*Residence.*?[\s:_]+([0-9]+\s*years?|[0-9]+)(?:\s|$|\n)",
        ])
        extracted_data["duration_of_residence_years"] = duration.strip()
        confidence_scores["duration_of_residence_years"] = self._get_field_confidence(duration, confidence_map)
        verification_flags["duration_of_residence_years"] = confidence_scores["duration_of_residence_years"] < self.confidence_threshold

        # ---- date ----
        date_val = self._extract_date(ocr_text, [
            r"\*\*Date\*\*\s*[:\|]?\s*\*?\*?([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})",
            r"\|\s*Date\s*\|\s*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})\s*\|",
            r"(?:^|\n)Date[\s:_]+([0-9\-\/]+)",
        ])
        extracted_data["date"] = date_val
        confidence_scores["date"] = self._get_field_confidence(date_val, confidence_map)
        verification_flags["date"] = confidence_scores["date"] < self.confidence_threshold

        # ---- place ----
        place = self._try_patterns(ocr_text, [
            r"\*\*Place\*\*\s*[:\|]?\s*\*?\*?([A-Za-z][A-Za-z\s]+?)(?=\n|\*\*|\|)",
            r"\|\s*Place\s*\|\s*([A-Za-z][A-Za-z\s]+?)\s*\|",
            r"(?:^|\n)Place[\s:_]+([A-Za-z\s]+?)(?:\n|Applicant|Signature|$)",
        ])
        extracted_data["place"] = place.strip()
        confidence_scores["place"] = self._get_field_confidence(place, confidence_map)
        verification_flags["place"] = confidence_scores["place"] < self.confidence_threshold

        return extracted_data, confidence_scores, verification_flags


def extract_fields(
    form_type: str,
    ocr_text: str,
    text_blocks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Extract structured fields based on form type.

    Args:
        form_type: Type of form (birth_certificate or residence_certificate)
        ocr_text: Full OCR extracted text (may be markdown or plain text)
        text_blocks: OCR text blocks with confidence scores

    Returns:
        Dict: Extracted data with confidence scores and verification flags
    """
    print(f"\n{'='*70}")
    print(f"📊 FIELD EXTRACTION — {form_type.upper()}")
    print(f"{'='*70}")
    print(f"📝 OCR Text Length: {len(ocr_text)} characters")
    print(f"📦 Text Blocks: {len(text_blocks)} blocks")

    extractor = FieldExtractor()

    if form_type == "birth_certificate":
        extracted_data, confidence_scores, verification_flags = \
            extractor.extract_birth_certificate_fields(ocr_text, text_blocks)
    elif form_type == "residence_certificate":
        extracted_data, confidence_scores, verification_flags = \
            extractor.extract_residence_certificate_fields(ocr_text, text_blocks)
    else:
        print(f"❌ Unknown form type: {form_type}")
        return {
            "extracted_data": {},
            "confidence_scores": {},
            "verification_flags": {},
            "error": "Unknown form type"
        }

    # Log results
    print(f"\n✅ EXTRACTION COMPLETE:")
    print(f"   Fields extracted: {len([v for v in extracted_data.values() if v])}/{len(extracted_data)}")
    print(f"\n📋 Extracted Values:")
    for field, value in extracted_data.items():
        if value:
            conf = confidence_scores.get(field, 0.0)
            flag = "⚠️" if verification_flags.get(field, False) else "✓"
            print(f"   {flag} {field:40s} = '{value}' (conf: {conf:.0%})")
        else:
            print(f"   ✗ {field:40s} = (empty)")

    fields_needing_review = [k for k, v in verification_flags.items() if v]
    if fields_needing_review:
        print(f"\n⚠️  Fields Needing Review ({len(fields_needing_review)}):")
        for field in fields_needing_review:
            print(f"   - {field}")

    return {
        "extracted_data": extracted_data,
        "confidence_scores": confidence_scores,
        "verification_flags": verification_flags
    }
