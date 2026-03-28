# PaperTrail - Field Reference Guide

This document maps the actual form fields to the database structure.

## Birth Certificate (West Bengal - Government of India)

**Department**: Civil Records Department  
**Collection**: `civil_records_department`  
**Form Type**: `birth_certificate`

### Form Fields

| Field Number | Form Label | Database Field | Type | Example |
|-------------|------------|----------------|------|---------|
| - | Name (নাম) | `name` | String | Rafikul Islam |
| - | Sex (লিঙ্গ) | `sex` | String | Male |
| - | Date of Birth (জন্ম তারিখ) | `date_of_birth` | Date | 22-10-1993 |
| - | Place of Birth (জন্ম স্থান) | `place_of_birth` | String | Paikpara |
| - | Name of Mother (মাতার নাম) | `name_of_mother` | String | Sathi Begam |
| - | Name of Father (পিতার নাম) | `name_of_father` | String | Samsul Haque |
| - | Address of Parents at Birth | `address_of_parents_at_birth` | String | Vill - Chakbarbaria po |
| - | Permanent Address of Parents | `permanent_address_of_parents` | String | Noapara, ps-Duttapukur, Dist-North |
| - | Registration No. (নিবন্ধন নং) | `registration_number` | String | 928 |
| - | Date of Registration | `date_of_registration` | Date | 17-08-2002 |
| - | Remarks (if any) | `remarks` | String | Name Correction |
| - | Date of Issue (জারির তারিখ) | `date_of_issue` | Date | 18/07/22 |

### Database Document Structure

```javascript
{
  "_id": ObjectId,
  "department": "civil_records_department",
  "form_type": "birth_certificate",
  "image_path": "uploads/birth_cert_001.jpg",
  
  "extracted_data": {
    "name": "Rafikul Islam",
    "sex": "Male",
    "date_of_birth": "22-10-1993",
    "place_of_birth": "Paikpara",
    "name_of_mother": "Sathi Begam",
    "name_of_father": "Samsul Haque",
    "address_of_parents_at_birth": "Vill - Chakbarbaria po",
    "permanent_address_of_parents": "Noapara, ps-Duttapukur, Dist-North",
    "registration_number": "928",
    "date_of_registration": "17-08-2002",
    "remarks": "Name Correction",
    "date_of_issue": "18/07/22"
  },
  
  "confidence_scores": {
    "name": 0.85,
    "sex": 0.92,
    "date_of_birth": 0.78,
    // ... confidence for each field
  },
  
  "corrected_data": {},
  "status": "pending_verification",
  "created_at": ISODate("2024-03-28T12:00:00Z"),
  "updated_at": ISODate("2024-03-28T12:00:00Z")
}
```

---

## Residence Certificate (Maharashtra State)

**Department**: Citizen Services Department  
**Collection**: `citizen_services_department`  
**Form Type**: `residence_certificate`

### Form Fields

| Field Number | Form Label | Database Field | Type | Example |
|-------------|------------|----------------|------|---------|
| 1 | Full Name: | `full_name` | String | Rajesh Kumar Sharma |
| 2 | Father / Husband Name: | `father_husband_name` | String | Mohan Sharma |
| 3 | Residential Address: | `residential_address` | String | 123 MG Road, Pune 411001 |
| 4 | Mobile Number: | `mobile_number` | String | 9876543210 |
| 5 | Purpose of Certificate: | `purpose_of_certificate` | String | Educational |
| 6 | Duration of Residence (Years): | `duration_of_residence_years` | String | 10 years |
| - | Date: | `date` | Date | 28-03-2024 |
| - | Place: | `place` | String | Pune |

### Database Document Structure

