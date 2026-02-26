#!/usr/bin/env python3
"""
Test Samples for Groq Validation Service
Run this script to test various pharmaceutical label scenarios
"""

import requests
import json

def test_validation_service(test_name, text):
    """Test the validation service with given text"""
    url = "http://127.0.0.1:5000/api/validate-text"
    payload = {"text": text}
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        print(f"\n{'='*60}")
        print(f"TEST: {test_name}")
        print(f"{'='*60}")
        print(f"INPUT TEXT:\n{text}")
        print(f"\nVALIDATION RESULT:")
        print(json.dumps(result, indent=2))
        
        if result.get('success') == False:
            print(f"❌ ERROR: {result.get('error')}")
        else:
            print(f"✅ SUCCESS")
            print(f"📊 Risk Level: {result.get('risk_level')}")
            print(f"🎯 Confidence: {result.get('confidence_score')}%")
            print(f"📋 Format Valid: {result.get('format_valid')}")
            
        return result
        
    except Exception as e:
        print(f"❌ REQUEST FAILED: {e}")
        return None

def main():
    """Run all test samples"""
    
    print("🧪 GROQ VALIDATION SERVICE TEST SUITE")
    print("Testing pharmaceutical label validation scenarios...")
    
    # Test 1: Complete Valid Label
    test_validation_service(
        "COMPLETE VALID LABEL",
        """Ibuprofen 200mg Tablets
Brand: Pain Relief Plus
UPC: 012345678901
Active Ingredient: Ibuprofen 200mg (NSAID)
Manufactured by: Consumer Health Corp.
Lot: IB20240115
Exp: 01/2027
License: PHM-2024-001"""
    )
    
    # Test 2: Minimal Valid Label
    test_validation_service(
        "MINIMAL VALID LABEL", 
        "Paracetamol 500mg, Lot: IB20240115, Exp: 01/2027, Manufacturer: PharmaCorp"
    )
    
    # Test 3: Missing Critical Information
    test_validation_service(
        "MISSING CRITICAL INFO",
        "Aspirin Tablets, Brand: HeadAway, Manufacturer: MedCorp"
    )
    
    # Test 4: Suspicious Formatting
    test_validation_service(
        "SUSPICIOUS FORMATTING",
        """DRUG: xyz123fake
STRENGTH: 999mg (unusual dosage)
LOT: FAKE2024
EXP: 01/2020 (expired)
MFR: Unknown Company
LICENSE: INVALID-LICENSE-NUMBER"""
    )
    
    # Test 5: Prescription Drug Label
    test_validation_service(
        "PRESCRIPTION DRUG",
        """Amoxicillin 500mg Capsules
Rx Only - Prescription Required
Manufacturer: Pharma Laboratories
NDC: 12345-678-90
Lot: AMX20241201
Exp: 12/2026
License: DEA-XYZ123"""
    )
    
    # Test 6: OTC Drug with Warnings
    test_validation_service(
        "OTC DRUG WITH WARNINGS",
        """Acetaminophen 325mg Tablets
Warnings: 
- Do not exceed 6 tablets in 24 hours
- May cause liver damage
- Consult doctor if pregnant
Manufacturer: HealthFirst Inc.
Lot: ACQ20240315
Exp: 03/2028"""
    )
    
    # Test 7: Vaccine Label
    test_validation_service(
        "VACCINE LABEL",
        """COVID-19 mRNA Vaccine
Pfizer-BioNTech
Batch: CV202402001
Manufacture: 02/2024
Expiry: 08/2024
License: EUA-12345
Storage: 2-8°C"""
    )
    
    # Test 8: Medical Device
    test_validation_service(
        "MEDICAL DEVICE",
        """Insulin Pen Device
Brand: GlucoCare
Manufacturer: MedTech Solutions
Serial Number: MT2024001234
Lot: INS202401
Manufacture: 01/2024
Expiry: 01/2026
License: FDA-510K-123456"""
    )
    
    # Test 9: Herbal Supplement
    test_validation_service(
        "HERBAL SUPPLEMENT",
        """Echinacea 400mg Capsules
Dietary Supplement
Brand: Natural Health
Manufacturer: Herbal Remedies Inc.
Lot: HRN20240501
Exp: 05/2026
Not evaluated by FDA"""
    )
    
    # Test 10: Invalid/Empty Input
    test_validation_service(
        "EMPTY INPUT",
        ""
    )
    
    print(f"\n{'='*60}")
    print("🏁 TEST SUITE COMPLETE")
    print(f"{'='*60}")
    print("\n📝 Summary:")
    print("- Test various pharmaceutical label formats")
    print("- Verify risk assessment accuracy")
    print("- Check confidence scoring")
    print("- Validate field extraction")
    print("- Test error handling")

if __name__ == "__main__":
    main()
