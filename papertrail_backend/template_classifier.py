"""
Template classification module.
Detects form type based on OCR text content using robust keyword matching.
"""

import re
from typing import Dict, Any
from .config import config


# Template detection keywords - ordered by priority
BIRTH_CERTIFICATE_KEYWORDS = [
    "birth certificate",
    "birth_certificate", 
    "জন্ম সংসাপত্র",  # Bengali for birth certificate
    "government of west bengal",
    "west bengal",
    "registration of births and deaths",
    "department of health",
    "date of birth",
    "name of mother",
    "name of father",
    "place of birth",
    "form: 5",
    "form 5",
    "form:5",
    "registration no",
    "date of registration",
    "date of issue",
]

RESIDENCE_CERTIFICATE_KEYWORDS = [
    "residence certificate",
    "application for residence",
    "government of maharashtra",
    "maharashtra state",
    "maharashtra",
    "residential address",
    "duration of residence",
    "purpose of certificate",
    "applicant details",
    "father / husband name",
    "father/husband name",
    "mobile number",
    "full name",
]


def classify_template(ocr_text: str) -> Dict[str, Any]:
    """
    Classify the form template based on OCR text content.
    Uses keyword matching with scoring to determine form type.
    
    Args:
        ocr_text: Full text extracted from form via OCR
        
    Returns:
        Dict with form_type, department, and classification_confidence
    """
    print(f"\n{'='*70}")
    print(f"📋 TEMPLATE CLASSIFICATION")
    print(f"{'='*70}")
    
    if not ocr_text:
        print("❌ No OCR text provided")
        return {
            "form_type": "unknown",
            "department": "unknown",
            "classification_confidence": 0.0
        }
    
    # Normalize text for matching — strip markdown formatting chars
    text_lower = ocr_text.lower()
    text_normalized = re.sub(r'[\*\_\#\|\[\]`]', ' ', text_lower)  # strip markdown
    text_normalized = re.sub(r'\s+', ' ', text_normalized).strip()
    
    print(f"📄 Text length: {len(ocr_text)} characters")
    print(f"🔍 Searching for keywords...")
    
    # Score for each template type
    birth_score = 0
    residence_score = 0
    birth_matches = []
    residence_matches = []
    
    # Check birth certificate keywords
    for keyword in BIRTH_CERTIFICATE_KEYWORDS:
        if keyword.lower() in text_normalized:
            # Higher weight for exact title matches
            if keyword in ["birth certificate", "জন্ম সংসাপত্র"]:
                weight = 10
            elif keyword in ["government of west bengal", "west bengal"]:
                weight = 5
            else:
                weight = 2
            birth_score += weight
            birth_matches.append(f"{keyword} (+{weight})")
    
    # Check residence certificate keywords
    for keyword in RESIDENCE_CERTIFICATE_KEYWORDS:
        if keyword.lower() in text_normalized:
            # Higher weight for exact title matches
            if keyword in ["residence certificate", "application for residence"]:
                weight = 10
            elif keyword in ["government of maharashtra", "maharashtra state", "maharashtra"]:
                weight = 5
            else:
                weight = 2
            residence_score += weight
            residence_matches.append(f"{keyword} (+{weight})")
    
    print(f"\n🎯 Birth Certificate Matches ({birth_score} points):")
    for match in birth_matches[:5]:  # Show top 5
        print(f"   ✓ {match}")
    if len(birth_matches) > 5:
        print(f"   ... and {len(birth_matches) - 5} more")
    
    print(f"\n🎯 Residence Certificate Matches ({residence_score} points):")
    for match in residence_matches[:5]:
        print(f"   ✓ {match}")
    if len(residence_matches) > 5:
        print(f"   ... and {len(residence_matches) - 5} more")
    
    # Determine winner
    total_score = birth_score + residence_score
    
    if total_score == 0:
        print("\n❌ No template keywords found - classification failed")
        return {
            "form_type": "unknown",
            "department": "unknown",
            "classification_confidence": 0.0
        }
    
    if birth_score > residence_score:
        confidence = birth_score / (birth_score + residence_score + 1)
        print(f"\n✅ CLASSIFIED AS: Birth Certificate")
        print(f"   Department: {config.CIVIL_RECORDS_COLLECTION}")
        print(f"   Confidence: {confidence:.1%}")
        return {
            "form_type": "birth_certificate",
            "department": config.CIVIL_RECORDS_COLLECTION,
            "classification_confidence": min(confidence, 1.0)
        }
    elif residence_score > birth_score:
        confidence = residence_score / (birth_score + residence_score + 1)
        print(f"\n✅ CLASSIFIED AS: Residence Certificate")
        print(f"   Department: {config.CITIZEN_SERVICES_COLLECTION}")
        print(f"   Confidence: {confidence:.1%}")
        return {
            "form_type": "residence_certificate",
            "department": config.CITIZEN_SERVICES_COLLECTION,
            "classification_confidence": min(confidence, 1.0)
        }
    else:
        # Tie - use additional heuristics
        print(f"\n⚖️  Score tie - using heuristics...")
        if "sex:" in text_normalized or "date of birth:" in text_normalized:
            print(f"   Found 'sex:' or 'date of birth:' → Birth Certificate")
            return {
                "form_type": "birth_certificate",
                "department": config.CIVIL_RECORDS_COLLECTION,
                "classification_confidence": 0.5
            }
        elif "1. full name" in text_normalized or "applicant details" in text_normalized:
            print(f"   Found '1. full name' or 'applicant details' → Residence Certificate")
            return {
                "form_type": "residence_certificate",
                "department": config.CITIZEN_SERVICES_COLLECTION,
                "classification_confidence": 0.5
            }
        
        print(f"❌ Could not break tie - classification failed")
        return {
            "form_type": "unknown",
            "department": "unknown",
            "classification_confidence": 0.0
        }


def get_department_for_form_type(form_type: str) -> str:
    """
    Get the department name for a given form type.
    
    Args:
        form_type: Type of form
        
    Returns:
        str: Department name
    """
    mapping = {
        "birth_certificate": config.CIVIL_RECORDS_COLLECTION,
        "residence_certificate": config.CITIZEN_SERVICES_COLLECTION
    }
    return mapping.get(form_type, "unknown")
