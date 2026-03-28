"""
PaperTrail Backend – Flask API
Simulates OCR extraction, form classification, and routing pipeline.
"""

import os
import json
import uuid
import random
import shutil
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image, ImageEnhance, ImageFilter

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory audit store
audit_records = []

# ────────────────────────────────────────────────────────────
# Mock OCR Data
# ────────────────────────────────────────────────────────────
MOCK_OCR_NAMES = [
    ("Rajesh Kumar Sharma", 0.92),
    ("Priya Nair", 0.78),
    ("Mohammed Salim Khan", 0.61),
    ("Sunita Devi Yadav", 0.88),
    ("Arun Venkatesh", 0.45),
]
MOCK_OCR_DOBS = [
    ("15/08/1985", 0.95),
    ("03/01/1990", 0.72),
    ("27/11/1978", 0.58),
    ("09/04/2001", 0.84),
    ("21/07/1995", 0.41),
]
MOCK_OCR_ADDRESSES = [
    ("12, Gandhi Nagar, Pune, Maharashtra – 411001", 0.80),
    ("Flat 4B, Nehru Colony, Chennai, TN – 600020", 0.63),
    ("H.No. 7, Sector 15, Gurgaon, HR – 122001", 0.38),
    ("Village Rampur, Dist. Varanasi, UP – 221103", 0.71),
    ("Plot 22, MG Road, Bengaluru, KA – 560001", 0.90),
]
MOCK_OCR_IDS = [
    ("MH-2318-5574-9921", 0.97),
    ("TN-0042-8871-3301", 0.76),
    ("HR-9917-2243-0045", 0.52),
    ("UP-1156-7734-8820", 0.66),
    ("KA-4423-1198-7700", 0.43),
]

FORM_TYPES = [
    "birth_certificate",
    "residence_certificate",
]

DEPARTMENT_MAP = {
    "birth_certificate": "Civil Records Department",
    "residence_certificate": "Local Administration Department",
}


def classify_from_text(filename: str) -> str:
    """Naive simulation: pick form type from filename keywords."""
    name = filename.lower()
    if "birth" in name:
        return FORM_TYPES[0]
    elif "residence" in name or "address" in name:
        return FORM_TYPES[1]
    else:
        return FORM_TYPES[0]


def simulate_preprocess(src_path: str, dest_path: str):
    """Apply simple image transformations to simulate preprocessing."""
    try:
        img = Image.open(src_path).convert("RGB")
        # Grayscale
        img = img.convert("L")
        # Noise reduction (blur then sharpen)
        img = img.filter(ImageFilter.MedianFilter(size=3))
        img = img.filter(ImageFilter.SHARPEN)
        # Contrast boost
        enhancer = ImageEnhance.Contrast(img.convert("RGB"))
        img = enhancer.enhance(1.6)
        # Brightness correction
        bright = ImageEnhance.Brightness(img)
        img = bright.enhance(1.1)
        img.save(dest_path)
    except Exception:
        # If image processing fails, just copy the file
        shutil.copy2(src_path, dest_path)


# ────────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────────

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/upload-form", methods=["POST"])
def upload_form():
    """Accept image file, save original + preprocessed versions."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
        return jsonify({"error": "Unsupported file format"}), 400

    form_id = str(uuid.uuid4())[:8].upper()
    original_name = f"{form_id}_original{ext}"
    processed_name = f"{form_id}_processed{ext}"

    original_path = os.path.join(UPLOAD_FOLDER, original_name)
    processed_path = os.path.join(UPLOAD_FOLDER, processed_name)

    file.save(original_path)
    simulate_preprocess(original_path, processed_path)

    return jsonify({
        "form_id": form_id,
        "original_image": f"/uploads/{original_name}",
        "processed_image": f"/uploads/{processed_name}",
        "message": "Form uploaded and preprocessed successfully",
    })


@app.route("/extract-fields", methods=["POST"])
def extract_fields():
    """Return mock OCR-extracted fields with confidence scores."""
    data = request.get_json(silent=True) or {}
    idx = random.randint(0, 4)

    name_val, name_conf = MOCK_OCR_NAMES[idx]
    dob_val, dob_conf = MOCK_OCR_DOBS[idx]
    addr_val, addr_conf = MOCK_OCR_ADDRESSES[idx]
    id_val, id_conf = MOCK_OCR_IDS[idx]

    return jsonify({
        "form_id": data.get("form_id", "UNKNOWN"),
        "extracted_fields": {
            "full_name":    {"value": name_val, "confidence": round(name_conf, 2)},
            "date_of_birth": {"value": dob_val, "confidence": round(dob_conf, 2)},
            "address":      {"value": addr_val, "confidence": round(addr_conf, 2)},
            "id_number":    {"value": id_val,   "confidence": round(id_conf, 2)},
        },
        "overall_confidence": round((name_conf + dob_conf + addr_conf + id_conf) / 4, 2),
    })


@app.route("/classify-form", methods=["POST"])
def classify_form():
    """Return predicted form category and routing department."""
    data = request.get_json(silent=True) or {}
    filename = data.get("filename", "")
    form_type = classify_from_text(filename)
    department = DEPARTMENT_MAP[form_type]

    return jsonify({
        "form_id": data.get("form_id", "UNKNOWN"),
        "form_type": form_type,
        "department": department,
        "confidence": round(random.uniform(0.72, 0.97), 2),
    })


@app.route("/submit-verified", methods=["POST"])
def submit_verified():
    """Store the final corrected form record."""
    data = request.get_json(silent=True) or {}

    record = {
        "form_id": data.get("form_id", str(uuid.uuid4())[:8].upper()),
        "form_type": data.get("form_type", "Unknown"),
        "department": data.get("department", "Unknown"),
        "original_image": data.get("original_image", ""),
        "processed_image": data.get("processed_image", ""),
        "extracted_fields": data.get("extracted_fields", {}),
        "final_corrected_fields": data.get("final_corrected_fields", {}),
        "confidence_scores": data.get("confidence_scores", {}),
        "timestamp": datetime.now().isoformat(),
        "verification_status": "Verified",
    }

    audit_records.append(record)
    return jsonify({"success": True, "form_id": record["form_id"], "message": "Form verified and submitted successfully."})


@app.route("/audit-records", methods=["GET"])
def get_audit_records():
    """Return all processed form records."""
    form_type_filter = request.args.get("form_type", "")
    records = audit_records

    if form_type_filter:
        records = [r for r in records if r["form_type"] == form_type_filter]

    # Return summary fields only
    summary = [{
        "form_id": r["form_id"],
        "form_type": r["form_type"],
        "department": r["department"],
        "timestamp": r["timestamp"],
        "verification_status": r["verification_status"],
    } for r in records]

    return jsonify({"records": summary, "total": len(summary)})


@app.route("/audit-record/<form_id>", methods=["GET"])
def get_audit_record(form_id):
    """Return full details for a single record."""
    for record in audit_records:
        if record["form_id"] == form_id:
            return jsonify(record)
    return jsonify({"error": "Record not found"}), 404


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "1.0.0", "service": "PaperTrail API"})


if __name__ == "__main__":
    print("PaperTrail API running on http://localhost:3001")
    app.run(port=3001, debug=False)
