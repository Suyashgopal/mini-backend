"""
Optimized Ollama OCR Service
CPU-friendly, memory-efficient, for images and PDFs.
Extracts text only — no extra processing.
"""

import time
import base64
import requests
import logging
from typing import Dict, Any
import os

try:
    import cv2
    import numpy as np
    from PIL import Image
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("Warning: OpenCV/PIL not available. Image preprocessing limited.")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class OllamaOCRService:
    def __init__(
        self,
        ollama_endpoint: str,
        model_name: str,
        timeout: int = 600,  # long timeout for CPU
        max_retries: int = 3,
        retry_delay: int = 5
    ):
        self.ollama_endpoint = ollama_endpoint.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.api_endpoint = f"{self.ollama_endpoint}/api/generate"

    # -------------------------------
    # IMAGE OCR
    # -------------------------------
    def process_image(self, image_path: str) -> Dict[str, Any]:
        start_time = time.time()
        image_bytes = self._preprocess_image(image_path)
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        text = self._send_to_ollama(image_base64)

        return {
            "extracted_text": text,
            "processing_time": round(time.time() - start_time, 2),
            "model_name": self.model_name
        }

    # -------------------------------
    # PDF OCR
    # -------------------------------
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        from pdf2image import convert_from_path
        import io

        start_time = time.time()

        images = convert_from_path(pdf_path, dpi=150)  # moderate resolution

        all_text = []

        for page_num, page in enumerate(images, 1):
            # Convert PIL page to bytes
            img_byte_arr = io.BytesIO()
            page.save(img_byte_arr, format="PNG")
            page_bytes = img_byte_arr.getvalue()

            # Optional: preprocess page
            page_bytes = self._preprocess_image_bytes(page_bytes)

            # Send to Ollama
            page_text = self._send_to_ollama(base64.b64encode(page_bytes).decode("utf-8"))
            all_text.append(page_text)

        combined_text = "\n--- Page Break ---\n".join(all_text)

        return {
            "extracted_text": combined_text,
            "processing_time": round(time.time() - start_time, 2),
            "model_name": self.model_name,
            "pages_processed": len(images)
        }

    # -------------------------------
    # SEND TO OLLAMA
    # -------------------------------
    def _send_to_ollama(self, image_base64: str) -> str:
        payload = {
            "model": self.model_name,
            "prompt": "Extract all text from this image. Return only the extracted text.",
            "images": [image_base64],
            "stream": False
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(self.api_endpoint, json=payload, timeout=self.timeout)
                if response.status_code == 200:
                    result = response.json()
                    text = result.get("response", "").strip()
                    if not text:
                        logger.warning("Ollama returned empty response")
                    return text
                else:
                    logger.warning(f"Ollama API {response.status_code}: {response.text}")
            except requests.Timeout:
                logger.warning(f"Ollama request timed out (attempt {attempt})")
            except requests.ConnectionError as e:
                logger.warning(f"Connection error to Ollama: {str(e)}")
            time.sleep(self.retry_delay)

        raise Exception(f"Ollama OCR failed after {self.max_retries} retries")

    # -------------------------------
    # IMAGE PREPROCESSING
    # -------------------------------
    def _preprocess_image(self, image_path: str) -> bytes:
        if not OPENCV_AVAILABLE:
            with open(image_path, "rb") as f:
                return f.read()

        image = cv2.imread(image_path)
        if image is None:
            from PIL import Image as PILImage
            image = np.array(PILImage.open(image_path))

        return self._preprocess_image_array(image)

    def _preprocess_image_bytes(self, image_bytes: bytes) -> bytes:
        if not OPENCV_AVAILABLE:
            return image_bytes

        import io
        np_arr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if image is None:
            return image_bytes

        return self._preprocess_image_array(image)

    def _preprocess_image_array(self, image: Any) -> bytes:
        # Resize if too large
        max_width = 1200
        if image.shape[1] > max_width:
            ratio = max_width / image.shape[1]
            new_height = int(image.shape[0] * ratio)
            image = cv2.resize(image, (max_width, new_height), interpolation=cv2.INTER_AREA)

        # Grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Adaptive threshold
        processed = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 11, 2)

        # Convert to PNG bytes
        _, buffer = cv2.imencode(".png", processed)
        return buffer.tobytes()