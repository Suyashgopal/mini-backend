"""
validation_routes.py — Updated to use OpenRouter API with step-3.5-flash model

Changes:
  1. Replaced GroqValidationService with OpenRouterValidationService
  2. Updated error messages to reference OpenRouter instead of Groq
  3. Added support for follow-up validation questions
  4. Maintained same API interface for backward compatibility
"""

import logging

from flask import Blueprint, jsonify, request

from services.openrouter_validation_service import OpenRouterValidationService

logger = logging.getLogger(__name__)

validation_bp = Blueprint("validation", __name__, url_prefix="/api/validation")

# Module-level singleton — OpenRouterValidationService is stateless after __init__
try:
    _openrouter_service = OpenRouterValidationService()
except EnvironmentError as _env_err:
    # Server starts but endpoint will return 503 until key is configured
    _openrouter_service = None
    logger.error("OpenRouterValidationService disabled: %s", _env_err)


@validation_bp.route("/validate-text", methods=["POST"])
def validate_text():
    if _openrouter_service is None:
        return jsonify({
            "error": "OpenRouter validation is not configured. "
                     "Set the OPENROUTER_API_KEY environment variable and restart the server."
        }), 503

    # force=True accepts requests even without Content-Type: application/json
    data = request.get_json(force=True, silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    extracted_text = data.get("text", "").strip()
    if not extracted_text:
        return jsonify({"error": "Field 'text' is required and must not be empty"}), 400

    # Check for optional follow-up question
    followup_question = data.get("followup_question", "").strip()

    try:
        if followup_question:
            result = _openrouter_service.validate_with_followup(extracted_text, followup_question)
        else:
            result = _openrouter_service.validate_text(extracted_text)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        logger.exception("OpenRouter validation failed")
        return jsonify({"error": str(exc)}), 502   # bad gateway — upstream API issue
    except Exception as exc:
        logger.exception("Unexpected error in validate_text")
        return jsonify({"error": "Internal server error"}), 500


@validation_bp.route("/test-drug-detection", methods=["POST"])
def test_drug_detection():
    """
    Test endpoint for debugging drug name detection.
    
    Request body:
    {
        "text": "Sample pharmaceutical label text"
    }
    """
    if _openrouter_service is None:
        return jsonify({
            "error": "OpenRouter validation is not configured. "
                     "Set the OPENROUTER_API_KEY environment variable and restart the server."
        }), 503

    data = request.get_json(force=True, silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    extracted_text = data.get("text", "").strip()
    if not extracted_text:
        return jsonify({"error": "Field 'text' is required and must not be empty"}), 400

    try:
        # Get validation result
        result = _openrouter_service.validate_text(extracted_text)
        
        # Add fallback drug name detection for comparison
        fallback_drug_name = _openrouter_service._extract_drug_name_fallback(extracted_text)
        
        # Return both results for debugging
        return jsonify({
            "success": True,
            "openrouter_result": result,
            "fallback_drug_name": fallback_drug_name,
            "input_text": extracted_text
        }), 200
        
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        logger.exception("OpenRouter test validation failed")
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        logger.exception("Unexpected error in test_drug_detection")
        return jsonify({"error": "Internal server error"}), 500
    """
    Enhanced validation endpoint that accepts follow-up questions for deeper analysis.
    
    Request body:
    {
        "text": "OCR extracted text",
        "question": "Are you sure about the expiry date? Check again."
    }
    """
    if _openrouter_service is None:
        return jsonify({
            "error": "OpenRouter validation is not configured. "
                     "Set the OPENROUTER_API_KEY environment variable and restart the server."
        }), 503

    data = request.get_json(force=True, silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    extracted_text = data.get("text", "").strip()
    question = data.get("question", "").strip()
    
    if not extracted_text:
        return jsonify({"error": "Field 'text' is required and must not be empty"}), 400
    
    if not question:
        return jsonify({"error": "Field 'question' is required for reasoning endpoint"}), 400

    try:
        result = _openrouter_service.validate_with_followup(extracted_text, question)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        logger.exception("OpenRouter reasoning validation failed")
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        logger.exception("Unexpected error in validate_with_reasoning")
        return jsonify({"error": "Internal server error"}), 500


@validation_bp.route("/validate-with-reasoning", methods=["POST"])
def validate_with_reasoning():
    """
    Enhanced validation endpoint that accepts follow-up questions for deeper analysis.
    
    Request body:
    {
        "text": "OCR extracted text",
        "question": "Are you sure about the expiry date? Check again."
    }
    """
    if _openrouter_service is None:
        return jsonify({
            "error": "OpenRouter validation is not configured. "
                     "Set the OPENROUTER_API_KEY environment variable and restart the server."
        }), 503

    data = request.get_json(force=True, silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    extracted_text = data.get("text", "").strip()
    question = data.get("question", "").strip()
    
    if not extracted_text:
        return jsonify({"error": "Field 'text' is required and must not be empty"}), 400
    
    if not question:
        return jsonify({"error": "Field 'question' is required for reasoning endpoint"}), 400

    try:
        result = _openrouter_service.validate_with_followup(extracted_text, question)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        logger.exception("OpenRouter reasoning validation failed")
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        logger.exception("Unexpected error in validate_with_reasoning")
        return jsonify({"error": "Internal server error"}), 500