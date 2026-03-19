#!/usr/bin/env python
"""
Simple script to test Ollama OCR extraction from sampleocr.jpeg
"""

import base64
import requests
import json
from pathlib import Path

# Configuration
OLLAMA_ENDPOINT = "http://localhost:11434"
MODEL_NAME = "glm-ocr:latest"
IMAGE_PATH = "samples/sampleocr.jpeg"

def extract_text_from_image(image_path):
    """Extract text from image using Ollama"""
    
    # Check if image exists
    if not Path(image_path).exists():
        print(f"❌ Error: Image not found at {image_path}")
        return None
    
    print(f"📷 Loading image: {image_path}")
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    print(f"✅ Image loaded and encoded")
    
    # Prepare request to Ollama
    api_endpoint = f"{OLLAMA_ENDPOINT}/api/generate"
    
    payload = {
        "model": MODEL_NAME,
        "prompt": "Extract all text from this image. Return only the extracted text without any explanation or formatting.",
        "images": [image_data],
        "stream": False
    }
    
    print(f"🔄 Sending request to Ollama at {api_endpoint}")
    print(f"📊 Using model: {MODEL_NAME}")
    
    try:
        # Send request to Ollama
        response = requests.post(
            api_endpoint,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ Error: Ollama returned status {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
        # Parse response
        result = response.json()
        extracted_text = result.get('response', '').strip()
        
        if not extracted_text:
            print("❌ Error: No text extracted from image")
            return None
        
        print(f"✅ Text extraction successful!")
        return extracted_text
        
    except requests.Timeout:
        print(f"❌ Error: Request timed out after 60 seconds")
        return None
    except requests.ConnectionError as e:
        print(f"❌ Error: Failed to connect to Ollama at {OLLAMA_ENDPOINT}")
        print(f"Make sure Ollama is running: ollama serve")
        print(f"Details: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def main():
    print("=" * 60)
    print("Ollama OCR Text Extraction Test")
    print("=" * 60)
    print()
    
    # Extract text
    extracted_text = extract_text_from_image(IMAGE_PATH)
    
    if extracted_text:
        print()
        print("=" * 60)
        print("EXTRACTED TEXT:")
        print("=" * 60)
        print(extracted_text)
        print()
        print("=" * 60)
        
        # Save to file
        output_file = "extracted_text.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        print(f"✅ Text saved to {output_file}")
    else:
        print()
        print("❌ Failed to extract text")
        print()
        print("Troubleshooting:")
        print("1. Make sure Ollama is running: ollama serve")
        print("2. Make sure the model is downloaded: ollama pull glm-ocr:latest")
        print("3. Check that Ollama is accessible at http://localhost:11434")

if __name__ == "__main__":
    main()
