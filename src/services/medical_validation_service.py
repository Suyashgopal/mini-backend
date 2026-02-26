"""
Medical Validation Service

Validates extracted medical text for structural authenticity
using deterministic rules and regex patterns.
"""

import re
from typing import Dict, Any


class MedicalValidationService:
    """
    Service for validating medical text structure using deterministic rules.
    Validates dosage format, expiry date, batch numbers, manufacturer presence,
    and drug name patterns without AI calls or image processing.
    """

    def __init__(self):
        """Initialize validation patterns."""
        # Dosage validation patterns
        self.dosage_patterns = [
            r"\b\d+(?:\.\d+)?\s?(mg|ml|g|mcg)\b",  # 500 mg, 5ml, 0.5 g
            r"\b\d+\s?(?:tablets?|capsules?)\b"      # 10 tablets, 2 capsules
        ]
        
        # Expiry date validation patterns
        self.expiry_patterns = [
            r"\b(0[1-9]|1[0-2])/\d{4}\b",           # MM/YYYY
            r"\b\d{2}/\d{2}/\d{4}\b",               # DD/MM/YYYY
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4}\b"  # Month YYYY
        ]
        
        # Batch/Lot number validation patterns
        self.batch_label_patterns = [
            r"\b(?:Batch|LOT|Lot No\.?)\b"            # Batch, LOT, Lot No
        ]
        
        self.batch_number_patterns = [
            r"\b[A-Z0-9]{6,12}\b"                     # Alphanumeric 6-12 chars
        ]
        
        # Manufacturer validation patterns
        self.manufacturer_patterns = [
            r"\b(?:Manufactured by|Marketed by|Distributed by)\b"
        ]
        
        # Drug name heuristic patterns
        self.drug_name_patterns = [
            r"\b[A-Z][a-zA-Z]+\s\d+(?:\.\d+)?\s?(?:mg|ml|g|mcg)\b"  # Paracetamol 500 mg
        ]

    def validate_text(self, extracted_text: str) -> Dict[str, Any]:
        """
        Validate extracted medical text for structural authenticity.
        
        Args:
            extracted_text: Raw text extracted from OCR
            
        Returns:
            Dictionary containing validation results and authenticity score
        """
        if not extracted_text or not isinstance(extracted_text, str):
            return self._create_response(
                dosage_format_valid=False,
                expiry_format_valid=False,
                batch_number_valid=False,
                manufacturer_present=False,
                drug_name_format_valid=False,
                authenticity_score=0,
                is_structurally_authentic=False
            )
        
        # Perform individual validations
        dosage_valid = self._validate_dosage_format(extracted_text)
        expiry_valid = self._validate_expiry_format(extracted_text)
        batch_valid = self._validate_batch_number(extracted_text)
        manufacturer_present = self._validate_manufacturer(extracted_text)
        drug_name_valid = self._validate_drug_name(extracted_text)
        
        # Calculate authenticity score (20 points per validation)
        score = 0
        if dosage_valid:
            score += 20
        if expiry_valid:
            score += 20
        if batch_valid:
            score += 20
        if manufacturer_present:
            score += 20
        if drug_name_valid:
            score += 20
        
        is_authentic = score >= 70
        
        return self._create_response(
            dosage_format_valid=dosage_valid,
            expiry_format_valid=expiry_valid,
            batch_number_valid=batch_valid,
            manufacturer_present=manufacturer_present,
            drug_name_format_valid=drug_name_valid,
            authenticity_score=score,
            is_structurally_authentic=is_authentic
        )

    def _validate_dosage_format(self, text: str) -> bool:
        """Validate dosage format using regex patterns."""
        for pattern in self.dosage_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _validate_expiry_format(self, text: str) -> bool:
        """Validate expiry date format using regex patterns."""
        for pattern in self.expiry_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _validate_batch_number(self, text: str) -> bool:
        """Validate batch/lot number using label and number patterns."""
        has_label = any(re.search(pattern, text, re.IGNORECASE) 
                      for pattern in self.batch_label_patterns)
        has_number = any(re.search(pattern, text) 
                        for pattern in self.batch_number_patterns)
        return has_label and has_number

    def _validate_manufacturer(self, text: str) -> bool:
        """Validate manufacturer presence using keyword patterns."""
        for pattern in self.manufacturer_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _validate_drug_name(self, text: str) -> bool:
        """Validate drug name format using heuristic patterns."""
        for pattern in self.drug_name_patterns:
            if re.search(pattern, text):
                return True
        return False

    def _create_response(self, 
                       dosage_format_valid: bool,
                       expiry_format_valid: bool,
                       batch_number_valid: bool,
                       manufacturer_present: bool,
                       drug_name_format_valid: bool,
                       authenticity_score: int,
                       is_structurally_authentic: bool) -> Dict[str, Any]:
        """Create standardized response dictionary."""
        return {
            "dosage_format_valid": dosage_format_valid,
            "expiry_format_valid": expiry_format_valid,
            "batch_number_valid": batch_number_valid,
            "manufacturer_present": manufacturer_present,
            "drug_name_format_valid": drug_name_format_valid,
            "authenticity_score": authenticity_score,
            "is_structurally_authentic": is_structurally_authentic
        }
