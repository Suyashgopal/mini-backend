import sys
import os

# Add project root to path
sys.path.append(os.path.abspath("."))

from src.services.medical_validation_service import MedicalValidationService

validator = MedicalValidationService()

text = """
Paracetamol 500 mg
Batch No: AB123456
EXP: 12/2026
Manufactured by ABC Pharma Ltd.
"""

print(validator.validate_text(text))
