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

from flask import Blueprint, jsonify, request

from configration.database import db
from models.database import ComparisonResult, OCRResult, VerifiedControl
from services.comparison_service import ComparisonService
from services.medical_validation_service import MedicalValidationService
from services.audit_service import AuditService

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

        # --- Medical validation on the raw extracted text ---
        validation_result = _medical_validator.validate_text(ocr_result.extracted_text or "")

        # --- FIX: derive final_decision from stored status, not a re-computed threshold ---
        # comparison.status is "PASS"/"FAIL" set by ComparisonService at >= 95% word similarity.
        # A label is VALID only when both text similarity AND structural authenticity pass.
        auth_passes   = validation_result["is_structurally_authentic"]
        sim_passes    = result["status"] == "PASS"
        final_decision = "VALID" if (sim_passes and auth_passes) else "SUSPICIOUS"
        
        # Get submitter IP address
        submitter_ip = request.remote_addr or "unknown"
        
        # Create comparison record
        comparison = ComparisonResult(
            verified_control_id=control.id,
            ocr_result_id=ocr_result.id,
            match_percentage=result["match_percentage"],
            deviations=json.dumps(result["deviations"]),
            status=result["status"],
            final_decision=final_decision,
            authenticity_score=validation_result["authenticity_score"],
            submitter_ip=submitter_ip,
        )
        
        # Generate audit hashes BEFORE committing
        compared_at_iso = comparison.compared_at.isoformat()
        
        # Audit hash: includes timestamp and IP for tamper detection
        comparison.audit_hash = AuditService.generate_audit_hash(
            extracted_text=ocr_result.extracted_text or "",
            match_percentage=comparison.match_percentage,
            status=comparison.status,
            final_decision=final_decision,
            authenticity_score=validation_result["authenticity_score"],
            compared_at=compared_at_iso,
            submitter_ip=submitter_ip,
        )
        
        # Content hash: no timestamp/IP for duplicate detection
        comparison.content_hash = AuditService.generate_content_hash(
            extracted_text=ocr_result.extracted_text or "",
            match_percentage=comparison.match_percentage,
            status=comparison.status,
        )
        
        db.session.add(comparison)
        db.session.commit()

        response_data = comparison.to_dict()
        response_data["medical_validation"] = validation_result

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


# ---------------------------------------------------------------------------
# Verify audit hash (tamper detection)
# ---------------------------------------------------------------------------

@bp.route("/verify/<int:comparison_id>", methods=["GET"])
def verify_comparison(comparison_id):
    """
    Verify if a comparison result has been tampered with.
    
    Returns:
        - tampered: True/False/None
        - reason: Explanation of verification result
        - verified_at: Timestamp of verification
    """
    try:
        comparison = ComparisonResult.query.get_or_404(comparison_id)
        
        # Get the OCR result to access extracted_text
        ocr_result = OCRResult.query.get_or_404(comparison.ocr_result_id)
        
        # Build record dict for verification
        record = {
            "extracted_text": ocr_result.extracted_text or "",
            "match_percentage": comparison.match_percentage,
            "status": comparison.status,
            "final_decision": comparison.final_decision,
            "authenticity_score": comparison.authenticity_score,
            "compared_at": comparison.compared_at.isoformat(),
            "submitter_ip": comparison.submitter_ip or "unknown",
        }
        
        # Verify using audit service
        verification_result = AuditService.verify_record(
            record,
            comparison.audit_hash
        )
        
        return jsonify({
            "success": True,
            "comparison_id": comparison_id,
            "verification": verification_result
        }), 200
        
    except Exception as exc:
        logger.exception("Failed to verify comparison %d", comparison_id)
        return jsonify({"success": False, "error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Find duplicate submissions (using content_hash)
# ---------------------------------------------------------------------------

@bp.route("/duplicates/<int:comparison_id>", methods=["GET"])
def find_duplicates(comparison_id):
    """
    Find all comparison results with the same content (duplicate submissions).
    
    Uses content_hash which is based only on label content, not timestamp or IP.
    """
    try:
        comparison = ComparisonResult.query.get_or_404(comparison_id)
        
        if not comparison.content_hash:
            return jsonify({
                "success": False,
                "error": "This comparison has no content_hash (created before audit system)"
            }), 400
        
        # Find all comparisons with same content_hash
        duplicates = ComparisonResult.query.filter(
            ComparisonResult.content_hash == comparison.content_hash,
            ComparisonResult.id != comparison_id  # Exclude the current one
        ).all()
        
        return jsonify({
            "success": True,
            "comparison_id": comparison_id,
            "content_hash": comparison.content_hash,
            "duplicate_count": len(duplicates),
            "duplicates": [
                {
                    "id": dup.id,
                    "compared_at": dup.compared_at.isoformat(),
                    "submitter_ip": dup.submitter_ip,
                    "status": dup.status,
                    "final_decision": dup.final_decision,
                }
                for dup in duplicates
            ]
        }), 200
        
    except Exception as exc:
        logger.exception("Failed to find duplicates for comparison %d", comparison_id)
        return jsonify({"success": False, "error": str(exc)}), 500