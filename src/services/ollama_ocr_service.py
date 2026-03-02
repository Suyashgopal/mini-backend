"""
ollama_ocr_service.py — Optimized OCR service using Ollama LLM.

Key improvements over original:
  - Parallel page processing for PDFs (ThreadPoolExecutor)
  - Adaptive image preprocessing: skip heavy CV2 pipeline for already-clean images
  - Reduced default timeout + per-request deadline instead of one giant timeout
  - Exponential back-off instead of fixed retry delay
  - Lazy Tesseract fallback wired directly into this service (no round-trip to route layer)
  - hashlib-based in-memory cache to skip re-encoding identical images
  - Cleaner logging with structured context
"""

import base64
import hashlib
import io
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from functools import lru_cache
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional heavy dependencies — imported lazily so the service still starts
# when they are absent.
# ---------------------------------------------------------------------------

def _try_import_cv2():
    try:
        import cv2
        import numpy as np
        return cv2, np
    except ImportError:
        return None, None

def _try_import_pil():
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None

def _try_import_pdf2image():
    try:
        from pdf2image import convert_from_path
        return convert_from_path
    except ImportError:
        return None

def _try_import_pytesseract():
    try:
        import pytesseract
        return pytesseract
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Simple in-process image cache  (keyed by SHA-256 of raw bytes)
# Prevents re-encoding and re-sending identical images when the same file
# is uploaded more than once within a process lifetime.
# ---------------------------------------------------------------------------

_IMAGE_CACHE: Dict[str, str] = {}   # sha256 → base64 string
_MAX_CACHE_ENTRIES = 128


def _cache_get(sha: str) -> Optional[str]:
    return _IMAGE_CACHE.get(sha)


def _cache_set(sha: str, b64: str) -> None:
    if len(_IMAGE_CACHE) >= _MAX_CACHE_ENTRIES:
        # evict oldest entry (insertion-order dict in Python 3.7+)
        _IMAGE_CACHE.pop(next(iter(_IMAGE_CACHE)))
    _IMAGE_CACHE[sha] = b64


# ---------------------------------------------------------------------------
# Main service class
# ---------------------------------------------------------------------------

