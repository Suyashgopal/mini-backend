"""
gemini_ocr_service.py

Primary OCR engine using Google Gemini 2.0 Flash vision API.
Handles both images and PDFs natively — no Poppler, no pdf2image,
no OpenCV preprocessing required.

Returns dicts with the same keys as OllamaOCRService so both
engines are drop-in interchangeable:
  { extracted_text, processing_time, model_name }
  { extracted_text, processing_time, model_name, pages_processed }  # PDF only
"""

import io
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Gemini SDK — imported lazily so the server starts even if the
# package is missing (graceful degradation to Ollama fallback).
try:
    import google.generativeai as genai
    from PIL import Image as PILImage
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning(
        "google-generativeai or Pillow not installed. "
        "Run: pip install google-generativeai"
    )

MODEL_NAME   = "gemini-2.0-flash"
OCR_PROMPT   = (
    "Extract all text from this pharmaceutical label exactly as it appears. "
    "Return only the extracted text — no explanations, no formatting, no extra words."
)
API_TIMEOUT  = 30   # seconds


class GeminiOCRService:
    """
    OCR service backed by Gemini 2.0 Flash.
    Raises RuntimeError on any failure so the caller can fall back to Ollama.
    """

    def __init__(self):
        if not GEMINI_AVAILABLE:
            raise RuntimeError(
                "google-generativeai package is not installed. "
                "Run: pip install google-generativeai"
            )

        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "Get a free key at https://aistudio.google.com and add it to .env"
            )

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(MODEL_NAME)
        logger.info("GeminiOCRService ready | model=%s", MODEL_NAME)

    # ------------------------------------------------------------------
    # Public API  (same signatures as OllamaOCRService)
    # ------------------------------------------------------------------

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """Extract text from a single image file."""
        t0 = time.monotonic()

        with open(image_path, "rb") as fh:
            image_bytes = fh.read()

        pil_image = PILImage.open(io.BytesIO(image_bytes))

        try:
            response = self._model.generate_content(
                [OCR_PROMPT, pil_image],
                request_options={"timeout": API_TIMEOUT},
            )
            text = response.text.strip()
        except Exception as exc:
            raise RuntimeError(f"Gemini image OCR failed: {exc}") from exc

        return {
            "extracted_text":  text,
            "processing_time": round(time.monotonic() - t0, 3),
            "model_name":      MODEL_NAME,
        }

    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text from a PDF using Gemini's native file API.
        No Poppler, no pdf2image, no page-by-page loop required.
        """
        t0 = time.monotonic()
        path = Path(pdf_path)

        if not path.exists():
            raise RuntimeError(f"PDF not found: {pdf_path}")

        try:
            # Upload the PDF to Gemini Files API (handles multi-page natively)
            uploaded = genai.upload_file(str(path), mime_type="application/pdf")

            response = self._model.generate_content(
                [OCR_PROMPT, uploaded],
                request_options={"timeout": API_TIMEOUT},
            )
            text = response.text.strip()

            # Clean up the uploaded file from Gemini servers immediately
            try:
                genai.delete_file(uploaded.name)
            except Exception:
                pass   # Non-critical — Gemini auto-deletes after 48h anyway

        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Gemini PDF OCR failed: {exc}") from exc

        return {
            "extracted_text":  text,
            "processing_time": round(time.monotonic() - t0, 3),
            "model_name":      MODEL_NAME,
            "pages_processed": "all",   # Gemini processes the full PDF in one shot
        }
