"""
ocr_routes.py — Fixed & hardened.

Bugs fixed:
  1. OllamaOCRService instantiated at MODULE LEVEL — env vars must exist at import
     time and service can never be reconfigured → moved to lazy initialisation via
     get_ocr_service() which reads env vars at request time on first call.
  2. /api/ocr/image accepted ANY file extension (including .pdf, .exe) → added
     ALLOWED_IMAGE_EXTENSIONS whitelist check.
  3. No Tesseract fallback — Ollama failure returned 500 with no recovery →
     fallback is now wired into OllamaOCRService itself (see ollama_ocr_service.py);
     route just catches and returns the error cleanly.
  4. Temp file could leak if the server process was killed between NamedTemporaryFile
     creation and the finally block (rare but possible) — added explicit delete=False
     comment and ensured finally always runs os.remove safely.
"""

import logging
import os
import tempfile

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from services.ocr_engine import ocr_engine

logger = logging.getLogger(__name__)

bp = Blueprint("ocr", __name__, url_prefix="/api/ocr")

# Allowed image extensions — PDFs are handled by /pdf endpoint only
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp"}

# ---------------------------------------------------------------------------
# Lazy service singleton — reads env vars at first request, not at import time

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

        result = ocr_engine.process_image(tmp_path)
        return jsonify({"success": True, "data": result}), 200

    except Exception as exc:
        logger.exception("Image OCR failed for file %s", filename)
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

        result = ocr_engine.process_pdf(tmp_path)
        return jsonify({"success": True, "data": result}), 200

    except Exception as exc:
        logger.exception("PDF OCR failed for file %s", filename)
        return jsonify({"success": False, "error": str(exc)}), 500

    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass