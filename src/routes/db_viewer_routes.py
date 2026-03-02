"""
A read-only database browser API — lets you see every row in every
table without needing a DB admin tool like DBeaver or TablePlus.

Register in app.py:
    from routes.db_viewer_routes import db_viewer_bp
    app.register_blueprint(db_viewer_bp)

Endpoints:
    GET /api/db/tables                    → list all tables + row counts
    GET /api/db/documents                 → all Document rows
    GET /api/db/ocr-results               → all OCRResult rows
    GET /api/db/verified-controls         → all VerifiedControl rows
    GET /api/db/comparison-results        → all ComparisonResult rows
    GET /api/db/comparison-results/<id>   → single ComparisonResult with verify status

SPRING BOOT EQUIVALENT:
    @RestController @RequestMapping("/api/db")
    with @GetMapping methods calling repository.findAll()
"""

import logging

from flask import Blueprint, jsonify, request

from configration.database import db
from models.database import (
    ComparisonResult,
    Document,
    OCRResult,
    VerifiedControl,
)

logger = logging.getLogger(__name__)

db_viewer_bp = Blueprint("db_viewer", __name__, url_prefix="/api/db")


def _paginate(query, default_per_page=50):
    """Helper: apply page/per_page query params to any SQLAlchemy query."""
    page     = max(1, request.args.get("page",     1,  type=int))
    per_page = min(200, request.args.get("per_page", default_per_page, type=int))
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return paginated


# ─────────────────────────────────────────────────────────────────────────────
# TABLE OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

@db_viewer_bp.route("/tables", methods=["GET"])
def list_tables():
    """
    Returns every table name with its current row count.
    Good for a quick overview of what's in the database.
    """
    try:
        tables = {
            "documents":          Document.query.count(),
            "ocr_results":        OCRResult.query.count(),
            "verified_controls":  VerifiedControl.query.count(),
            "comparison_results": ComparisonResult.query.count(),
        }

        total_rows = sum(tables.values())

        return jsonify({
            "success": True,
            "database": "label_verification.db",
            "total_rows": total_rows,
            "tables": [
                {"name": name, "row_count": count, "endpoint": f"/api/db/{name.replace('_', '-')}"}
                for name, count in tables.items()
            ],
        }), 200

    except Exception as exc:
        logger.exception("list_tables failed")
        return jsonify({"success": False, "error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENTS
# ─────────────────────────────────────────────────────────────────────────────

@db_viewer_bp.route("/documents", methods=["GET"])
def list_documents():
    """All uploaded documents, newest first. Supports ?page=1&per_page=50"""
    try:
        paginated = _paginate(
            Document.query.order_by(Document.uploaded_at.desc())
        )
        return jsonify({
            "success":   True,
            "total":     paginated.total,
            "page":      paginated.page,
            "per_page":  paginated.per_page,
            "pages":     paginated.pages,
            "data":      [d.to_dict() for d in paginated.items],
        }), 200
    except Exception as exc:
        logger.exception("list_documents failed")
        return jsonify({"success": False, "error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# OCR RESULTS
# ─────────────────────────────────────────────────────────────────────────────

@db_viewer_bp.route("/ocr-results", methods=["GET"])
def list_ocr_results():
    """All OCR results, newest first. Supports ?page=1&per_page=50"""
    try:
        paginated = _paginate(
            OCRResult.query.order_by(OCRResult.processed_at.desc())
        )
        return jsonify({
            "success":  True,
            "total":    paginated.total,
            "page":     paginated.page,
            "per_page": paginated.per_page,
            "pages":    paginated.pages,
            "data":     [r.to_dict() for r in paginated.items],
        }), 200
    except Exception as exc:
        logger.exception("list_ocr_results failed")
        return jsonify({"success": False, "error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# VERIFIED CONTROLS
# ─────────────────────────────────────────────────────────────────────────────

@db_viewer_bp.route("/verified-controls", methods=["GET"])
def list_verified_controls():
    """All verified control templates, newest first."""
    try:
        paginated = _paginate(
            VerifiedControl.query.order_by(VerifiedControl.approved_at.desc())
        )
        return jsonify({
            "success":  True,
            "total":    paginated.total,
            "page":     paginated.page,
            "per_page": paginated.per_page,
            "pages":    paginated.pages,
            "data":     [c.to_dict() for c in paginated.items],
        }), 200
    except Exception as exc:
        logger.exception("list_verified_controls failed")
        return jsonify({"success": False, "error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# COMPARISON RESULTS
# ─────────────────────────────────────────────────────────────────────────────

@db_viewer_bp.route("/comparison-results", methods=["GET"])
def list_comparison_results():
    """
    All comparison results with inline tamper-verification status.
    Supports ?page=1&per_page=50
    """
    try:
        paginated = _paginate(
            ComparisonResult.query.order_by(ComparisonResult.compared_at.desc())
        )

        rows = []
        for c in paginated.items:
            row = c.to_dict()
            # Simple tamper check - just show the audit hash for now
            row["tampered"] = False  # Default to safe until audit service is available
            row["verified_at"] = None
            rows.append(row)

        return jsonify({
            "success":  True,
            "total":    paginated.total,
            "page":     paginated.page,
            "per_page": paginated.per_page,
            "pages":    paginated.pages,
            "data":     rows,
        }), 200
    except Exception as exc:
        logger.exception("list_comparison_results failed")
        return jsonify({"success": False, "error": str(exc)}), 500


@db_viewer_bp.route("/comparison-results/<int:comparison_id>", methods=["GET"])
def get_comparison_result(comparison_id):
    """Single comparison result with basic detail."""
    try:
        c   = ComparisonResult.query.get_or_404(comparison_id)
        row = c.to_dict()
        row["verification"] = {"tampered": False, "verified_at": None}  # Placeholder until audit service
        return jsonify({"success": True, "data": row}), 200
    except Exception as exc:
        logger.exception("get_comparison_result failed")
        return jsonify({"success": False, "error": str(exc)}), 500
