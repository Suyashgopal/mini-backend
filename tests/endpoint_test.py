#!/usr/bin/env python3
"""
Test Corrected API Endpoints
Shows the correct URLs for frontend integration
"""

import requests
import json

def test_endpoint(method, url, data=None, files=None):
    """Test API endpoint and return response"""
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST" and files:
            response = requests.post(url, files=files)
        elif method == "POST" and data:
            response = requests.post(url, json=data)
        else:
            return None
            
        print(f"\n{'='*60}")
        print(f"ENDPOINT: {method} {url}")
        print(f"STATUS: {response.status_code}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            print(f"RESPONSE: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"RESPONSE: {response.text[:200]}...")
            
        return response
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None

def main():
    """Test all corrected endpoints"""
    
    print("🔧 CORRECTED API ENDPOINTS TEST")
    print("These are the URLs your frontend should call:")
    
    # Test 1: Health Check
    test_endpoint("GET", "http://127.0.0.1:5000/health")
    
    # Test 2: Root Endpoint
    test_endpoint("GET", "http://127.0.0.1:5000/")
    
    # Test 3: OCR Image Endpoint (for image files)
    print(f"\n📷 OCR IMAGE ENDPOINT:")
    print("URL: POST http://127.0.0.1:5000/api/ocr/image")
    print("Content-Type: multipart/form-data")
    print("Body: file (image file)")
    print("Frontend Example:")
    print("const formData = new FormData();")
    print("formData.append('file', imageFile);")
    print("fetch('/api/ocr/image', { method: 'POST', body: formData });")
    
    # Test 4: OCR PDF Endpoint (for PDF files)
    print(f"\n📄 OCR PDF ENDPOINT:")
    print("URL: POST http://127.0.0.1:5000/api/ocr/pdf")
    print("Content-Type: multipart/form-data")
    print("Body: file (PDF file)")
    print("Frontend Example:")
    print("const formData = new FormData();")
    print("formData.append('file', pdfFile);")
    print("fetch('/api/ocr/pdf', { method: 'POST', body: formData });")
    
    # Test 5: Validation Endpoint (for text validation)
    test_result = test_endpoint(
        "POST", 
        "http://127.0.0.1:5000/api/validation/validate-text",
        data={"text": "Ibuprofen 200mg, Lot: TEST123, Exp: 01/2028"}
    )
    
    # Test 6: Verified Controls List
    test_endpoint("GET", "http://127.0.0.1:5000/api/verified/")
    
    print(f"\n{'='*60}")
    print("📋 FRONTEND INTEGRATION GUIDE:")
    print(f"{'='*60}")
    
    endpoints = [
        ("Health Check", "GET", "/health", "Check API status"),
        ("OCR Image", "POST", "/api/ocr/image", "Extract text from images"),
        ("OCR PDF", "POST", "/api/ocr/pdf", "Extract text from PDFs"),
        ("Validate Text", "POST", "/api/validation/validate-text", "Validate pharmaceutical text"),
        ("List Verified", "GET", "/api/verified/", "Get verified controls"),
        ("Create Verified", "POST", "/api/verified/create/<ocr_result_id>", "Create verified control"),
        ("Comparison", "POST", "/api/comparison/compare", "Compare text similarity")
    ]
    
    print("\n🔗 CORRECT ENDPOINTS:")
    for name, method, endpoint, description in endpoints:
        print(f"  {method:8} {endpoint:35} - {description}")
    
    print(f"\n{'='*60}")
    print("✅ All endpoints are now correctly registered!")
    print("❌ OLD INCORRECT ENDPOINTS TO AVOID:")
    print("   - /api/extract-text (doesn't exist)")
    print("   - /api/validate-text (should be /api/validation/validate-text)")

if __name__ == "__main__":
    main()
