"""
validation_routes.py — Fixed & hardened.

Bugs fixed:
  1. GroqValidationService() instantiated on every request — wastes startup cost
     and re-reads/validates env var on each call → module-level singleton.
  2. request.json crashes with 415 if Content-Type header is missing →
     replaced with request.get_json(force=True, silent=True) which is tolerant.
  3. No logging of validation errors → added logger.exception().
"""

import logging

from flask import Blueprint, jsonify, request

from services.groq_validation_service import GroqValidationService

logger = logging.getLogger(__name__)

validation_bp = Blueprint("validation", __name__, url_prefix="/api/validation")

# Module-level singleton — GroqValidationService is stateless after __init__
try:
    _groq_service = GroqValidationService()
except EnvironmentError as _env_err:
    # Server starts but endpoint will return 503 until key is configured
    _groq_service = None
    logger.error("GroqValidationService disabled: %s", _env_err)


@validation_bp.route("/validate-text", methods=["POST"])
def validate_text():
    if _groq_service is None:
        return jsonify({
            "error": "Groq validation is not configured. "
                     "Set the GROQ_API_KEY environment variable and restart the server."
        }), 503

    # force=True accepts requests even without Content-Type: application/json
    data = request.get_json(force=True, silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    extracted_text = data.get("text", "").strip()
    if not extracted_text:
        return jsonify({"error": "Field 'text' is required and must not be empty"}), 400

    try:
        result = _groq_service.validate_text(extracted_text)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        logger.exception("Groq validation failed")
        return jsonify({"error": str(exc)}), 502   # bad gateway — upstream API issue
    except Exception as exc:
        logger.exception("Unexpected error in validate_text")
        return jsonify({"error": "Internal server error"}), 500