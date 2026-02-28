"""
Example usage of the OCR System
Primary: Ollama
Fallback: Tesseract
Includes translation with chunking
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ======================================================
# Example 1: Image OCR (Auto Fallback)
# ======================================================

def example_basic_ocr():
    print("=" * 60)
    print("Example 1: Image OCR (Auto Fallback)")
    print("=" * 60)

    from services.ollama_ocr_service import OllamaOCRService
    from services.ocr_service import OCRService

    ollama = OllamaOCRService()
    tesseract = OCRService()

    image_path = "uploads/sample_label.jpg"

    if not os.path.exists(image_path):
        print(f"⚠ Image not found: {image_path}")
        return

    print(f"\nProcessing: {image_path}")

    try:
        result = ollama.process_image(image_path)
        engine = "ollama"
    except Exception as e:
        print(f"⚠ Ollama failed: {e}")
        print("→ Switching to Tesseract fallback")
        result = tesseract.process_image(image_path)
        engine = "tesseract"

    print("\n--- OCR Result ---")
    print(f"Engine Used: {engine}")
    print(f"Confidence: {result['confidence_score']:.2%}")
    print(f"Processing Time: {result['processing_time']:.2f}s")

    print("\nExtracted Text:")
    print("-" * 60)
    print(result["extracted_text"])
    print("-" * 60)

    print("\nTranslated Text:")
    print("-" * 60)
    print(result.get("translated_text", "N/A"))
    print("-" * 60)


# ======================================================
# Example 2: PDF OCR
# ======================================================

def example_pdf_processing():
    print("\n" + "=" * 60)
    print("Example 2: PDF OCR")
    print("=" * 60)

    from services.ollama_ocr_service import OllamaOCRService
    from services.ocr_service import OCRService

    ollama = OllamaOCRService()
    tesseract = OCRService()

    pdf_path = "uploads/sample_document.pdf"

    if not os.path.exists(pdf_path):
        print(f"⚠ PDF not found: {pdf_path}")
        return

    print(f"\nProcessing: {pdf_path}")

    try:
        result = ollama.process_pdf(pdf_path)
        engine = "ollama"
    except Exception:
        print("⚠ Ollama failed → Using Tesseract")
        result = tesseract.process_pdf(pdf_path)
        engine = "tesseract"

    print("\n--- PDF OCR Result ---")
    print(f"Engine Used: {engine}")
    print(f"Confidence: {result['confidence_score']:.2%}")
    print(f"Processing Time: {result['processing_time']:.2f}s")

    print("\nExtracted Text (first 500 chars):")
    print("-" * 60)
    print(result["extracted_text"][:500])
    print("-" * 60)


# ======================================================
# Example 3: Batch Processing
# ======================================================

def example_batch_processing():
    print("\n" + "=" * 60)
    print("Example 3: Batch Processing")
    print("=" * 60)

    import glob
    from services.ollama_ocr_service import OllamaOCRService
    from services.ocr_service import OCRService

    ollama = OllamaOCRService()
    tesseract = OCRService()

    image_files = glob.glob("uploads/*.jpg") + glob.glob("uploads/*.png")

    if not image_files:
        print("⚠ No images found in uploads folder")
        return

    print(f"\nFound {len(image_files)} images")

    results = []

    for image_path in image_files:
        print(f"\nProcessing: {os.path.basename(image_path)}")

        try:
            result = ollama.process_image(image_path)
            engine = "ollama"
        except Exception:
            result = tesseract.process_image(image_path)
            engine = "tesseract"

        results.append(result["confidence_score"])

        print(f"  ✓ Engine: {engine}")
        print(f"  ✓ Confidence: {result['confidence_score']:.2%}")

    print("\n--- Batch Summary ---")

    if results:
        avg_confidence = sum(results) / len(results)
        print(f"Average Confidence: {avg_confidence:.2%}")
        print(f"Total Processed: {len(results)}")


# ======================================================
# MAIN
# ======================================================

def main():
    print("\n" + "=" * 60)
    print("OCR SYSTEM - USAGE EXAMPLES")
    print("=" * 60)

    examples = [
        example_basic_ocr,
        example_pdf_processing,
        example_batch_processing,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n✗ Example failed: {e}")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()