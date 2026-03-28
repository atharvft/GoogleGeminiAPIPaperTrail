"""
Template Engine for handling auto-generation of blank templates
from filled forms, and rendering clean digital forms over templates.
"""

import os
import json
import cv2
import numpy as np
import traceback
from typing import Dict, Any, Tuple, Optional
from difflib import SequenceMatcher

from .config import config

# Path to template files
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(TEMPLATES_DIR, exist_ok=True)


def _fuzzy_match(word: str, target: str) -> bool:
    """Return True if word is a strong subtree/match inside the target value."""
    if not word or not target:
        return False
    w = word.lower().strip()
    t = target.lower().strip()
    
    # Direct substring
    if w in t:
        return True
    
    # Fuzzy match threshold for handwriting mistakes (e.g. Kolhapur vs Kolhpur)
    matcher = SequenceMatcher(None, w, t)
    # Check if a substantial part of the target matches the word
    # For small words (len < 4), require exact match.
    if len(w) < 4:
        return w in t.split()
    
    return matcher.ratio() > 0.85 or any(SequenceMatcher(None, w, part).ratio() > 0.85 for part in t.split())


class TemplateEngine:
    """Handles generating templates and digital forms."""
    
    def __init__(self):
        self._paddle_ocr = None
        
    def _init_paddle(self):
        """Initialize PaddleOCR lazily, only if installed."""
        if self._paddle_ocr is None:
            try:
                from paddleocr import PaddleOCR
                print("[TemplateEngine] Initializing PaddleOCR...")
                self._paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en')
            except ImportError:
                print("[TemplateEngine] ⚠ PaddleOCR not installed. Will fallback to Tesseract.")
                self._paddle_ocr = False

    def auto_create_template(
        self, 
        image_path: str, 
        extracted_data: Dict[str, Any], 
        form_type: str
    ) -> Tuple[str, str]:
        """
        Auto-erase handwritten text using extracted data values,
        generating a clean blank template and a coordinates map.
        
        Args:
            image_path: Original image.
            extracted_data: Dict of extracted fields (e.g., {"name": "John Doe", "date_of_birth": "12/05/2021"}).
            form_type: E.g., "birth_certificate"
            
        Returns:
            Tuple of (template_image_path, template_coords_json_path)
        """
        print(f"\n[TemplateEngine] 🪄 Auto-creating blank template for '{form_type}' from {os.path.basename(image_path)}")
        
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to read image at {image_path}")

        coords_map = {}
        
        # Values we want to erase
        target_values = []
        for key, value in extracted_data.items():
            if isinstance(value, str) and value.strip():
                target_values.append((key, value))

        boxes = []
        texts = []

        # 1. Try PaddleOCR first (better bounding boxes for handwriting)
        self._init_paddle()
        if self._paddle_ocr:
            try:
                result = self._paddle_ocr.ocr(image_path, cls=True)
                for idx in range(len(result)):
                    res = result[idx]
                    if not res: continue
                    for line in res:
                        # PaddleOCR format: [[(x1, y1), (x2, y2), (x3, y3), (x4, y4)], ('text', confidence)]
                        box = line[0]
                        text = line[1][0]
                        # Convert 4 points to bounding rect
                        x_coords = [p[0] for p in box]
                        y_coords = [p[1] for p in box]
                        x, y = int(min(x_coords)), int(min(y_coords))
                        w, h = int(max(x_coords) - x), int(max(y_coords) - y)
                        boxes.append({"x": x, "y": y, "w": w, "h": h})
                        texts.append(text)
                print(f"[TemplateEngine] PaddleOCR found {len(boxes)} text lines.")
            except Exception as e:
                print(f"[TemplateEngine] ⚠ PaddleOCR failed: {e}. Falling back to Tesseract.")
                self._paddle_ocr = False
                
        # 2. Fallback to Tesseract if PaddleOCR failed or isn't installed
        if not self._paddle_ocr:
            import pytesseract
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            n_boxes = len(data['level'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                if text:
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    boxes.append({"x": x, "y": y, "w": w, "h": h})
                    texts.append(text)
            print(f"[TemplateEngine] Tesseract found {len(boxes)} text blocks.")

        # 3. Process boxes: Erase if matches target values
        erased_count = 0
        for i, box in enumerate(boxes):
            text = texts[i]
            
            # Check if this text belongs to any extracted field value
            matched_key = None
            for key, val in target_values:
                # If the OCR text is part of a value we extracted (or vice-versa)
                if _fuzzy_match(text, val) or _fuzzy_match(val, text):
                    matched_key = key
                    break
            
            if matched_key:
                # We found handwritten text!
                # Pad the box slightly to ensure all strokes are erased
                pad_x, pad_y = 10, 5
                x1 = max(0, box['x'] - pad_x)
                y1 = max(0, box['y'] - pad_y)
                x2 = min(img.shape[1], box['x'] + box['w'] + pad_x)
                y2 = min(img.shape[0], box['y'] + box['h'] + pad_y)
                
                # Draw white rectangle to erase
                cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), -1)
                
                # Save coordinate (use bottom-left of the box for text baseline)
                if matched_key not in coords_map:
                    # Save the first encountered bounding box as the starting coordinate
                    coords_map[matched_key] = {"x": box['x'], "y": box['y'] + box['h']}
                erased_count += 1
                
        print(f"[TemplateEngine] Erased {erased_count} matching handwritten blocks.")
        
        # 4. Save template images
        template_filename = f"{form_type}_template.jpg"
        template_path = os.path.join(TEMPLATES_DIR, template_filename)
        cv2.imwrite(template_path, img)
        print(f"[TemplateEngine] ✓ Master template saved at {template_path}")
        
        # 5. Save coordinates mapping
        coords_filename = f"{form_type}_coords.json"
        coords_path = os.path.join(TEMPLATES_DIR, coords_filename)
        with open(coords_path, "w") as f:
            json.dump(coords_map, f, indent=4)
        print(f"[TemplateEngine] ✓ Template coordinates mapped: {len(coords_map)} fields.")
        
        return template_path, coords_path


    def generate_digital_form(self, form_type: str, extracted_data: Dict[str, Any]) -> Optional[str]:
        """
        Overlay extracted data onto the saved master template.
        
        Returns path to generated output image, or None if template doesn't exist.
        """
        template_path = os.path.join(TEMPLATES_DIR, f"{form_type}_template.jpg")
        coords_path = os.path.join(TEMPLATES_DIR, f"{form_type}_coords.json")
        
        if not os.path.exists(template_path):
            print(f"[TemplateEngine] ❌ No master template found for '{form_type}'")
            return None
            
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            print("[TemplateEngine] Pillow not installed.")
            return None
            
        # Open template
        img = Image.open(template_path).convert('RGB')
        draw = ImageDraw.Draw(img)
        
        # Try loading a readable default font
        font = None
        try:
            # Arial or similar default legible font
            font = ImageFont.truetype("Arial.ttf", size=32)
        except IOError:
            try:
                # Mac OS default
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size=32)
            except IOError:
                # Fallback purely to basic pillow font
                font = ImageFont.load_default()
        
        # Load coordinates (fallback to empty if not exists)
        coords = {}
        if os.path.exists(coords_path):
            with open(coords_path, "r") as f:
                coords = json.load(f)
                
        # Draw text at coordinates
        for key, value in extracted_data.items():
            if not value or not str(value).strip():
                continue
                
            pos = coords.get(key)
            if pos:
                x, y = pos['x'], pos['y']
            else:
                # If we don't know where it goes, we skip it for now,
                # or we could append it at the bottom.
                continue
                
            # Draw blue computer text over the blank space
            # Shift y slightly up because PIL draws from top-left, while our baseline was bottom-left
            draw.text((x, y - 30), str(value), fill=(0, 51, 153), font=font)
            
        # Save output
        output_filename = f"generated_{form_type}_{os.urandom(4).hex()}.jpg"
        output_path = os.path.join(config.UPLOAD_FOLDER, output_filename)
        img.save(output_path)
        
        print(f"[TemplateEngine] ✓ Digital form generated: {output_path}")
        return output_filename

template_engine = TemplateEngine()
