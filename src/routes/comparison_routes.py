"""
comparison_routes.py — with Conditional Groq Validation
========================================================

FULL PIPELINE (what runs on every POST /run):
  1. ComparisonService      → text similarity score
  2. MedicalValidationService → regex structural check
  3. AuditService.generate_content_hash() → content fingerprint
  4. DB lookup              → has this content been seen before?
  5a. YES → load cached groq_validation from previous record
  5b. NO  → call GroqValidationService.validate_text() live
  6. AuditService.generate_audit_hash() → tamper-detection fingerprint
  7. Save everything to DB
  8. Return full result

ENDPOINTS:
  POST /api/comparison/run/<control_id>/<ocr_result_id>
  GET  /api/comparison/result/<id>
  GET  /api/comparison/verify/<id>
  GET  /api/comparison/history/<control_id>
  GET  /api/comparison/duplicates/<content_hash>
"""

import json
import logging

from flask import Blueprint, jsonify, request

from configration.database import db
from models.database import ComparisonResult, OCRResult, VerifiedControl
from services.audit_service import AuditService
from services.comparison_service import ComparisonService
from services.groq_validation_service import GroqValidationService
from services.medical_validation_service import MedicalValidationService

logger = logging.getLogger(__name__)

bp = Blueprint("comparison", __name__, url_prefix="/api/comparison")

# ── Module-level singletons ───────────────────────────────────────────
# Instantiated once at startup, reused across all requests.
# MedicalValidationService is pure regex — always available.
# GroqValidationService reads GROQ_API_KEY from env — may be None if key missing.

_medical_validator = MedicalValidationService()

try:
    _groq_service = GroqValidationService()
    logger.info("GroqValidationService ready — conditional validation active.")
