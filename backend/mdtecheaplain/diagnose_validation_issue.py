"""
Diagnostic script to identify validation issues

This script will:
1. Check if backend is running
2. Test all validation endpoints
3. Show what's working and what's not
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_endpoint(name, method, url, data=None, files=None):
    """Test an endpoint and report results"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    print(f"Method: {method}")
    print(f"URL: {url}")
    
    try:
        start = time.time()
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            if files:
                response = requests.post(url, files=files, timeout=30)
            else:
                response = requests.post(
                    url,
                    headers={'Content-Type': 'application/json'},
                    json=data,
                    timeout=30
                )
        
        elapsed = time.time() - start
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Response Time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✓ Response Type: JSON")
                print(f"\nResponse Preview:")
                print(json.dumps(result, indent=2)[:500])
                return True, result
            except:
                print(f"✓ Response Type: Text")
                print(f"\nResponse: {response.text[:200]}")
                return True, response.text
        else:
            print(f"✗ Error Response: {response.text[:200]}")
            return False, None
            
    except requests.exceptions.Timeout:
        print(f"✗ TIMEOUT after 30 seconds")
        return False, None
    except requests.exceptions.ConnectionError:
        print(f"✗ CONNECTION ERROR - Server not running?")
        return False, None
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False, None

print("="*60)
print("BACKEND VALIDATION DIAGNOSTIC")
print("="*60)

# Test 1: Health Check
success, _ = test_endpoint(
    "Health Check",
    "GET",
    f"{BASE_URL}/health"
)

if not success:
    print("\n" + "="*60)
    print("❌ BACKEND IS NOT RUNNING!")
    print("="*60)
    print("\nPlease start the backend server:")
    print("  python src/app.py")
    exit(1)

# Test 2: Root Endpoint
test_endpoint(
    "Root Endpoint",
    "GET",
    f"{BASE_URL}/"
)

# Test 3: Groq Validation
sample_text = """
Drug Name: ASPIRIN 500mg
Batch Number: ABC-123
Expiry Date: 12/2025
Manufacturer: Test Pharma
"""

success, result = test_endpoint(
    "Groq Validation Endpoint",
    "POST",
    f"{BASE_URL}/api/validation/validate-text",
    data={"text": sample_text}
)

if success and result:
    print("\n" + "="*60)
    print("✅ GROQ VALIDATION IS WORKING!")
    print("="*60)
    print(f"Drug Name: {result.get('drug_name')}")
    print(f"Batch Number: {result.get('batch_number')}")
    print(f"Risk Level: {result.get('risk_level')}")
    print(f"Confidence: {result.get('confidence_score')}%")

# Test 4: List all available endpoints
print("\n" + "="*60)
print("CHECKING ALL REGISTERED ENDPOINTS")
print("="*60)

success, result = test_endpoint(
    "List Endpoints",
    "GET",
    f"{BASE_URL}/"
)

if success and isinstance(result, dict):
    endpoints = result.get('available_endpoints', [])
    print("\nAvailable Endpoints:")
    for endpoint in endpoints:
        print(f"  • {endpoint}")

print("\n" + "="*60)
print("DIAGNOSIS COMPLETE")
print("="*60)

print("\n📋 SUMMARY:")
print("  • Backend is running: ✓")
print("  • Health endpoint: ✓")
print("  • Validation endpoint: ✓" if success else "  • Validation endpoint: ✗")

print("\n💡 NEXT STEPS:")
print("  1. If validation is working here but not in your frontend:")
print("     → The issue is in your frontend code")
print("     → Check browser console (F12) for errors")
print("     → Check Network tab to see actual requests")
print("  ")
print("  2. Open test_validation_frontend.html in your browser")
print("     → This will test the validation from a real browser")
print("  ")
print("  3. Check your frontend code:")
print("     → Make sure it's calling: POST /api/validation/validate-text")
print("     → Make sure request body has: { \"text\": \"...\" }")
print("     → Make sure it's not stuck in a loading state")

print("\n" + "="*60)
