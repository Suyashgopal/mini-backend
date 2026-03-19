"""
comparison_service.py — Minimal comparison service for text matching.

This is a simplified version that compares two texts and returns similarity metrics.
"""

import logging
from difflib import SequenceMatcher
from typing import Dict, List

logger = logging.getLogger(__name__)


class ComparisonService:
    """Service for comparing pharmaceutical label texts."""
    
    @staticmethod
    def compare_texts(control_text: str, production_text: str) -> Dict:
        """
        Compare control text with production text and return similarity metrics.
        
        Args:
            control_text: The verified control text
            production_text: The OCR extracted production text
            
        Returns:
            Dict containing match_percentage, deviations, and status
        """
        if not control_text or not production_text:
            return {
                "match_percentage": 0.0,
                "deviations": ["Empty text provided"],
                "status": "FAIL"
            }
        
        # Normalize texts for comparison
        control_normalized = control_text.strip().lower()
        production_normalized = production_text.strip().lower()
        
        # Calculate similarity using SequenceMatcher
        matcher = SequenceMatcher(None, control_normalized, production_normalized)
        similarity_ratio = matcher.ratio()
        match_percentage = similarity_ratio * 100
        
        # Find differences
        deviations = []
        opcodes = matcher.get_opcodes()
        
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'delete':
                deviations.append(f"Missing: '{control_text[i1:i2]}'")
            elif tag == 'insert':
                deviations.append(f"Extra: '{production_text[j1:j2]}'")
            elif tag == 'replace':
                deviations.append(f"Changed: '{control_text[i1:i2]}' → '{production_text[j1:j2]}'")
        
        # Determine status (pass if >= 95% similarity)
        status = "PASS" if match_percentage >= 95.0 else "FAIL"
        
        logger.info(
            "Text comparison: %.1f%% similarity, %d deviations, status=%s",
            match_percentage, len(deviations), status
        )
        
        return {
            "match_percentage": match_percentage,
            "deviations": deviations,
            "status": status
        }