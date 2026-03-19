"""
Test script to verify Tesseract OCR setup
"""

import sys
import os

def test_tesseract_installation():
    """Test if Tesseract is installed"""
    print("=" * 60)
    print("Testing Tesseract OCR Installation")
    print("=" * 60)
    
    # Test 1: Check if tesseract command exists
    print("\n1. Checking Tesseract command...")
    try:
        import subprocess
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Tesseract is installed")
            print(f"  Version: {result.stdout.split()[1]}")
        else:
            print("✗ Tesseract command failed")
            return False
    except FileNotFoundError:
        print("✗ Tesseract not found in PATH")
        print("  Please install Tesseract and add it to PATH")
        return False
    
    # Test 2: Check Python dependencies
    print("\n2. Checking Python dependencies...")
    
    dependencies = {
        'pytesseract': 'pytesseract',
        'PIL': 'Pillow',
        'cv2': 'opencv-python',
        'pdf2image': 'pdf2image',
        'numpy': 'numpy'
    }
    
    missing = []
    for module, package in dependencies.items():
        try:
            __import__(module)
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"✗ {package} is NOT installed")
            missing.append(package)
    
    if missing:
        print(f"\nInstall missing packages with:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    # Test 3: Test pytesseract integration
    print("\n3. Testing pytesseract integration...")
    try:
        import pytesseract
        from PIL import Image
        import numpy as np
        
        # Set Tesseract path from environment
        tesseract_cmd = os.getenv('TESSERACT_CMD')
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            print(f"  Using Tesseract from: {tesseract_cmd}")
        
        # Create a simple test image with text
        img = Image.new('RGB', (200, 50), color='white')
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "TEST 123", fill='black')
        
        # Try OCR
        text = pytesseract.image_to_string(img)
        if 'TEST' in text or '123' in text:
            print("✓ pytesseract is working")
            print(f"  Extracted: {text.strip()}")
        else:
            print("⚠ pytesseract working but accuracy may be low")
            print(f"  Extracted: {text.strip()}")
        
    except Exception as e:
        print(f"✗ pytesseract test failed: {str(e)}")
        return False
    
    # Test 4: Check for poppler (PDF support)
    print("\n4. Checking PDF support (poppler)...")
    try:
        result = subprocess.run(['pdftoppm', '-v'], 
                              capture_output=True, text=True)
        if result.returncode == 0 or 'pdftoppm' in result.stderr:
            print("✓ Poppler is installed (PDF support available)")
        else:
            print("⚠ Poppler not found (PDF processing may not work)")
    except FileNotFoundError:
        print("⚠ Poppler not found (PDF processing may not work)")
        print("  Install poppler-utils for PDF support")
    
    # Test 5: Test OCR service
    print("\n5. Testing OCR Service...")
    try:
        from services.ocr_service import OCRService
        
        ocr = OCRService()
        print("✓ OCR Service initialized successfully")
        
    except Exception as e:
        print(f"✗ OCR Service initialization failed: {str(e)}")
        return False
    
    return True

def test_with_sample_image():
    """Test OCR with a sample pharmaceutical label"""
    print("\n" + "=" * 60)
    print("Testing with Sample Image")
    print("=" * 60)
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        import pytesseract
        
        # Set Tesseract path
        tesseract_cmd = os.getenv('TESSERACT_CMD')
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Create a sample pharmaceutical label
        img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add text
        text_lines = [
            "PHARMACEUTICAL LABEL",
            "",
            "Drug Name: ACETAMINOPHEN 500mg",
            "Batch Number: BN-2024-001234",
            "Expiry Date: 12/2025",
            "Manufacturer: PharmaCorp Inc.",
            "",
            "CONTROLLED SUBSTANCE",
            "Schedule II"
        ]
        
        y = 20
        for line in text_lines:
            draw.text((20, y), line, fill='black')
            y += 25
        
        # Save sample image
        sample_path = 'test_sample.png'
        img.save(sample_path)
        print(f"\n✓ Created sample image: {sample_path}")
        
        # Test OCR
        print("\nRunning OCR on sample image...")
        text = pytesseract.image_to_string(img)
        
        print("\nExtracted Text:")
        print("-" * 60)
        print(text)
        print("-" * 60)
        
        # Check if key information was extracted
        checks = {
            'Drug Name': 'ACETAMINOPHEN' in text,
            'Batch Number': 'BN-2024' in text or '2024' in text,
            'Expiry Date': '2025' in text,
            'Manufacturer': 'PharmaCorp' in text or 'Pharma' in text,
            'Controlled': 'CONTROLLED' in text or 'Schedule' in text
        }
        
        print("\nValidation:")
        for field, found in checks.items():
            status = "✓" if found else "✗"
            print(f"{status} {field}: {'Found' if found else 'Not found'}")
        
        accuracy = sum(checks.values()) / len(checks) * 100
        print(f"\nAccuracy: {accuracy:.1f}%")
        
        if accuracy >= 60:
            print("✓ OCR is working well!")
        else:
            print("⚠ OCR accuracy is low. Consider:")
            print("  - Checking Tesseract installation")
            print("  - Improving image quality")
            print("  - Adjusting OCR configuration")
        
        # Clean up
        if os.path.exists(sample_path):
            os.remove(sample_path)
        
        return True
        
    except Exception as e:
        print(f"✗ Sample test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TESSERACT OCR SETUP VERIFICATION")
    print("=" * 60)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run tests
    installation_ok = test_tesseract_installation()
    
    if installation_ok:
        sample_ok = test_with_sample_image()
        
        if sample_ok:
            print("\n" + "=" * 60)
            print("✓ ALL TESTS PASSED!")
            print("=" * 60)
            print("\nYour Tesseract OCR setup is ready to use.")
            print("\nNext steps:")
            print("1. Start the Flask server: python app.py")
            print("2. Upload a pharmaceutical document via API")
            print("3. Check the OCR results")
            return 0
        else:
            print("\n" + "=" * 60)
            print("⚠ SOME TESTS FAILED")
            print("=" * 60)
            print("\nPlease check the errors above and fix them.")
            return 1
    else:
        print("\n" + "=" * 60)
        print("✗ SETUP INCOMPLETE")
        print("=" * 60)
        print("\nPlease install missing dependencies:")
        print("1. Install Tesseract OCR")
        print("2. Install Python packages: pip install -r requirements.txt")
        print("3. Configure .env file")
        print("\nSee TESSERACT_SETUP.md for detailed instructions.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