class OllamaOCRService:
    """OCR service backed by an Ollama vision model with Tesseract fallback."""

    DEFAULT_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
    DEFAULT_MODEL    = os.getenv("OLLAMA_MODEL", "glm-ocr:latest")

    # Reduced from 600 s — most images should finish in well under a minute.
    # Raise via env var if your hardware is truly that slow.
    DEFAULT_TIMEOUT  = int(os.getenv("OLLAMA_TIMEOUT", "120"))

    # Max worker threads for parallel PDF-page processing.
    DEFAULT_PDF_WORKERS = int(os.getenv("OLLAMA_PDF_WORKERS", "4"))

    def __init__(
        self,
        ollama_endpoint: str = DEFAULT_ENDPOINT,
        model_name:      str = DEFAULT_MODEL,
        timeout:         int = DEFAULT_TIMEOUT,
        max_retries:     int = 3,
        retry_delay:     float = 1.0,   # base delay; doubles on each retry (exp back-off)
        pdf_workers:     int = DEFAULT_PDF_WORKERS,
        use_tesseract_fallback: bool = True,
    ):
        self.api_url   = f"{ollama_endpoint.rstrip('/')}/api/generate"
        self.model     = model_name
        self.timeout   = timeout
        self.max_retries   = max_retries
        self.retry_delay   = retry_delay
        self.pdf_workers   = pdf_workers
        self.use_tesseract_fallback = use_tesseract_fallback

        self._cv2, self._np = _try_import_cv2()
        self._Image          = _try_import_pil()
        self._convert_pdf    = _try_import_pdf2image()
        self._tesseract      = _try_import_pytesseract() if use_tesseract_fallback else None

        logger.info(
            "OllamaOCRService ready | model=%s endpoint=%s timeout=%ss workers=%s",
            self.model, self.api_url, self.timeout, self.pdf_workers,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_image(self, image_path: str) -> Dict:
        """Extract text from a single image file."""
        t0 = time.monotonic()
        image_bytes = self._preprocess_image(image_path)
        text = self._extract_text(image_bytes, context=image_path)
        return {
            "extracted_text":  text,
            "processing_time": round(time.monotonic() - t0, 3),
            "model_name":      self.model,
        }

    def process_pdf(self, pdf_path: str) -> Dict:
        """Extract text from every page of a PDF, processing pages in parallel."""
        if self._convert_pdf is None:
            raise RuntimeError("pdf2image is not installed — cannot process PDFs.")

        t0 = time.monotonic()

        # Detect Poppler path on Windows automatically
        poppler_path = self._find_poppler_path()
        convert_kwargs: Dict = {"dpi": 200}
        if poppler_path:
            convert_kwargs["poppler_path"] = poppler_path

        logger.info("Converting PDF to images: %s", pdf_path)
        pages: List = self._convert_pdf(pdf_path, **convert_kwargs)

        if not pages:
            return {
                "extracted_text":  "",
                "processing_time": round(time.monotonic() - t0, 3),
                "model_name":      self.model,
                "pages_processed": 0,
            }

        logger.info("Processing %d page(s) with %d worker(s)", len(pages), min(self.pdf_workers, len(pages)))

        # ---- Parallel page processing ----------------------------------------
        page_texts: List[Optional[str]] = [None] * len(pages)

        with ThreadPoolExecutor(max_workers=min(self.pdf_workers, len(pages))) as pool:
            future_to_idx = {
                pool.submit(self._process_pil_page, page, idx): idx
                for idx, page in enumerate(pages)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    page_texts[idx] = future.result(timeout=self.timeout + 10)
                except FuturesTimeout:
                    logger.warning("Page %d timed out — skipping.", idx + 1)
                    page_texts[idx] = f"[Page {idx + 1}: timeout]"
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Page %d failed: %s", idx + 1, exc)
                    page_texts[idx] = f"[Page {idx + 1}: error — {exc}]"

        combined = "\n\n--- Page Break ---\n\n".join(t for t in page_texts if t)
        return {
            "extracted_text":  combined,
            "processing_time": round(time.monotonic() - t0, 3),
            "model_name":      self.model,
            "pages_processed": len(pages),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_pil_page(self, pil_image, page_index: int) -> str:
        """Preprocess one PIL page image and send to Ollama."""
        img_bytes = self._preprocess_pil_image(pil_image)
        return self._extract_text(img_bytes, context=f"page {page_index + 1}")

    def _extract_text(self, image_bytes: bytes, context: str = "") -> str:
        """Send image bytes to Ollama (with retry + fallback) and return text."""
        sha = hashlib.sha256(image_bytes).hexdigest()
        cached = _cache_get(sha)
        if cached is not None:
            logger.debug("Cache hit for %s", context)
            return cached

        b64 = base64.b64encode(image_bytes).decode("utf-8")

        try:
            text = self._send_to_ollama(b64, context=context)
            _cache_set(sha, text)
            return text
        except Exception as ollama_err:  # noqa: BLE001
            logger.warning("Ollama failed for %s (%s) — trying Tesseract fallback.", context, ollama_err)
            if self._tesseract and self._Image:
                return self._tesseract_fallback(image_bytes, context)
            raise

    def _send_to_ollama(self, image_base64: str, context: str = "") -> str:
        """POST to Ollama API with exponential back-off retry."""
        payload = {
            "model":  self.model,
            "prompt": "Extract all text from this image. Return only the extracted text.",
            "images": [image_base64],
            "stream": False,
        }
        delay = self.retry_delay
        last_exc: Exception = RuntimeError("No attempts made")

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(self.api_url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                text = data.get("response", "").strip()
                if not text:
                    raise ValueError("Empty response from Ollama")
                logger.debug("Ollama OK for %s (attempt %d)", context, attempt)
                return text

            except requests.exceptions.Timeout as exc:
                last_exc = exc
                logger.warning("Ollama timeout [%s] attempt %d/%d", context, attempt, self.max_retries)
            except requests.exceptions.ConnectionError as exc:
                last_exc = exc
                logger.warning("Ollama connection error [%s] attempt %d/%d: %s", context, attempt, self.max_retries, exc)
            except (requests.exceptions.HTTPError, ValueError) as exc:
                last_exc = exc
                logger.warning("Ollama error [%s] attempt %d/%d: %s", context, attempt, self.max_retries, exc)

            if attempt < self.max_retries:
                time.sleep(delay)
                delay = min(delay * 2, 30)   # exponential back-off, cap at 30 s

        raise RuntimeError(f"Ollama failed after {self.max_retries} attempts for {context}: {last_exc}") from last_exc

    # ------------------------------------------------------------------
    # Image preprocessing
    # ------------------------------------------------------------------

    def _preprocess_image(self, image_path: str) -> bytes:
        """Load and preprocess an image from disk."""
        if self._cv2 is not None:
            img = self._cv2.imread(image_path)
            if img is not None:
                return self._preprocess_array(img)

        if self._Image is not None:
            with open(image_path, "rb") as fh:
                raw = fh.read()
            pil = self._Image.open(io.BytesIO(raw))
            return self._preprocess_pil_image(pil)

        # No image library — return raw bytes unchanged
        with open(image_path, "rb") as fh:
            return fh.read()

    def _preprocess_pil_image(self, pil_image) -> bytes:
        """Preprocess a PIL image object."""
        if self._cv2 is not None and self._np is not None:
            import numpy as np  # already confirmed available
            arr = self._cv2.cvtColor(np.array(pil_image.convert("RGB")), self._cv2.COLOR_RGB2BGR)
            return self._preprocess_array(arr)

        # CV2 unavailable — just return PNG bytes without heavy processing
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        return buf.getvalue()

    def _preprocess_array(self, img) -> bytes:
        """
        Lightweight preprocessing pipeline.

        Changes vs original:
        - Only resize if width > 1600 px (was 1200 — a tighter crop lost detail)
        - Skip adaptive threshold when image is already high-contrast
          (avoids artefacts on clean pharmaceutical label scans)
        - Use INTER_AREA for downscaling (better than default INTER_LINEAR)
        """
        cv2, np = self._cv2, self._np

        # 1. Resize — only if truly large
        h, w = img.shape[:2]
        if w > 1600:
            scale = 1600 / w
            img = cv2.resize(img, (1600, int(h * scale)), interpolation=cv2.INTER_AREA)

        # 2. Grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # 3. Adaptive threshold — only if image is not already mostly B&W
        #    (standard deviation of pixel values < 60 → already low-contrast / greyscale scan)
        std_dev = float(np.std(gray))
        if std_dev > 40:
            processed = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2,
            )
        else:
            processed = gray   # skip threshold for already-clean images

        # 4. Encode to PNG bytes
        success, buf = cv2.imencode(".png", processed)
        if not success:
            raise RuntimeError("Failed to encode preprocessed image to PNG")
        return buf.tobytes()

    # ------------------------------------------------------------------
    # Tesseract fallback
    # ------------------------------------------------------------------

    def _tesseract_fallback(self, image_bytes: bytes, context: str = "") -> str:
        """Use Tesseract to extract text when Ollama is unavailable."""
        logger.info("Using Tesseract fallback for %s", context)
        if self._Image is None:
            raise RuntimeError("PIL is required for Tesseract fallback")
        pil = self._Image.open(io.BytesIO(image_bytes))
        text = self._tesseract.image_to_string(pil)
        return text.strip()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _find_poppler_path() -> Optional[str]:
        """Detect Poppler binary directory on Windows."""
        if os.name != "nt":
            return None
        candidates = [
            r"C:\Program Files\poppler\bin",
            r"C:\poppler\bin",
            r"C:\Program Files (x86)\poppler\bin",
        ]
        for path in candidates:
            if os.path.isdir(path):
                return path
        return None