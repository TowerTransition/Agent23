"""
Simplified sanitizer for fine-tuned model.
Since the model is already fine-tuned, we do minimal cleanup only.
"""

import re
from typing import Optional


def sanitize_post(text: str, domain: Optional[str] = None) -> str:
    """
    Minimal sanitization - just basic cleanup since model is fine-tuned.
    
    Args:
        text: Generated text from the model
        domain: Optional domain for context (not used in simple version)
    
    Returns:
        Cleaned text with basic artifacts removed
    """
    # Basic cleanup only
    text = text.strip()
    
    # Remove common instruction artifacts
    text = re.sub(r'(?i)\bEND\b', '', text)
    text = re.sub(r'(?m)^\s*\d+\.\s+.*$', '', text)  # Numbered instruction lines
    
    # Remove template phrases that shouldn't be in output
    text = re.sub(r'(?i)\b4-6 sentences\.?\s*one question\.?\b', '', text)
    text = re.sub(r'(?i)\bfollow these\b', '', text)
    text = re.sub(r'(?i)\bcontinue with\b', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
