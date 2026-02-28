"""
comparison_routes.py — Fixed & hardened.

Bugs fixed:
  1. comparison used ocr_result.translated_text which can be NULL in the DB →
     now falls back to extracted_text when translated_text is absent, with a
     warning logged so the caller knows which field was used.
  2. final_decision duplicated the PASS/FAIL logic from ComparisonService
     inconsistently (>= 95 check on percentage vs > 0.95 on ratio internally) →
     now reads directly from the stored comparison.status field.
  3. MedicalValidationService() was re-instantiated on every request →
     module-level singleton used instead.
"""

import json
import logging

from flask import Blueprint, jsonify

from config.database import db
from models.database import ComparisonResult, OCRResult, VerifiedControl
from services.comparison_service import ComparisonService
from services.medical_validation_service import MedicalValidationService

logger = logging.getLogger(__name__)

bp = Blueprint("comparison", __name__, url_prefix="/api/comparison")

# Module-level singleton — MedicalValidationService is stateless and cheap to share
_medical_validator = MedicalValidationService()


# ---------------------------------------------------------------------------
# Compare production label vs verified control
# ---------------------------------------------------------------------------

@bp.route("/run/<int:control_id>/<int:ocr_result_id>", methods=["POST"])
def run_comparison(control_id, ocr_result_id):
    try:
        control    = VerifiedControl.query.get_or_404(control_id)
        ocr_result = OCRResult.query.get_or_404(ocr_result_id)

        # --- FIX: fall back to extracted_text when translated_text is absent ---
        production_text = ocr_result.translated_text or ocr_result.extracted_text
        if not ocr_result.translated_text:
            logger.warning(
                "OCRResult %d has no translated_text — using extracted_text for comparison.",
                ocr_result_id,
            )

        result = ComparisonService.compare_texts(
            control.verified_text,
            production_text,
        )

        comparison = ComparisonResult(
            verified_control_id=control.id,
            ocr_result_id=ocr_result.id,
            match_percentage=result["match_percentage"],
            deviations=json.dumps(result["deviations"]),
            status=result["status"],
        )
        db.session.add(comparison)
        db.session.commit()

        # --- Medical validation on the raw extracted text ---
        validation_result = _medical_validator.validate_text(ocr_result.extracted_text or "")

        # --- FIX: derive final_decision from stored status, not a re-computed threshold ---
        # comparison.status is "PASS"/"FAIL" set by ComparisonService at >= 95% word similarity.
        # A label is VALID only when both text similarity AND structural authenticity pass.
        auth_passes   = validation_result["is_structurally_authentic"]
        sim_passes    = comparison.status == "PASS"
        final_decision = "VALID" if (sim_passes and auth_passes) else "SUSPICIOUS"

        response_data = comparison.to_dict()
        response_data["medical_validation"] = validation_result
        response_data["final_decision"]     = final_decision

        return jsonify({"success": True, "data": response_data}), 200

    except Exception as exc:
        db.session.rollback()
        logger.exception("Comparison failed for control=%d ocr=%d", control_id, ocr_result_id)
        return jsonify({"success": False, "error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Retrieve a stored comparison result
# ---------------------------------------------------------------------------

@bp.route("/result/<int:comparison_id>", methods=["GET"])
def get_comparison_result(comparison_id):
    try:
        comparison = ComparisonResult.query.get_or_404(comparison_id)
        return jsonify({"success": True, "data": comparison.to_dict()}), 200
    except Exception as exc:
        logger.exception("Failed to retrieve comparison %d", comparison_id)
        return jsonify({"success": False, "error": str(exc)}), 500