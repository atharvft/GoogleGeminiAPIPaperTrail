"""
============================================================
 PaperTrail — Government Form Extraction using Gemini API
============================================================
 MODEL   : gemini-2.5-flash  (FREE tier — no credit card)
 FREE LIMITS: 10 requests/min · 250 requests/day
 SUPPORTS:
   1. West Bengal Birth Certificate  (English + Bengali)
   2. Maharashtra Residence Certificate (English)

 SETUP (run once in VS Code terminal):
   pip install google-generativeai pillow

 GET FREE API KEY (no credit card needed):
   https://aistudio.google.com/app/apikey

 HOW TO RUN:
   python extract_forms.py
   → it will ask you for the image path and form type

 OR pass image directly:
   python extract_forms.py path/to/filled_form.jpg
============================================================
"""

import google.generativeai as genai
from PIL import Image
import json
import os
import sys


# ──────────────────────────────────────────────────────────
#  STEP 1 — PASTE YOUR FREE GEMINI API KEY HERE
#  Get it free at: https://aistudio.google.com/app/apikey
# ──────────────────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyC1Ev2EBT-8aUfiBpIMIGlZKveym42NDIk"

# gemini-2.5-flash = free, vision-capable, best on free tier (March 2026)
GEMINI_MODEL = "gemini-2.5-flash"


# ──────────────────────────────────────────────────────────
#  PROMPT 1 — WEST BENGAL BIRTH CERTIFICATE
# ──────────────────────────────────────────────────────────
BIRTH_CERTIFICATE_PROMPT = """
You are an expert OCR system that extracts data from Indian government forms.

This image is a filled handwritten WEST BENGAL GOVERNMENT BIRTH CERTIFICATE
issued by the Department of Health & Family Welfare.

The printed labels are in English and Bengali.
The handwritten values filled by the applicant may be in English, Bengali, or both.

YOUR TASK:
- Read the form carefully.
- Extract ONLY the handwritten or filled-in values — NOT the printed label text.
- If a field is blank or not filled, set its value to null.
- If handwriting is unclear but you can make a reasonable guess, extract it and set "uncertain": true.
- If you cannot read something at all, set value to null and "uncertain": true.

EXTRACT THESE EXACT FIELDS:

1.  name                  — Child's full name written after the "Name:" label
2.  sex                   — Male / Female written after the "Sex:" label
3.  date_of_birth         — Written after "Date of Birth:" — use DD/MM/YYYY format if possible
4.  place_of_birth        — Written after "Place of Birth:"
5.  name_of_mother        — Written after "Name of Mother:"
6.  name_of_father        — Written after "Name of Father:"
7.  address_at_birth      — Written after "Address of the Parents at the time of Birth of the Child:"
8.  permanent_address     — Written after "Permanent Address of the Parents:"
9.  registration_no       — Written after "Registration No:"
10. date_of_registration  — Written after "Date of Registration:"
11. date_of_issue         — Written after "Date of Issue:"
12. local_area_body       — Written in the blank after "(Local Area/Local Body)" near the top

OUTPUT RULES:
- Return ONLY a raw valid JSON object.
- Do NOT include markdown, code fences, or any explanation.
- Start your response with { and end with }

{
  "form_type": "Birth Certificate",
  "state": "West Bengal",
  "department": "Department of Health and Family Welfare",
  "fields": {
    "name":                 { "value": "...", "uncertain": false },
    "sex":                  { "value": "...", "uncertain": false },
    "date_of_birth":        { "value": "...", "uncertain": false },
    "place_of_birth":       { "value": "...", "uncertain": false },
    "name_of_mother":       { "value": "...", "uncertain": false },
    "name_of_father":       { "value": "...", "uncertain": false },
    "address_at_birth":     { "value": "...", "uncertain": false },
    "permanent_address":    { "value": "...", "uncertain": false },
    "registration_no":      { "value": "...", "uncertain": false },
    "date_of_registration": { "value": "...", "uncertain": false },
    "date_of_issue":        { "value": "...", "uncertain": false },
    "local_area_body":      { "value": "...", "uncertain": false }
  }
}
"""


