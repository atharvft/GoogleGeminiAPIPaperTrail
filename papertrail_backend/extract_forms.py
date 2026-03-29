"""
============================================================
 PaperTrail — Gemini 2.5 Flash + MongoDB Storage
============================================================
 Extracts form data using Gemini Vision API and saves
 directly to MongoDB using your existing database.py functions.

 COLLECTIONS USED (already defined in your database.py):
   Birth Certificate   → civil_records_department
   Residence Cert      → citizen_services_department
   Every save          → audit_logs (auto)

 SETUP:
   pip install google-genai pillow pymongo
============================================================
"""

from google import genai
from google.genai import types
from PIL import Image
import json, os, sys, shutil
from datetime import datetime

# ── Import YOUR existing database functions ───────────────
# No changes needed in database.py — we just call its functions
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from papertrail_backend.database import (
    save_birth_certificate,
    save_residence_certificate,
    save_audit_log,
)


# ──────────────────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────────────────
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
GEMINI_MODEL   = "gemini-2.5-flash"

UPLOAD_FOLDER  = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ──────────────────────────────────────────────────────────
#  PROMPT 1 — WEST BENGAL BIRTH CERTIFICATE
# ──────────────────────────────────────────────────────────
BIRTH_CERTIFICATE_PROMPT = """
You are an expert OCR system that extracts data from Indian government forms.

This image is a filled handwritten WEST BENGAL GOVERNMENT BIRTH CERTIFICATE
issued by the Department of Health & Family Welfare.

Printed labels are in English and Bengali.
Handwritten values may be in English, Bengali, or both.

YOUR TASK:
- Extract ONLY the handwritten or filled-in values — NOT the printed label text.
- If a field is blank, set value to null.
- If handwriting is unclear but guessable, extract it and set "uncertain": true.
- If completely unreadable, set value to null and "uncertain": true.

EXTRACT THESE FIELDS:
1.  name                  — Child's name written after "Name:" label
2.  sex                   — Male/Female written after "Sex:" label
3.  date_of_birth         — Written after "Date of Birth:" in DD/MM/YYYY
4.  place_of_birth        — Written after "Place of Birth:"
5.  name_of_mother        — Written after "Name of Mother:"
6.  name_of_father        — Written after "Name of Father:"
7.  address_at_birth      — Written after "Address of the Parents at the time of Birth..."
8.  permanent_address     — Written after "Permanent Address of the Parents:"
9.  registration_no       — Written after "Registration No:"
10. date_of_registration  — Written after "Date of Registration:"
11. date_of_issue         — Written after "Date of Issue:"
12. local_area_body       — Written after "(Local Area/Local Body)" near top

Return ONLY raw JSON. No markdown. No explanation. Start with { end with }.

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

Printed labels are in English.
Handwritten values may be in English or Marathi.

YOUR TASK:
- Extract ONLY the handwritten or filled-in values — NOT the printed label text.
- If a field is blank, set value to null.
- If handwriting is unclear but guessable, extract it and set "uncertain": true.
- For Residential Address — may span 2 lines, join into one string.

EXTRACT THESE FIELDS:
1. full_name               — Written after "1. Full Name:"
2. father_husband_name     — Written after "2. Father / Husband Name:"
3. residential_address     — Written after "3. Residential Address:" (may be 2 lines)
4. mobile_number           — Written after "4. Mobile Number:"
5. purpose_of_certificate  — Written after "5. Purpose of Certificate:"
6. duration_of_residence   — Written after "6. Duration of Residence (Years):"
7. date                    — Written after "Date:" at bottom
8. place                   — Written after "Place:" at bottom

Return ONLY raw JSON. No markdown. No explanation. Start with { end with }.

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
#  HELPER — Parse Gemini fields into what database.py expects
#
#  Gemini returns:
#    { "name": { "value": "Ramesh", "uncertain": false } }
#
#  database.py save functions expect two flat dicts:
#    extracted_data    = { "name": "Ramesh" }
#    confidence_scores = { "name": 0.95 }
# ──────────────────────────────────────────────────────────
def parse_gemini_fields(gemini_fields: dict) -> tuple:
    extracted_data    = {}
    confidence_scores = {}

    for field_key, field_info in gemini_fields.items():
        value     = field_info.get("value")
        uncertain = field_info.get("uncertain", False)

        extracted_data[field_key] = value

        # Confidence score based on uncertainty flag
        if value is None:
            confidence_scores[field_key] = 0.0    # blank field
        elif uncertain:
            confidence_scores[field_key] = 0.45   # extracted but unsure
        else:
            confidence_scores[field_key] = 0.95   # confident extraction

    return extracted_data, confidence_scores


# ──────────────────────────────────────────────────────────
#  Copy image into uploads/ folder with timestamp filename
# ──────────────────────────────────────────────────────────
def save_image_to_uploads(original_path: str) -> str:
    ext       = os.path.splitext(original_path)[1]
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename  = f"form_{timestamp}{ext}"
    dest      = os.path.join(UPLOAD_FOLDER, filename)
    shutil.copy2(original_path, dest)
    return dest


# ──────────────────────────────────────────────────────────
#  GEMINI EXTRACTION
# ──────────────────────────────────────────────────────────
def extract_form_data(image_path: str, form_type: str = "auto") -> dict:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    client = genai.Client(api_key=GEMINI_API_KEY)

    print(f"\n  📂  Image  : {image_path}")
    img = Image.open(image_path)
    print(f"  📐  Size   : {img.size[0]} x {img.size[1]} px")

    # Auto-detect
    if form_type == "auto":
        print("  🔍  Auto-detecting form type...")
        r = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                "Read only the title/header of this form. Reply with EXACTLY one word:\n"
                "birth_certificate\nresidence_certificate\nunknown",
                img
            ],
        )
        detected = r.text.strip().lower()
        form_type = (
            "birth_certificate"    if "birth"     in detected else
            "residence_certificate" if "residence" in detected else
            "unknown"
        )
        print(f"  ✅  Detected: {form_type}")

    if form_type == "birth_certificate":
        prompt = BIRTH_CERTIFICATE_PROMPT
        print("  📋  Prompt : West Bengal Birth Certificate")
    elif form_type == "residence_certificate":
        prompt = RESIDENCE_CERTIFICATE_PROMPT
        print("  📋  Prompt : Maharashtra Residence Certificate")
    else:
        return {"parse_error": True, "error": "Unknown form type"}

    print("  🤖  Calling Gemini 2.5 Flash...")
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt, img],
        config=types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=2048,
        )
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.splitlines()[1:-1]).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"form_type": "parse_error", "raw_gemini_response": raw, "parse_error": True}


# ──────────────────────────────────────────────────────────
#  SAVE TO MONGODB
#  Calls your existing database.py functions directly
# ──────────────────────────────────────────────────────────
def save_to_mongodb(gemini_result: dict, image_path: str) -> str | None:
    """
    Saves extracted Gemini data into MongoDB.

    Routing:
      Birth Certificate   → civil_records_department     (save_birth_certificate)
      Residence Cert      → citizen_services_department  (save_residence_certificate)
      Both automatically  → audit_logs                   (inside save_* functions)
    """
    if gemini_result.get("parse_error"):
        print("  ⚠️  Skipping DB save — parse error.")
        return None

    form_type = gemini_result.get("form_type", "").lower()
    fields    = gemini_result.get("fields", {})

    if not fields:
        print("  ⚠️  No fields found — skipping DB save.")
        return None

    # Convert Gemini fields → flat dicts
    extracted_data, confidence_scores = parse_gemini_fields(fields)

    # Copy image to uploads folder
    stored_path = save_image_to_uploads(image_path)

    try:
        if "birth" in form_type:
            form_id = save_birth_certificate(
                image_path        = stored_path,
                extracted_data    = extracted_data,
                confidence_scores = confidence_scores,
            )
            collection_name = "civil_records_department"

        elif "residence" in form_type:
            form_id = save_residence_certificate(
                image_path        = stored_path,
                extracted_data    = extracted_data,
                confidence_scores = confidence_scores,
            )
            collection_name = "citizen_services_department"

        else:
            print(f"  ⚠️  Unknown form_type '{form_type}' — skipping.")
            return None

        print(f"\n  ✅  Saved to MongoDB")
        print(f"  🗂️   Collection : {collection_name}")
        print(f"  🔑  Document ID : {form_id}")
        print(f"  📌  Status      : pending_verification")
        return form_id

    except Exception as e:
        print(f"\n  ❌  MongoDB save failed: {e}")
        return None


# ──────────────────────────────────────────────────────────
#  DISPLAY IN TERMINAL
# ──────────────────────────────────────────────────────────
def display_results(data: dict):
    print("\n" + "═" * 64)
    print("   EXTRACTED FORM DATA")
    print("═" * 64)

    if data.get("parse_error"):
        print("  ❌  Parse failed.")
        print(data.get("raw_gemini_response", ""))
        return

    print(f"  Form   : {data.get('form_type', '—')}")
    print(f"  State  : {data.get('state', '—')}")
    print(f"  Dept   : {data.get('department', '—')}")
    print("─" * 64)

    fields      = data.get("fields", {})
    need_review = []

    for key, info in fields.items():
        label     = key.replace("_", " ").title()
        value     = info.get("value")
        uncertain = info.get("uncertain", False)

        if value is None:
            icon, display = "⬜", "(blank)"
        elif uncertain:
            icon, display = "⚠️ ", str(value)
            need_review.append(label)
        else:
            icon, display = "✅", str(value)

        print(f"  {icon}  {label:<34}  {display}")

    print("─" * 64)
    total  = len(fields)
    filled = sum(1 for f in fields.values() if f.get("value") is not None)
    print(f"  📊  {filled}/{total} fields extracted  |  {len(need_review)} need review")
    print("═" * 64)


# ──────────────────────────────────────────────────────────
#  SAVE LOCAL JSON
# ──────────────────────────────────────────────────────────
def save_json(data: dict, image_path: str):
    out = os.path.splitext(image_path)[0] + "_extracted.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  💾  JSON saved : {out}")


# ──────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   PaperTrail — Gemini 2.5 Flash + MongoDB Storage        ║")
    print("╚══════════════════════════════════════════════════════════╝")

    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("\n  ❌  Set GEMINI_API_KEY in the script.")
        print("  → https://aistudio.google.com/app/apikey")
        sys.exit(1)

    # Image path
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        print()
        print("  Enter path to your filled form image:")
        image_path = input("  Image path: ").strip().strip('"').strip("'")

    # Form type
    print()
    print("  Select form type:")
    print("    1  →  West Bengal Birth Certificate")
    print("    2  →  Maharashtra Residence Certificate")
    print("    Enter  →  Auto-detect")
    choice = input("\n  Choice [1 / 2 / Enter]: ").strip()
    form_type = {"1": "birth_certificate", "2": "residence_certificate", "": "auto"}.get(choice, "auto")

    print("\n" + "─" * 64)

    try:
        # ── Step 1: Extract with Gemini ──────────────────────
        data = extract_form_data(image_path, form_type)

        # ── Step 2: Show in terminal ─────────────────────────
        display_results(data)

        # ── Step 3: Save to MongoDB ──────────────────────────
        print("\n  💾  Saving to MongoDB...")
        form_id = save_to_mongodb(data, image_path)

        if form_id:
            print(f"\n  🎉  Done! Document stored successfully.")
        else:
            print("\n  ⚠️  MongoDB save was skipped.")

        # ── Step 4: Save local JSON ──────────────────────────
        save_json(data, image_path)

        # ── Step 5: Print full JSON ──────────────────────────
        print()
        print("  📄  Full extracted JSON:")
        print("─" * 64)
        print(json.dumps(data, ensure_ascii=False, indent=2))

    except FileNotFoundError as e:
        print(f"\n  ❌  {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ❌  {e}")
        raise


if __name__ == "__main__":
    main()