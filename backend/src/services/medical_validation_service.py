"""
medical_validation_service.py — Minimal medical validation service.

This is a simplified version that performs basic pharmaceutical label validation.
"""

import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)


class MedicalValidationService:
    """Service for validating pharmaceutical label authenticity."""
    
    def validate_text(self, extracted_text: str) -> Dict:
        """
        Validate pharmaceutical label text for structural authenticity.
        
        Args:
            extracted_text: The OCR extracted text from the label
            
        Returns:
            Dict containing validation results and authenticity score
        """
        if not extracted_text or not extracted_text.strip():
            return {
                "is_structurally_authentic": False,
                "authenticity_score": 0.0,
                "validation_details": {
                    "has_drug_name": False,
                    "has_strength": False,
                    "has_batch_number": False,
                    "has_expiry_date": False,
                    "has_manufacturer": False,
                },
                "warnings": ["Empty or missing text"]
            }
        
        text = extracted_text.lower()
        validation_details = {}
        warnings = []
        score_components = []
        
        # Check for drug name (look for common pharmaceutical patterns)
        has_drug_name = bool(re.search(r'\b\w+\s*(tablet|capsule|syrup|injection|mg|ml)\b', text))
        validation_details["has_drug_name"] = has_drug_name
        score_components.append(20 if has_drug_name else 0)
        
        # Check for strength (dosage information)
        has_strength = bool(re.search(r'\b\d+\s*(mg|ml|g|%|iu|mcg)\b', text))
        validation_details["has_strength"] = has_strength
        score_components.append(20 if has_strength else 0)
        
        # Check for batch number
        has_batch_number = bool(re.search(r'\b(batch|lot|b\.?no|l\.?no)[:\s]*[a-z0-9]+\b', text))
        validation_details["has_batch_number"] = has_batch_number
        score_components.append(20 if has_batch_number else 0)
        
        # Check for expiry date
        has_expiry_date = bool(re.search(r'\b(exp|expiry|use\s+by)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text))
        validation_details["has_expiry_date"] = has_expiry_date
        score_components.append(20 if has_expiry_date else 0)
        
        # Check for manufacturer
        has_manufacturer = bool(re.search(r'\b(mfg|manufactured|mfd)[:\s]*by\b', text))
        validation_details["has_manufacturer"] = has_manufacturer
        score_components.append(20 if has_manufacturer else 0)
        
        # Calculate authenticity score (0-100)
        authenticity_score = sum(score_components)
        
        # Determine if structurally authentic (need at least 60% score)
        is_structurally_authentic = authenticity_score >= 60.0
        
        # Add warnings for missing critical fields
        if not has_drug_name:
            warnings.append("No drug name detected")
        if not has_strength:
            warnings.append("No dosage strength detected")
        if not has_expiry_date:
            warnings.append("No expiry date detected")
        
        logger.info(
            "Medical validation: %.1f%% authenticity, authentic=%s, %d warnings",
            authenticity_score, is_structurally_authentic, len(warnings)
        )
        
        return {
            "is_structurally_authentic": is_structurally_authentic,
            "authenticity_score": authenticity_score,
            "validation_details": validation_details,
            "warnings": warnings
        }