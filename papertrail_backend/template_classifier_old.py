"""
Template classification module.
Detects which government form template the document belongs to.
"""

from typing import Dict, Optional, Tuple
from .config import config


class TemplateClassifier:
    """Classifies government forms based on OCR text content."""
    
    # Keywords for each template type
    BIRTH_CERTIFICATE_KEYWORDS = [
        "birth certificate",
        "date of birth",
        "place of birth",
        "name of mother",
        "name of father",
        "registration no",
        "department of health",
        "west bengal",
        "জন্ম",  # Birth in Bengali
        "মাতার নাম",  # Mother's name in Bengali
        "পিতার নাম"  # Father's name in Bengali
    ]
    
    RESIDENCE_CERTIFICATE_KEYWORDS = [
        "residence certificate",
        "residential address",
        "duration of residence",
        "purpose of certificate",
        "maharashtra",
        "government of maharashtra",
        "father / husband name",
        "applicant details",
        "mobile number"
    ]
    
    def __init__(self):
        self.templates = {
            "birth_certificate": {
                "keywords": self.BIRTH_CERTIFICATE_KEYWORDS,
                "department": config.CIVIL_RECORDS_COLLECTION,
                "department_name": "Civil Records Department"
            },
            "residence_certificate": {
                "keywords": self.RESIDENCE_CERTIFICATE_KEYWORDS,
                "department": config.CITIZEN_SERVICES_COLLECTION,
                "department_name": "Citizen Services Department"
            }
        }
    
    def classify(self, ocr_text: str) -> Tuple[str, str, float]:
        """
        Classify document template based on OCR text.
        
        Args:
            ocr_text: Extracted text from OCR
            
        Returns:
            Tuple: (form_type, department, confidence)
        """
        ocr_text_lower = ocr_text.lower()
        
        scores = {}
        
        # Calculate match scores for each template
        for template_name, template_data in self.templates.items():
            score = self._calculate_keyword_match_score(
                ocr_text_lower,
                template_data["keywords"]
            )
            scores[template_name] = score
        
        # Get template with highest score
        if not scores:
            return "unknown", "unknown", 0.0
        
        best_template = max(scores, key=scores.get)
        confidence = scores[best_template]
        
        # Require minimum confidence threshold
        if confidence < 0.3:  # At least 30% keyword match
            return "unknown", "unknown", confidence
        
        department = self.templates[best_template]["department"]
        
        return best_template, department, confidence
    
    def _calculate_keyword_match_score(self, text: str, keywords: list) -> float:
        """
        Calculate keyword match score.
        
        Args:
            text: Text to search in
            keywords: List of keywords to search for
            
        Returns:
            float: Match score (0.0 to 1.0)
        """
        matches = 0
        
        for keyword in keywords:
            if keyword.lower() in text:
                matches += 1
        
        # Normalize score
        score = matches / len(keywords) if keywords else 0.0
        
        return score
    
    def get_template_info(self, form_type: str) -> Optional[Dict]:
        """
        Get template configuration information.
        
        Args:
            form_type: Form type identifier
            
        Returns:
            Optional[Dict]: Template configuration or None
        """
        return self.templates.get(form_type)


def classify_template(ocr_text: str) -> Dict[str, any]:
    """
    Convenience function to classify document template.
    
    Args:
        ocr_text: Extracted text from OCR
        
    Returns:
        Dict: Classification result with form_type, department, and confidence
    """
    classifier = TemplateClassifier()
    form_type, department, confidence = classifier.classify(ocr_text)
    
    return {
        "form_type": form_type,
        "department": department,
        "classification_confidence": confidence
    }


def detect_form_type_by_keywords(text: str) -> str:
    """
    Simple keyword-based form type detection.
    
    Args:
        text: OCR extracted text
        
    Returns:
        str: Detected form type
    """
    text_lower = text.lower()
    
    # Check for birth certificate
    if any(keyword in text_lower for keyword in ["birth certificate", "certificate of birth"]):
        return "birth_certificate"
    
    # Check for residence certificate
    if any(keyword in text_lower for keyword in ["residence certificate", "certificate of residence"]):
        return "residence_certificate"
    
    return "unknown"


def get_department_by_form_type(form_type: str) -> str:
    """
    Get department collection name by form type.
    
    Args:
        form_type: Form type identifier
        
    Returns:
        str: Department collection name
    """
    department_mapping = {
        "birth_certificate": config.CIVIL_RECORDS_COLLECTION,
        "residence_certificate": config.CITIZEN_SERVICES_COLLECTION
    }
    
    return department_mapping.get(form_type, "unknown")
