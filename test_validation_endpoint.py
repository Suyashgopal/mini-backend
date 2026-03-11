"""
Test the Groq validation endpoint to diagnose issues
"""

import requests
import time

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

print("Testing Groq Validation Endpoint")
print("=" * 60)

url = 'http://localhost:5000/api/validation/validate-text'

print(f"\nEndpoint: {url}")
print(f"Sample text length: {len(sample_text)} characters")
print("\nSending request...")

start_time = time.time()

try:
    response = requests.post(
        url,
        headers={'Content-Type': 'application/json'},
        json={'text': sample_text},
        timeout=30
    )
    
    elapsed = time.time() - start_time
    
    print(f"\n✓ Response received in {elapsed:.2f} seconds")
    print(f"Status Code: {response.status_code}")
    print("\nResponse:")
    print("-" * 60)
    
    if response.status_code == 200:
        result = response.json()
        import json
        print(json.dumps(result, indent=2))
        
        print("\n" + "=" * 60)
        print("EXTRACTED FIELDS:")
        print("=" * 60)
        print(f"Drug Name:        {result.get('drug_name')}")
        print(f"Strength:         {result.get('strength')}")
        print(f"Batch Number:     {result.get('batch_number')}")
        print(f"Expiry Date:      {result.get('expiry_date')}")
        print(f"Manufacturer:     {result.get('manufacturer')}")
        print(f"Risk Level:       {result.get('risk_level')}")
        print(f"Confidence:       {result.get('confidence_score')}%")
        
    else:
        print(f"Error: {response.text}")
        
except requests.exceptions.Timeout:
    print(f"\n❌ Request timed out after 30 seconds")
    print("   The Groq API might be slow or unavailable")
    
except requests.exceptions.ConnectionError:
    print(f"\n❌ Cannot connect to {url}")
    print("   Make sure the Flask server is running")
    
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 60)
