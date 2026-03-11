"""
Pharmaceutical Field Extractor Service

Extracts structured pharmaceutical data (drug name, batch number, expiry date, etc.)
from OCR-extracted text using pattern matching and NLP techniques.
"""

import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PharmaFieldExtractor:
    """Extract pharmaceutical fields from OCR text."""
    
    def __init__(self):
        # Drug name patterns - matches drug name followed by dosage
        self._drug_name_patterns = [
            # Pattern: Drug Name 500mg, Drug Name 10ml, etc.
            re.compile(r'(?:Drug\s+Name|Name|Product)[\s:]+([A-Za-z][A-Za-z\s]+?)\s+\d+(?:\.\d+)?\s?(?:mg|ml|g|mcg|iu|%)', re.IGNORECASE),
            # Pattern: DRUG NAME in caps followed by dosage
            re.compile(r'\b([A-Z][A-Z\s]{2,30}?)\s+\d+(?:\.\d+)?\s?(?:mg|ml|g|mcg|iu|%)\b'),
            # Pattern: Drug Name: VALUE
            re.compile(r'(?:Drug\s+Name|Name|Product)[\s:]+([A-Za-z][A-Za-z\s]+?)(?:\n|$|\.)', re.IGNORECASE),
        ]
        
        # Batch/Lot number patterns
        self._batch_patterns = [
            re.compile(r'(?:Batch|Lot)[\s#:]+([A-Z0-9\-]{6,20})', re.IGNORECASE),
            re.compile(r'\b(LOT|BATCH)[\s:]+([A-Z0-9\-]{6,20})\b', re.IGNORECASE),
        ]
        
        # Expiry date patterns
        self._expiry_patterns = [
            re.compile(r'(?:Exp|Expiry|Expiration)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', re.IGNORECASE),
            re.compile(r'(?:Exp|Expiry|Expiration)[\s:]+([A-Z]{3}\s+\d{4})', re.IGNORECASE),
            re.compile(r'(?:Exp|Expiry|Expiration)[\s:]+(\d{4}[/-]\d{1,2}[/-]\d{1,2})', re.IGNORECASE),
        ]
        
        # Manufacturer patterns
        self._manufacturer_patterns = [
            re.compile(r'(?:Manufacturer|Mfg|Made\s+by)[\s:]+([A-Za-z][A-Za-z\s&.,]+?)(?:\n|$|\.)', re.IGNORECASE),
            re.compile(r'(?:Manufactured\s+by)[\s:]+([A-Za-z][A-Za-z\s&.,]+?)(?:\n|$|\.)', re.IGNORECASE),
        ]
        
        # Strength/Dosage patterns
        self._strength_patterns = [
            re.compile(r'(?:Strength|Dosage)[\s:]+(\d+(?:\.\d+)?\s?(?:mg|ml|g|mcg|iu|%))', re.IGNORECASE),
            re.compile(r'\b(\d+(?:\.\d+)?\s?(?:mg|ml|g|mcg|iu|%))\b'),
        ]
        
        # License/NDC number patterns
        self._license_patterns = [
            re.compile(r'(?:NDC|License|Lic)[\s#:]+(\d{4,5}[-\s]?\d{3,4}[-\s]?\d{1,2})', re.IGNORECASE),
        ]
    
    def extract_fields(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract pharmaceutical fields from OCR text.
        
        Args:
            text: Raw OCR-extracted text
            
        Returns:
            Dictionary with extracted fields (drug_name, batch_number, expiry_date, etc.)
        """
        if not text or not text.strip():
            return self._empty_result()
        
        return {
            'drug_name': self._extract_drug_name(text),
            'batch_number': self._extract_batch_number(text),
            'expiry_date': self._extract_expiry_date(text),
            'manufacturer': self._extract_manufacturer(text),
            'strength': self._extract_strength(text),
            'license_number': self._extract_license_number(text),
        }
    
    def _extract_drug_name(self, text: str) -> Optional[str]:
        """Extract drug name from text."""
        for pattern in self._drug_name_patterns:
            match = pattern.search(text)
            if match:
                drug_name = match.group(1).strip()
                # Clean up extra whitespace
                drug_name = ' '.join(drug_name.split())
                if len(drug_name) >= 3:  # Minimum 3 characters
                    logger.debug(f"Extracted drug name: {drug_name}")
                    return drug_name
        return None
    
    def _extract_batch_number(self, text: str) -> Optional[str]:
        """Extract batch/lot number from text."""
        for pattern in self._batch_patterns:
            match = pattern.search(text)
            if match:
                # Get the last group (the actual batch number)
                batch = match.group(match.lastindex).strip()
                logger.debug(f"Extracted batch number: {batch}")
                return batch
        return None
    
    def _extract_expiry_date(self, text: str) -> Optional[str]:
        """Extract expiry date from text."""
        for pattern in self._expiry_patterns:
            match = pattern.search(text)
            if match:
                expiry = match.group(1).strip()
                logger.debug(f"Extracted expiry date: {expiry}")
                return expiry
        return None
    
    def _extract_manufacturer(self, text: str) -> Optional[str]:
        """Extract manufacturer name from text."""
        for pattern in self._manufacturer_patterns:
            match = pattern.search(text)
            if match:
                manufacturer = match.group(1).strip()
                # Clean up
                manufacturer = ' '.join(manufacturer.split())
                if len(manufacturer) >= 3:
                    logger.debug(f"Extracted manufacturer: {manufacturer}")
                    return manufacturer
        return None
    
    def _extract_strength(self, text: str) -> Optional[str]:
        """Extract drug strength/dosage from text."""
        for pattern in self._strength_patterns:
            match = pattern.search(text)
            if match:
                strength = match.group(1).strip()
                logger.debug(f"Extracted strength: {strength}")
                return strength
        return None
    
    def _extract_license_number(self, text: str) -> Optional[str]:
        """Extract license/NDC number from text."""
        for pattern in self._license_patterns:
            match = pattern.search(text)
            if match:
                license_num = match.group(1).strip()
                logger.debug(f"Extracted license number: {license_num}")
                return license_num
        return None
    
    def _empty_result(self) -> Dict[str, None]:
        """Return empty result structure."""
        return {
            'drug_name': None,
            'batch_number': None,
            'expiry_date': None,
            'manufacturer': None,
            'strength': None,
            'license_number': None,
        }


# Module-level singleton
pharma_extractor = PharmaFieldExtractor()
