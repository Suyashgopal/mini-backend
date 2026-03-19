"""
ocr_routes.py — Simplified to use only Ollama OCR service.

Changes:
  1. Removed OCR engine abstraction layer
  2. Removed OCR space and Tesseract references
  3. Direct integration with Ollama OCR service only
  4. Simplified error handling for single OCR provider
"""

import logging
import os
import tempfile

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from services.ollama_ocr_service import OllamaOCRService

logger = logging.getLogger(__name__)

bp = Blueprint("ocr", __name__, url_prefix="/api/ocr")

# Allowed image extensions — PDFs are handled by /pdf endpoint only
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp"}

# ---------------------------------------------------------------------------
# Lazy service singleton — reads env vars at first request, not at import time
_ollama_service = None

def get_ollama_service():
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaOCRService()
    return _ollama_service

def _extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lstrip(".").lower()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@bp.route("/image", methods=["POST"])
def ocr_image():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part in request"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    ext = _extension(filename)

    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({
            "success": False,
            "error": f"Unsupported file type '.{ext}'. "
                     f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}",
        }), 400

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        ollama_service = get_ollama_service()
        result = ollama_service.process_image(tmp_path)
        return jsonify({"success": True, "data": result}), 200

    except Exception as exc:
        logger.exception("Ollama OCR failed for file %s", filename)
        return jsonify({"success": False, "error": str(exc)}), 500

    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass   # Already deleted or never created — safe to ignore


@bp.route("/pdf", methods=["POST"])
def ocr_pdf():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part in request"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    if _extension(filename) != "pdf":
        return jsonify({"success": False, "error": "File must be a PDF"}), 400

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        ollama_service = get_ollama_service()
        result = ollama_service.process_pdf(tmp_path)
        return jsonify({"success": True, "data": result}), 200

    except Exception as exc:
        logger.exception("Ollama PDF OCR failed for file %s", filename)
        return jsonify({"success": False, "error": str(exc)}), 500

    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass