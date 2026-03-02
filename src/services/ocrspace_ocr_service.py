"""
ocrspace_ocr_service.py

Primary OCR engine using OCR.space API.
Returns same dict format as OllamaOCRService:

  { extracted_text, processing_time, model_name }
  { extracted_text, processing_time, model_name, pages_processed }
"""

import logging
import os
import time
from typing import Dict, Any

import requests

logger = logging.getLogger(__name__)

API_URL = "https://api.ocr.space/parse/image"
MODEL_NAME = "ocr.space"


class OCRSpaceOCRService:
    def __init__(self):
        self.api_key = os.getenv("OCRSPACE_API_KEY", "").strip()
        if not self.api_key:
            raise RuntimeError(
                "OCRSPACE_API_KEY not set. "
                "Get free key at https://ocr.space/ocrapi"
            )
        logger.info("OCRSpaceOCRService ready")

    def _call_api(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            response = requests.post(
                API_URL,
                files={"file": f},
                data={
                    "apikey": self.api_key,
                    "language": "eng",
                    "isOverlayRequired": False,
                },
                timeout=60,
            )

        if response.status_code != 200:
            raise RuntimeError(f"OCR.space HTTP {response.status_code}")

        data = response.json()

        if data.get("IsErroredOnProcessing"):
            raise RuntimeError(str(data.get("ErrorMessage")))

        parsed = data.get("ParsedResults", [])
        if not parsed:
            return ""

        return "\n".join(p.get("ParsedText", "") for p in parsed)

    def process_image(self, image_path: str) -> Dict[str, Any]:
        t0 = time.monotonic()
        text = self._call_api(image_path)

        return {
            "extracted_text": text.strip(),
            "processing_time": round(time.monotonic() - t0, 3),
            "model_name": MODEL_NAME,
        }

    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        t0 = time.monotonic()
        text = self._call_api(pdf_path)

        return {
            "extracted_text": text.strip(),
            "processing_time": round(time.monotonic() - t0, 3),
            "model_name": MODEL_NAME,
            "pages_processed": "all",
        }
