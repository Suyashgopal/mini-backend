"""
Test script for pharmaceutical field extraction

This demonstrates how the pharma field extractor works with sample text.
"""

from src.services.pharma_field_extractor import pharma_extractor

# Sample OCR text from a pharmaceutical label
sample_text = """
PHARMACEUTICAL LABEL

Drug Name: ACETAMINOPHEN 500mg
Batch Number: BN-2024-001234
Expiry Date: 12/2025
Manufacturer: Pfizer Inc.
NDC: 0071-0155-23

Dosage: Take 1 tablet every 4-6 hours as needed
"""

print("=" * 60)
print("PHARMACEUTICAL FIELD EXTRACTION TEST")
print("=" * 60)
print("\nSample OCR Text:")
print("-" * 60)
print(sample_text)
print("-" * 60)

# Extract fields
fields = pharma_extractor.extract_fields(sample_text)

print("\nExtracted Fields:")
print("-" * 60)
for field_name, field_value in fields.items():
    status = "✓" if field_value else "✗"
    print(f"{status} {field_name:20s}: {field_value or 'Not detected'}")
print("=" * 60)
