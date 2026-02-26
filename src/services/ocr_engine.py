"""
ocr_engine.py

Unified OCR engine: tries OCR.space first, automatically falls back
to Ollama if OCR.space is unavailable or fails.

Usage (in routes or anywhere else):
    from services.ocr_engine import ocr_engine
    result = ocr_engine.process_image(tmp_path)
    result = ocr_engine.process_pdf(tmp_path)

Both methods always return the same dict shape as before.
"""

import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OCREngine:
    """
    Facade that routes OCR requests to OCR.space (primary) or
    Ollama (fallback), decided at startup based on env vars.
    """

    def __init__(self):
        self._ocrspace: Optional[object] = None
        self._ollama: Optional[object] = None
        self._primary: str = "none"
        self._init_engines()

    def _init_engines(self):
        # ── Try OCR.space first ──────────────────────────────────────────
        ocrspace_key = os.getenv("OCRSPACE_API_KEY", "").strip()
        logger.info("OCREngine: OCRSPACE_API_KEY found: %s", bool(ocrspace_key))
        if ocrspace_key:
            try:
                from services.ocrspace_ocr_service import OCRSpaceOCRService
                logger.info("OCREngine: Importing OCRSpaceOCRService successful")
                self._ocrspace = OCRSpaceOCRService()
                self._primary = "ocr.space"
                logger.info("OCREngine: PRIMARY = OCR.space")
            except Exception as exc:
                logger.warning("OCREngine: OCR.space init failed (%s) — will use Ollama only.", exc)
        else:
            logger.info("OCREngine: OCRSPACE_API_KEY not set — OCR.space disabled.")

        # ── Always initialise Ollama as backup ────────────────────────
        try:
            from services.ollama_ocr_service import OllamaOCRService
            self._ollama = OllamaOCRService(
                ollama_endpoint=os.getenv("OLLAMA_ENDPOINT", "http://127.0.0.1:11434"),
                model_name=os.getenv("OLLAMA_MODEL", "glm-ocr:latest"),
                timeout=int(os.getenv("OLLAMA_TIMEOUT", "120")),
                max_retries=int(os.getenv("OLLAMA_RETRIES", "3")),
            )
            if self._primary == "none":
                self._primary = "ollama"
            logger.info("OCREngine: FALLBACK = Ollama (%s)", os.getenv("OLLAMA_ENDPOINT", "http://127.0.0.1:11434"))
        except Exception as exc:
            logger.warning("OCREngine: Ollama init failed (%s).", exc)

        if self._primary == "none":
            logger.error(
                "OCREngine: NO OCR engine available! "
                "Set OCRSPACE_API_KEY or ensure Ollama is running."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_image(self, image_path: str) -> Dict[str, Any]:
        return self._run("process_image", image_path)

    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        return self._run("process_pdf", pdf_path)

    @property
    def active_engine(self) -> str:
        """Returns 'ocr.space', 'ollama', or 'none' — useful for health endpoint."""
        return self._primary

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(self, method: str, file_path: str) -> Dict[str, Any]:
        """Try OCR.space → if it raises, log and try Ollama → if both fail, raise."""
        errors = []

        if self._ocrspace is not None:
            try:
                result = getattr(self._ocrspace, method)(file_path)
                result["engine_used"] = "ocr.space"
                return result
            except Exception as exc:
                errors.append(f"OCR.space: {exc}")
                logger.warning(
                    "OCREngine: OCR.space failed for %s (%s) — falling back to Ollama.",
                    file_path, exc,
                )

        if self._ollama is not None:
            try:
                result = getattr(self._ollama, method)(file_path)
                result["engine_used"] = "ollama"
                return result
            except Exception as exc:
                errors.append(f"Ollama: {exc}")
                logger.error("OCREngine: Ollama also failed for %s (%s).", file_path, exc)

        raise RuntimeError(
            f"All OCR engines failed for {file_path}. "
            f"Errors: {' | '.join(errors)}"
        )


# Module-level singleton — import and use this everywhere
ocr_engine = OCREngine()