```javascript
{
  "_id": ObjectId,
  "department": "citizen_services_department",
  "form_type": "residence_certificate",
  "image_path": "uploads/residence_cert_001.jpg",
  
  "extracted_data": {
    "full_name": "Rajesh Kumar Sharma",
    "father_husband_name": "Mohan Sharma",
    "residential_address": "123 MG Road, Pune 411001",
    "mobile_number": "9876543210",
    "purpose_of_certificate": "Educational",
    "duration_of_residence_years": "10 years",
    "date": "28-03-2024",
    "place": "Pune"
  },
  
  "confidence_scores": {
    "full_name": 0.88,
    "father_husband_name": 0.82,
    "residential_address": 0.75,
    // ... confidence for each field
  },
  
  "corrected_data": {},
  "status": "pending_verification",
  "created_at": ISODate("2024-03-28T12:00:00Z"),
  "updated_at": ISODate("2024-03-28T12:00:00Z")
}
```

---

## Field Extraction Confidence

The system assigns a confidence score (0.0 to 1.0) to each extracted field based on OCR quality.

- **High Confidence** (≥ 0.75): Field is likely correct
- **Low Confidence** (< 0.75): Field flagged for human verification

### Verification Flags

Fields with low confidence are automatically flagged:

```json
"verification_flags": {
  "name": false,              // No verification needed
  "registration_number": true, // Needs verification
  "date_of_birth": false
}
```

---

## Template Detection Keywords

### Birth Certificate Detection
- "birth certificate"
- "date of birth"
- "name of mother" / "মাতার নাম"
- "name of father" / "পিতার নাম"
- "department of health"
- "west bengal"
- Bengali text (জন্ম, মাতার, পিতার)

### Residence Certificate Detection
- "residence certificate"
- "government of maharashtra"
- "residential address"
- "father / husband name"
- "duration of residence"
- "applicant details"

---

## OCR Text Patterns

### Bengali Text Handling

The birth certificate includes Bengali text. The OCR must handle:
- নাম (Name)
- লিঙ্গ (Sex/Gender)
- জন্ম তারিখ (Date of Birth)
- মাতার নাম (Mother's Name)
- পিতার নাম (Father's Name)
- নিবন্ধন নং (Registration Number)

### Handwriting Challenges

Common OCR challenges with handwritten forms:
1. **Cursive writing**: May merge characters
2. **Date formats**: DD-MM-YYYY, DD/MM/YYYY variations
3. **Numbers vs Letters**: 0/O, 1/I, 5/S confusion
4. **Address fields**: Multi-line, variable length
5. **Names**: Capitalization inconsistency

### Extraction Strategies

1. **Number fields** (mobile, registration): Extract pure digits
2. **Date fields**: Normalize to DD-MM-YYYY format
3. **Name fields**: Capitalize properly
4. **Address fields**: Preserve line breaks, clean extra spaces
5. **Multi-line fields**: Use flexible regex patterns

---

## API Response Format

### Upload Response Example

```json
{
  "success": true,
  "form_type": "birth_certificate",
  "department": "civil_records_department",
  "form_id": "507f1f77bcf86cd799439011",
  
  "extracted_data": {
    "name": "Rafikul Islam",
    "sex": "Male",
    // ... all extracted fields
  },
  
  "confidence_scores": {
    "name": 0.85,
    "sex": 0.92,
    // ... confidence for each field
  },
  
  "verification_flags": {
    "name": false,
    "registration_number": true,
    // ... flags for each field
  },
  
  "classification_confidence": 0.95
}
```

---

## Usage Notes

1. **Clerk Upload**: Clerks upload photos of handwritten forms
2. **OCR Processing**: System extracts text with Sarvam OCR
3. **Auto-Classification**: Template detected automatically
4. **Field Extraction**: Structured data extracted via regex patterns
5. **Confidence Scoring**: Each field scored for accuracy
6. **Human Verification**: Low-confidence fields reviewed by clerk
7. **Data Storage**: Saved to department-specific MongoDB collection

---

## Tuning Field Extraction

If extraction accuracy is low, adjust in `field_extractor.py`:

1. **Regex patterns**: Modify patterns for your forms
2. **Confidence threshold**: Adjust in `config.py` (default: 0.75)
3. **Keywords**: Add state/department-specific terms
4. **Bengali support**: Ensure UTF-8 encoding for Bengali text

---

Last Updated: March 28, 2024