# ──────────────────────────────────────────────────────────
#  PROMPT 2 — MAHARASHTRA RESIDENCE CERTIFICATE
# ──────────────────────────────────────────────────────────
RESIDENCE_CERTIFICATE_PROMPT = """
You are an expert OCR system that extracts data from Indian government forms.

This image is a filled handwritten GOVERNMENT OF MAHARASHTRA STATE
APPLICATION FOR RESIDENCE CERTIFICATE.

The printed labels are in English.
The handwritten values filled by the applicant may be in English or Marathi.

YOUR TASK:
- Read the form carefully.
- Extract ONLY the handwritten or filled-in values — NOT the printed label text.
- If a field is blank or not filled, set its value to null.
- If handwriting is unclear but you can make a reasonable guess, extract it and set "uncertain": true.
- If you cannot read something at all, set value to null and "uncertain": true.
- For Residential Address — it may span 2 lines, combine them into one string.

EXTRACT THESE EXACT FIELDS:

1. full_name               — Written after "1. Full Name:"
2. father_husband_name     — Written after "2. Father / Husband Name:"
3. residential_address     — Written after "3. Residential Address:" (may be 2 lines)
4. mobile_number           — Written after "4. Mobile Number:"
5. purpose_of_certificate  — Written after "5. Purpose of Certificate:"
6. duration_of_residence   — Number of years written after "6. Duration of Residence (Years):"
7. date                    — Written after "Date:" at the bottom of the form
8. place                   — Written after "Place:" at the bottom of the form

OUTPUT RULES:
- Return ONLY a raw valid JSON object.
- Do NOT include markdown, code fences, or any explanation.
- Start your response with { and end with }

{
  "form_type": "Residence Certificate Application",
  "state": "Maharashtra",
  "department": "Government of Maharashtra State",
  "fields": {
    "full_name":              { "value": "...", "uncertain": false },
    "father_husband_name":    { "value": "...", "uncertain": false },
    "residential_address":    { "value": "...", "uncertain": false },
    "mobile_number":          { "value": "...", "uncertain": false },
    "purpose_of_certificate": { "value": "...", "uncertain": false },
    "duration_of_residence":  { "value": "...", "uncertain": false },
    "date":                   { "value": "...", "uncertain": false },
    "place":                  { "value": "...", "uncertain": false }
  }
}
"""


# ──────────────────────────────────────────────────────────
#  PROMPT 3 — AUTO-DETECT (unknown form)
# ──────────────────────────────────────────────────────────
AUTO_DETECT_PROMPT = """
You are an expert OCR system that extracts data from Indian government forms.

STEP 1 — Read the title or header text of this form to identify what it is.
STEP 2 — Extract ALL handwritten or filled-in values from every field on the form.

RULES:
- Extract ONLY values written by the applicant — NOT the printed label text itself.
- If a field is empty, set value to null.
- If handwriting is unclear but guessable, extract it and set "uncertain": true.
- Use the printed label text as the JSON key (convert to snake_case, lowercase).

OUTPUT RULES:
- Return ONLY a raw valid JSON object.
- Do NOT include markdown, code fences, or any explanation.
- Start your response with { and end with }

{
  "form_type": "name of form from header",
  "state": "state name from header",
  "department": "department from header",
  "detected_languages": "e.g. English and Bengali",
  "fields": {
    "field_name_snake_case": { "value": "extracted value or null", "uncertain": false }
  }
}
"""


# ──────────────────────────────────────────────────────────
#  CORE EXTRACTION FUNCTION
# ──────────────────────────────────────────────────────────
def extract_form_data(image_path: str, form_type: str = "auto") -> dict:
    """
    Sends image to Gemini 2.5 Flash and returns extracted fields as a dict.

    Args:
        image_path : path to filled form image (JPG / PNG / WEBP)
        form_type  : 'birth_certificate' | 'residence_certificate' | 'auto'

    Returns:
        dict with extracted fields
    """

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    print(f"\n  📂  Image  : {image_path}")
    img = Image.open(image_path)
    print(f"  📐  Size   : {img.size[0]} x {img.size[1]} px")

    # Auto-detect form type if not specified
    if form_type == "auto":
        print("  🔍  Auto-detecting form type...")
        detect_prompt = (
            "Look at this government form image. Read only the title/header. "
            "Reply with EXACTLY one of these words only — nothing else:\n"
            "  birth_certificate\n"
            "  residence_certificate\n"
            "  unknown"
        )
        r = model.generate_content([detect_prompt, img])
        detected = r.text.strip().lower()
        if "birth" in detected:
            form_type = "birth_certificate"
        elif "residence" in detected:
            form_type = "residence_certificate"
        else:
            form_type = "unknown"
        print(f"  ✅  Detected: {form_type}")

    # Select prompt
    if form_type == "birth_certificate":
        prompt = BIRTH_CERTIFICATE_PROMPT
        print("  📋  Prompt : West Bengal Birth Certificate")
    elif form_type == "residence_certificate":
        prompt = RESIDENCE_CERTIFICATE_PROMPT
        print("  📋  Prompt : Maharashtra Residence Certificate")
    else:
        prompt = AUTO_DETECT_PROMPT
        print("  📋  Prompt : Auto-detect (unknown form)")

    # Send to Gemini
    print("  🤖  Calling Gemini 2.5 Flash...")
    response = model.generate_content(
        contents=[prompt, img],
        generation_config=genai.GenerationConfig(
            temperature=0.1,        # Low = deterministic factual extraction
            max_output_tokens=2048,
        )
    )

    raw = response.text.strip()

    # Strip accidental markdown code fences
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]).strip()

    # Parse JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("\n  ⚠️  Gemini returned non-JSON output. Saving raw response.")
        return {
            "form_type": "parse_error",
            "raw_gemini_response": raw,
            "parse_error": True
        }


