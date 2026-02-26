from flask import Blueprint, request, jsonify
from services.groq_validation_service import GroqValidationService

validation_bp = Blueprint("validation", __name__, url_prefix="/api/validation")

@validation_bp.route("/validate-text", methods=["POST"])
def validate_text():

    data = request.json
    extracted_text = data.get("text")

    if not extracted_text:
        return jsonify({"error": "No text provided"}), 400

    service = GroqValidationService()
    result = service.validate_text(extracted_text)

    return jsonify(result)
