from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile
from services.ollama_ocr_service import OllamaOCRService

bp = Blueprint("ocr", __name__, url_prefix="/api/ocr")

# Initialize Ollama OCR service
ollama_service = OllamaOCRService(
    ollama_endpoint=os.getenv("OLLAMA_ENDPOINT", "http://127.0.0.1:11434"),
    model_name=os.getenv("OLLAMA_MODEL", "glm-ocr:latest"),
    timeout=int(os.getenv("OLLAMA_TIMEOUT", 600)),   # CPU-friendly timeout
    max_retries=int(os.getenv("OLLAMA_RETRIES", 3))
)

# -------------------------------
# Image OCR Endpoint
# -------------------------------
@bp.route("/image", methods=["POST"])
def ocr_image():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    _, ext = os.path.splitext(filename)

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        file.save(tmp_file.name)
        tmp_path = tmp_file.name

    try:
        result = ollama_service.process_image(tmp_path)
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

# -------------------------------
# PDF OCR Endpoint
# -------------------------------
@bp.route("/pdf", methods=["POST"])
def ocr_pdf():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No selected file"}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "File must be a PDF"}), 400

    filename = secure_filename(file.filename)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        file.save(tmp_file.name)
        tmp_path = tmp_file.name

    try:
        result = ollama_service.process_pdf(tmp_path)
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass