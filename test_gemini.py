#!/usr/bin/env python3
"""Test Gemini extraction directly on the uploaded forms."""

import sys
import os
sys.path.append('/Users/atharvdalvi/Desktop/PaperTrail')

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv('/Users/atharvdalvi/Desktop/PaperTrail/papertrail_backend/.env')

from papertrail_backend.gemini_extractor import extract_with_gemini
import json

def test_form(image_path, form_type, form_name):
    """Test Gemini extraction on a specific form."""
    print(f"\n=== Testing {form_name} ===")
    print(f"Image: {image_path}")
    print(f"Type: {form_type}")
    
    try:
        result = extract_with_gemini(image_path, form_type)
        if result:
            print("✅ Gemini extraction successful!")
            print("\n📋 Extracted Key-Value Pairs:")
            print("=" * 50)
            for field, value in result.items():
                print(f"{field:25} : {value}")
            print("=" * 50)
            return result
        else:
            print("❌ Gemini extraction failed or returned empty result")
            return None
    except Exception as e:
        print(f"❌ Error during Gemini extraction: {str(e)}")
        return None

if __name__ == "__main__":
    # Test both forms
    birth_result = test_form(
        "/Users/atharvdalvi/Desktop/PaperTrail/uploads/birth_certificate.png", 
        "birth_certificate",
        "West Bengal Birth Certificate"
    )
    
    residence_result = test_form(
        "/Users/atharvdalvi/Desktop/PaperTrail/uploads/residence_certificate.png", 
        "residence_certificate", 
        "Maharashtra Residence Certificate Application"
    )
    
    print(f"\n\n🎯 Summary:")
    print(f"Birth Certificate: {'✅ Success' if birth_result else '❌ Failed'}")
    print(f"Residence Certificate: {'✅ Success' if residence_result else '❌ Failed'}")