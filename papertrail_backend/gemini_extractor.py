"""
Gemini API form extraction module for PaperTrail.
Integrates Google's Gemini 2.5 Flash for vision-based OCR extraction.
"""

import os
import json
from typing import Dict, Optional
from PIL import Image

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  google-generativeai not installed. Gemini extraction disabled.")


GEMINI_MODEL = "gemini-2.5-flash"

BIRTH_CERTIFICATE_PROMPT = """
You are an expert OCR system that extracts data from Indian government forms.

This image is a filled handwritten WEST BENGAL GOVERNMENT BIRTH CERTIFICATE
issued by the Department of Health & Family Welfare.

The printed labels are in English and Bengali.
The handwritten values filled by the applicant may be in English, Bengali, or both.

YOUR TASK:
- Read the form carefully.
- Extract ONLY the handwritten or filled-in values — NOT the printed label text.
- If a field is blank or not filled, set its value to empty string "".
- If handwriting is unclear but you can make a reasonable guess, extract it.

EXTRACT THESE EXACT FIELDS:
1.  name                  — Child's full name
2.  sex                   — Male / Female
3.  date_of_birth         — Use DD/MM/YYYY format if possible
4.  place_of_birth        — Place name
5.  name_of_mother        — Mother's name
6.  name_of_father        — Father's name
7.  address_of_parents_at_birth — Address at birth
8.  permanent_address_of_parents — Permanent address
9.  registration_number   — Registration number
10. date_of_registration  — Registration date
11. date_of_issue         — Issue date
12. remarks               — Any remarks

OUTPUT RULES:
- Return ONLY a raw valid JSON object.
- Do NOT include markdown, code fences, or any explanation.
- Start your response with { and end with }

{
  "name": "...",
  "sex": "...",
  "date_of_birth": "...",
  "place_of_birth": "...",
  "name_of_mother": "...",
  "name_of_father": "...",
  "address_of_parents_at_birth": "...",
  "permanent_address_of_parents": "...",
  "registration_number": "...",
  "date_of_registration": "...",
  "date_of_issue": "...",
  "remarks": ""
}
"""

RESIDENCE_CERTIFICATE_PROMPT = """
You are an expert OCR system that extracts data from Indian government forms.

This image is a filled handwritten GOVERNMENT OF MAHARASHTRA STATE
APPLICATION FOR RESIDENCE CERTIFICATE.

The printed labels are in English.
The handwritten values filled by the applicant may be in English or Marathi.

YOUR TASK:
- Read the form carefully.
- Extract ONLY the handwritten or filled-in values — NOT the printed label text.
- If a field is blank or not filled, set its value to empty string "".
- For Residential Address — it may span 2 lines, combine them into one string.

EXTRACT THESE EXACT FIELDS:
1. full_name               — Full Name
2. father_husband_name     — Father / Husband Name
3. residential_address     — Residential Address (may be 2 lines)
4. mobile_number           — Mobile Number
5. purpose_of_certificate  — Purpose of Certificate
6. duration_of_residence_years — Duration of Residence (Years)
7. date                    — Date at bottom
8. place                   — Place at bottom

OUTPUT RULES:
- Return ONLY a raw valid JSON object.
- Do NOT include markdown, code fences, or any explanation.
- Start your response with { and end with }

{
  "full_name": "...",
  "father_husband_name": "...",
  "residential_address": "...",
  "mobile_number": "...",
  "purpose_of_certificate": "...",
  "duration_of_residence_years": "...",
  "date": "...",
  "place": ""
}
"""


def extract_with_gemini(
    image_path: str,
    form_type: str,
    gemini_api_key: Optional[str] = None
) -> Dict:
    """
    Extract form data using Gemini 2.5 Flash vision model.
    
    Args:
        image_path: Path to the form image
        form_type: 'birth_certificate' or 'residence_certificate'
        gemini_api_key: Gemini API key (reads from env if not provided)
        
    Returns:
        Dict with extracted fields and metadata
    """
    if not GEMINI_AVAILABLE:
        return {
            "success": False,
            "error": "google-generativeai package not installed",
            "extracted_data": {}
        }
    
    # Get API key
    api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY not configured",
            "extracted_data": {}
        }
    
    if not os.path.exists(image_path):
        return {
            "success": False,
            "error": f"Image not found: {image_path}",
            "extracted_data": {}
        }
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        img = Image.open(image_path)
        print(f"[GeminiExtractor] Image size: {img.size[0]} x {img.size[1]} px")
        
        # Select prompt
        if form_type == "birth_certificate":
            prompt = BIRTH_CERTIFICATE_PROMPT
            print(f"[GeminiExtractor] Using Birth Certificate prompt")
        elif form_type == "residence_certificate":
            prompt = RESIDENCE_CERTIFICATE_PROMPT
            print(f"[GeminiExtractor] Using Residence Certificate prompt")
        else:
            return {
                "success": False,
                "error": f"Unsupported form_type: {form_type}",
                "extracted_data": {}
            }
        
        # Call Gemini
        print(f"[GeminiExtractor] Calling Gemini 2.5 Flash...")
        response = model.generate_content(
            contents=[prompt, img],
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=2048,
            )
        )
        
        raw = response.text.strip()
        
        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1]).strip()
        
        # Parse JSON
        extracted_data = json.loads(raw)
        
        print(f"[GeminiExtractor] ✅ Extracted {len(extracted_data)} fields")
        
        return {
            "success": True,
            "extracted_data": extracted_data,
            "method": "gemini_vision",
            "model": GEMINI_MODEL,
            "confidence": 0.95  # Gemini is generally high confidence
        }
        
    except json.JSONDecodeError as e:
        print(f"[GeminiExtractor] ❌ JSON parse error: {e}")
        return {
            "success": False,
            "error": "Gemini returned invalid JSON",
            "raw_response": raw if 'raw' in locals() else "",
            "extracted_data": {}
        }
    except Exception as e:
        print(f"[GeminiExtractor] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "extracted_data": {}
        }
