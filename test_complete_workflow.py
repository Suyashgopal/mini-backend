"""
Test Complete Pharmaceutical Extraction Workflow

This demonstrates both pattern-based and AI-based extraction.
"""

import requests
import json

# Sample pharmaceutical label text
sample_text = """
PHARMACEUTICAL LABEL

Drug Name: ACETAMINOPHEN 500mg
Batch Number: BN-2024-001234
Expiry Date: 12/2025
Manufacturer: Pfizer Inc.
NDC: 0071-0155-23

Dosage: Take 1 tablet every 4-6 hours as needed
Storage: Store at room temperature
"""

print("=" * 70)
print("COMPLETE PHARMACEUTICAL EXTRACTION WORKFLOW TEST")
print("=" * 70)

print("\nSample Label Text:")
print("-" * 70)
print(sample_text)
print("-" * 70)

# Test Groq AI Validation
print("\n🤖 Testing Groq AI Validation...")
print("-" * 70)

try:
    response = requests.post(
        'http://localhost:5000/api/validation/validate-text',
        headers={'Content-Type': 'application/json'},
        json={'text': sample_text},
        timeout=30
    )
    
    if response.status_code == 200:
        validation_result = response.json()
        
        print("✓ Groq Validation Successful!\n")
        print(f"Drug Name:        {validation_result.get('drug_name', 'N/A')}")
        print(f"Strength:         {validation_result.get('strength', 'N/A')}")
        print(f"Batch Number:     {validation_result.get('batch_number', 'N/A')}")
        print(f"Expiry Date:      {validation_result.get('expiry_date', 'N/A')}")
        print(f"Manufacturer:     {validation_result.get('manufacturer', 'N/A')}")
        print(f"License Number:   {validation_result.get('license_number', 'N/A')}")
        print(f"\nRisk Level:       {validation_result.get('risk_level', 'N/A')}")
        print(f"Confidence:       {validation_result.get('confidence_score', 'N/A')}%")
        print(f"Missing Fields:   {', '.join(validation_result.get('missing_fields', [])) or 'None'}")
        print(f"\nAnalysis: {validation_result.get('analysis_summary', 'N/A')}")
        
    elif response.status_code == 503:
        print("⚠️  Groq validation is not configured")
        print("   Make sure GROQ_API_KEY is set in .env and restart the server")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to backend server")
    print("   Make sure the Flask server is running on http://localhost:5000")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("\nTo test with an actual image:")
print("  1. Start the backend: python src/app.py")
print("  2. Upload an image to: POST http://localhost:5000/api/ocr/image")
print("  3. Use the extracted_text in: POST http://localhost:5000/api/validation/validate-text")
print("=" * 70)
