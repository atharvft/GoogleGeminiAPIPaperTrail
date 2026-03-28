"""
Image preprocessing module using OpenCV.
Cleans and enhances images for better OCR accuracy.
"""

import cv2
import numpy as np
from typing import Tuple, Optional
import os


def load_image(image_path: str) -> Optional[np.ndarray]:
    """
    Load image from file path.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Optional[np.ndarray]: Loaded image or None if failed
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    
    return image


def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Convert image to grayscale.
    
    Args:
        image: Input image
        
    Returns:
        np.ndarray: Grayscale image
    """
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def remove_noise(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """
    Remove noise using Gaussian blur.
    
    Args:
        image: Input grayscale image
        kernel_size: Size of Gaussian kernel (must be odd)
        
    Returns:
        np.ndarray: Denoised image
    """
    return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)


def adaptive_threshold(image: np.ndarray) -> np.ndarray:
    """
    Apply adaptive thresholding for better text extraction.
    Works well with varying lighting conditions.
    
    Args:
        image: Input grayscale image
        
    Returns:
        np.ndarray: Binary thresholded image
    """
    return cv2.adaptiveThreshold(
        image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )


def deskew_image(image: np.ndarray) -> np.ndarray:
    """
    Correct image skew/rotation.
    Uses Hough transform to detect text lines and calculate skew angle.
    
    Args:
        image: Input binary image
        
    Returns:
        np.ndarray: Deskewed image
    """
    # Detect edges
    edges = cv2.Canny(image, 50, 150, apertureSize=3)
    
    # Detect lines using Hough transform
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    
    if lines is None:
        return image
    
    # Calculate average angle
    angles = []
    for rho, theta in lines[:, 0]:
        angle = np.degrees(theta) - 90
        if -45 < angle < 45:
            angles.append(angle)
    
    if not angles:
        return image
    
    median_angle = np.median(angles)
    
    # Rotate image to correct skew
    if abs(median_angle) > 0.5:  # Only deskew if angle is significant
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(
            image,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return rotated
    
    return image


def morphological_operations(image: np.ndarray) -> np.ndarray:
    """
    Apply morphological operations to improve text clarity.
    
    Args:
        image: Input binary image
        
    Returns:
        np.ndarray: Processed image
    """
    # Define kernel for morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    
    # Remove small noise - opening operation
    opening = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Close gaps in text - closing operation
    closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    return closing


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """
    Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Args:
        image: Input grayscale image
        
    Returns:
        np.ndarray: Contrast-enhanced image
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(image)


def preprocess_image_pipeline(image_path: str) -> Tuple[np.ndarray, str]:
    """
    Complete preprocessing pipeline for OCR optimization.
    Uses a gentle approach suitable for handwritten forms.
    
    Steps:
    1. Load image
    2. Resize if too large
    3. Convert to grayscale
    4. Enhance contrast with CLAHE
    5. Light denoising
    
    Args:
        image_path: Path to input image
        
    Returns:
        Tuple[np.ndarray, str]: Processed image and path to saved processed image
    """
    # Load image
    image = load_image(image_path)
    
    # Resize if too large (for better performance)
    image = resize_image_if_needed(image, max_dimension=3000)
    
    # Convert to grayscale
    gray = convert_to_grayscale(image)
    
    # Enhance contrast (helps with faded text)
    enhanced = enhance_contrast(gray)
    
    # Light denoising - use bilateral filter to preserve edges
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
    
    # For handwritten text, we skip heavy thresholding
    # as it can break thin strokes
    
    # Save processed image
    processed_path = save_processed_image(image_path, denoised)
    
    return denoised, processed_path


def save_processed_image(original_path: str, processed_image: np.ndarray) -> str:
    """
    Save processed image to disk.
    
    Args:
        original_path: Path to original image
        processed_image: Processed image array
        
    Returns:
        str: Path to saved processed image
    """
    # Generate processed image path
    dir_name = os.path.dirname(original_path)
    file_name = os.path.basename(original_path)
    name, ext = os.path.splitext(file_name)
    processed_path = os.path.join(dir_name, f"{name}_processed{ext}")
    
    # Save image
    cv2.imwrite(processed_path, processed_image)
    
    return processed_path


def resize_image_if_needed(image: np.ndarray, max_dimension: int = 2000) -> np.ndarray:
    """
    Resize image if dimensions exceed maximum.
    Maintains aspect ratio.
    
    Args:
        image: Input image
        max_dimension: Maximum width or height
        
    Returns:
        np.ndarray: Resized image
    """
    height, width = image.shape[:2]
    
    if height > max_dimension or width > max_dimension:
        if height > width:
            new_height = max_dimension
            new_width = int(width * (max_dimension / height))
        else:
            new_width = max_dimension
            new_height = int(height * (max_dimension / width))
        
        resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        return resized
    
    return image