# ──────────────────────────────────────────────────────────
#  DISPLAY RESULTS IN TERMINAL
# ──────────────────────────────────────────────────────────
def display_results(data: dict):
    print("\n" + "═" * 64)
    print("   EXTRACTED FORM DATA")
    print("═" * 64)

    if data.get("parse_error"):
        print("  ❌ Could not parse Gemini response as JSON.")
        print("  Raw output:")
        print(data.get("raw_gemini_response", ""))
        return

    print(f"  Form      : {data.get('form_type', '—')}")
    print(f"  State     : {data.get('state', '—')}")
    print(f"  Dept      : {data.get('department', '—')}")
    if "detected_languages" in data:
        print(f"  Languages : {data.get('detected_languages', '—')}")
    print("─" * 64)

    fields      = data.get("fields", {})
    need_review = []

    for key, info in fields.items():
        label     = key.replace("_", " ").title()
        value     = info.get("value")
        uncertain = info.get("uncertain", False)

        if value is None:
            icon    = "⬜"
            display = "(blank — not filled by applicant)"
        elif uncertain:
            icon    = "⚠️ "
            display = str(value)
            need_review.append(label)
        else:
            icon    = "✅"
            display = str(value)

        print(f"  {icon}  {label:<34}  {display}")

    print("─" * 64)

    total  = len(fields)
    filled = sum(1 for f in fields.values() if f.get("value") is not None)
    blank  = total - filled

    if need_review:
        print(f"\n  ⚠️  Needs human review ({len(need_review)} fields):")
        for f in need_review:
            print(f"      → {f}")

    print(f"\n  📊  {filled}/{total} fields extracted")
    print(f"      {blank} blank  |  {len(need_review)} flagged for review")
    print("═" * 64)


# ──────────────────────────────────────────────────────────
#  SAVE JSON
# ──────────────────────────────────────────────────────────
def save_json(data: dict, image_path: str) -> str:
    out_path = os.path.splitext(image_path)[0] + "_extracted.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  💾  Saved : {out_path}")
    return out_path


# ──────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║    PaperTrail — Gemini 2.5 Flash Form Extractor          ║")
    print("║    FREE model · No credit card · 250 req/day free        ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # Validate API key
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print()
        print("  ❌  API key missing!")
        print()
        print("  Steps to fix:")
        print("  1. Go to https://aistudio.google.com/app/apikey")
        print("  2. Click 'Create API Key' (free, no credit card)")
        print("  3. Copy the key")
        print("  4. Open extract_forms.py in VS Code")
        print("  5. Replace YOUR_GEMINI_API_KEY_HERE with your key")
        sys.exit(1)

    # Get image path
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        print()
        print("  Enter the path to your filled form image:")
        print("  Examples:")
        print("    ./filled_birth_cert.jpg")
        print("    C:\\Users\\You\\Desktop\\form.png")
        image_path = input("\n  Image path: ").strip().strip('"').strip("'")

    # Get form type
    print()
    print("  Select form type:")
    print("    1  →  West Bengal Birth Certificate")
    print("    2  →  Maharashtra Residence Certificate")
    print("    Enter  →  Auto-detect from the image")
    choice = input("\n  Your choice [1 / 2 / Enter]: ").strip()

    form_type = {
        "1": "birth_certificate",
        "2": "residence_certificate",
        "":  "auto",
    }.get(choice, "auto")

    # Run
    print()
    print("─" * 64)
    try:
        data = extract_form_data(image_path, form_type)
        display_results(data)
        save_json(data, image_path)

        print()
        print("  📄  Full JSON output:")
        print("─" * 64)
        print(json.dumps(data, ensure_ascii=False, indent=2))

    except FileNotFoundError as e:
        print(f"\n  ❌  {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ❌  Error: {e}")
        raise


if __name__ == "__main__":
    main()