except Exception as exc:
    _groq_service = None
    logger.warning(
        "GroqValidationService unavailable (%s). "
        "Comparison will run without Groq validation.", exc
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/comparison/run/<control_id>/<ocr_result_id>
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/run/<int:control_id>/<int:ocr_result_id>", methods=["POST"])
def run_comparison(control_id, ocr_result_id):
    """
    Full comparison pipeline with conditional Groq validation.

    Groq API is called ONLY for new label content.
    If the same content was submitted before and already has a
    groq_validation stored, that cached result is reused.
    """
    try:
        control    = VerifiedControl.query.get_or_404(control_id)
        ocr_result = OCRResult.query.get_or_404(ocr_result_id)

        # Fall back to extracted_text if translated_text is absent
        production_text = ocr_result.translated_text or ocr_result.extracted_text
        if not ocr_result.translated_text:
            logger.warning(
                "OCRResult %d has no translated_text — using extracted_text.",
                ocr_result_id,
            )

        # ── 1. Text similarity comparison ─────────────────────────────────
        result = ComparisonService.compare_texts(
            control.verified_text,
            production_text,
        )

        # ── 2. Medical structural validation (regex, always runs) ──────────
        medical_result = _medical_validator.validate_text(
            ocr_result.extracted_text or ""
        )

        # ── 3. Final decision ──────────────────────────────────────────────
        final_decision = (
            "VALID"
            if result["status"] == "PASS"
            and medical_result["is_structurally_authentic"]
            else "SUSPICIOUS"
        )

        # ── 4. Submitter IP ────────────────────────────────────────────────
        submitter_ip = (
            request.headers.get("X-Forwarded-For", request.remote_addr)
            or "unknown"
        ).split(",")[0].strip()

        # ── 5. Content hash (no timestamp/IP — pure label content) ─────────
        content_hash = AuditService.generate_content_hash(
            extracted_text   = ocr_result.extracted_text or "",
            match_percentage = result["match_percentage"],
            status           = result["status"],
        )

        # ── 6. Conditional Groq validation ────────────────────────────────
        groq_result = None
        groq_source = "unavailable"

        if _groq_service is not None:
            # Look for a previous record with the same content that
            # already has a groq_validation stored
            previous = (
                ComparisonResult.query
                .filter_by(content_hash=content_hash)
                .filter(ComparisonResult.groq_validation.isnot(None))
                .order_by(ComparisonResult.compared_at.desc())
                .first()
            )

            if previous:
                # Cache hit — reuse stored Groq result, skip API call
                groq_result = json.loads(previous.groq_validation)
                groq_source = "cached"
                logger.info(
                    "Groq cache hit for content_hash=%s... "
                    "(reusing result from comparison id=%d)",
                    content_hash[:12], previous.id,
                )
            else:
                # Cache miss — new content, call Groq API
                try:
                    groq_result = _groq_service.validate_text(
                        ocr_result.extracted_text or ""
                    )
                    groq_source = "fresh"
                    logger.info(
                        "Groq fresh validation complete | "
                        "risk=%s confidence=%s",
                        groq_result.get("risk_level"),
                        groq_result.get("confidence_score"),
                    )
                except Exception as groq_exc:
                    # Groq failure is non-fatal — comparison still saves
                    groq_result = None
                    groq_source = "error"
                    logger.warning("Groq validation failed: %s", groq_exc)

        # ── 7. Save comparison result ──────────────────────────────────────
        comparison = ComparisonResult(
            verified_control_id = control.id,
            ocr_result_id       = ocr_result.id,
            match_percentage    = result["match_percentage"],
            deviations          = json.dumps(result["deviations"]),
            status              = result["status"],
            submitter_ip        = submitter_ip,
            final_decision      = final_decision,
            content_hash        = content_hash,
            groq_validation     = json.dumps(groq_result) if groq_result else None,
        )
        db.session.add(comparison)

        # flush() to get the real compared_at timestamp before hashing
        db.session.flush()

        # ── 8. Audit hash (timestamp + IP included — unique per submission) ─
        audit_hash = AuditService.generate_audit_hash(
            extracted_text     = ocr_result.extracted_text or "",
            match_percentage   = result["match_percentage"],
            status             = result["status"],
            final_decision     = final_decision,
            authenticity_score = medical_result["authenticity_score"],
            compared_at        = comparison.compared_at.isoformat(),
            submitter_ip       = submitter_ip,
        )
        comparison.audit_hash = audit_hash

        # ── 9. Commit ──────────────────────────────────────────────────────
        db.session.commit()

        logger.info(
            "Comparison %d saved | status=%s | decision=%s | "
            "groq=%s | audit=%s... | content=%s...",
            comparison.id, result["status"], final_decision,
            groq_source, audit_hash[:12], content_hash[:12],
        )

        # ── 10. Build response ─────────────────────────────────────────────
        response_data = comparison.to_dict()
        response_data["medical_validation"] = medical_result
        response_data["groq_validation"]    = groq_result
        response_data["groq_source"]        = groq_source
        # groq_source tells frontend: "fresh" | "cached" | "unavailable" | "error"

        return jsonify({"success": True, "data": response_data}), 200

    except Exception as exc:
        db.session.rollback()
        logger.exception("run_comparison failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/comparison/result/<id>  — unchanged
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/result/<int:comparison_id>", methods=["GET"])
def get_comparison_result(comparison_id):
    try:
        comparison = ComparisonResult.query.get_or_404(comparison_id)
        return jsonify({"success": True, "data": comparison.to_dict()}), 200
    except Exception as exc:
        logger.exception("get_comparison_result failed for id %d", comparison_id)
        return jsonify({"success": False, "error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/comparison/verify/<id>  — unchanged
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/verify/<int:comparison_id>", methods=["GET"])
def verify_comparison(comparison_id):
    try:
        comparison   = ComparisonResult.query.get_or_404(comparison_id)
        record       = comparison.to_dict()
        verification = AuditService.verify_record(record, comparison.audit_hash)
        return jsonify({
            "success":       True,
            "comparison_id": comparison_id,
            "verification":  verification,
        }), 200
    except Exception as exc:
        logger.exception("verify_comparison failed for id %d", comparison_id)
        return jsonify({"success": False, "error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/comparison/history/<control_id>  — unchanged
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/history/<int:control_id>", methods=["GET"])
def comparison_history(control_id):
    try:
        VerifiedControl.query.get_or_404(control_id)

        comparisons = (
            ComparisonResult.query
            .filter_by(verified_control_id=control_id)
            .order_by(ComparisonResult.compared_at.desc())
            .all()
        )

        history = []
        for c in comparisons:
            entry        = c.to_dict()
            verification = AuditService.verify_record(entry, c.audit_hash)
            entry["tampered"]    = verification["tampered"]
            entry["verified_at"] = verification["verified_at"]
            history.append(entry)

        total    = len(history)
        passed   = sum(1 for h in history if h.get("status") == "PASS")
        tampered = sum(1 for h in history if h.get("tampered") is True)

        return jsonify({
            "success":    True,
            "control_id": control_id,
            "summary": {
                "total":          total,
                "passed":         passed,
                "failed":         total - passed,
                "tampered_count": tampered,
            },
            "history": history,
        }), 200

    except Exception as exc:
        logger.exception("comparison_history failed for control %d", control_id)
        return jsonify({"success": False, "error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/comparison/duplicates/<content_hash>  — unchanged
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/duplicates/<string:content_hash>", methods=["GET"])
def find_duplicates(content_hash):
    try:
        if len(content_hash) != 64:
            return jsonify({
                "success": False,
                "error":   "content_hash must be a 64-character SHA-256 hex string",
            }), 400

        matches = (
            ComparisonResult.query
            .filter_by(content_hash=content_hash)
            .order_by(ComparisonResult.compared_at.asc())
            .all()
        )

        results    = [c.to_dict() for c in matches]
        is_dup     = len(results) > 1
        first_seen = results[0]["compared_at"]  if results else None
        last_seen  = results[-1]["compared_at"] if results else None

        return jsonify({
            "success":      True,
            "content_hash": content_hash,
            "count":        len(results),
            "is_duplicate": is_dup,
            "first_seen":   first_seen,
            "last_seen":    last_seen,
            "submissions":  results,
        }), 200

    except Exception as exc:
        logger.exception("find_duplicates failed for hash %s", content_hash[:12])
        return jsonify({"success": False, "error": str(exc)}), 500
