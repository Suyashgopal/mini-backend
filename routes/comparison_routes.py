from flask import Blueprint, jsonify
from database import db
from models.database import (
    VerifiedControl,
    OCRResult,
    ComparisonResult
)
from services.comparison_service import ComparisonService
import json

bp = Blueprint("comparison", __name__, url_prefix="/api/comparison")


# ===============================
# Compare Production vs Verified
# ===============================
@bp.route("/run/<int:control_id>/<int:ocr_result_id>", methods=["POST"])
def run_comparison(control_id, ocr_result_id):
    try:
        control = VerifiedControl.query.get_or_404(control_id)
        ocr_result = OCRResult.query.get_or_404(ocr_result_id)

        result = ComparisonService.compare_texts(
            control.verified_text,
            ocr_result.translated_text
        )

        comparison = ComparisonResult(
            verified_control_id=control.id,
            ocr_result_id=ocr_result.id,
            match_percentage=result["match_percentage"],
            deviations=json.dumps(result["deviations"]),
            status=result["status"]
        )

        db.session.add(comparison)
        db.session.commit()

        return jsonify({
            "success": True,
            "data": comparison.to_dict()
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===============================
# Get Comparison Result
# ===============================
@bp.route("/result/<int:comparison_id>", methods=["GET"])
def get_comparison_result(comparison_id):
    try:
        comparison = ComparisonResult.query.get_or_404(comparison_id)

        return jsonify({
            "success": True,
            "data": comparison.to_dict()
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
