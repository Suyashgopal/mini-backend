from flask import Blueprint, request, jsonify
from config.database import db
from models.database import VerifiedControl, OCRResult

bp = Blueprint("verified", __name__, url_prefix="/api/verified")


# ====================================================
# Create Verified Control
# ====================================================
@bp.route("/create/<int:ocr_result_id>", methods=["POST"])
def create_verified_control(ocr_result_id):
    if not request.is_json:
        return jsonify({"success": False, "error": "Request must be JSON"}), 400

    try:
        ocr_result = OCRResult.query.get_or_404(ocr_result_id)

        data = request.get_json()
        control_name = (data.get("control_name") or "").strip()
        status = (data.get("status") or "verified").strip().lower()

        if not control_name:
            return jsonify({"success": False, "error": "control_name is required"}), 400

        if status not in ["verified", "rejected"]:
            return jsonify({
                "success": False,
                "error": "status must be 'verified' or 'rejected'"
            }), 400

        verified = VerifiedControl(
            control_name=control_name,
            source_document_id=ocr_result.document_id,
            verified_text=ocr_result.translated_text,
            status=status,
        )

        db.session.add(verified)
        db.session.commit()

        return jsonify({"success": True, "data": verified.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# ====================================================
# List Verified Controls (Paginated)
# ====================================================
@bp.route("/", methods=["GET"])
def list_verified_controls():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        pagination = VerifiedControl.query.order_by(
            VerifiedControl.approved_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            "success": True,
            "data": [c.to_dict() for c in pagination.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ====================================================
# Get Single Verified Control
# ====================================================
@bp.route("/<int:control_id>", methods=["GET"])
def get_verified_control(control_id):
    try:
        control = VerifiedControl.query.get_or_404(control_id)
        return jsonify({"success": True, "data": control.to_dict()}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ====================================================
# Update Verified Control
# ====================================================
@bp.route("/<int:control_id>", methods=["PUT"])
def update_verified_control(control_id):
    if not request.is_json:
        return jsonify({"success": False, "error": "Request must be JSON"}), 400

    try:
        control = VerifiedControl.query.get_or_404(control_id)
        data = request.get_json()

        if "control_name" in data:
            new_name = (data.get("control_name") or "").strip()
            if not new_name:
                return jsonify({"success": False, "error": "control_name cannot be empty"}), 400
            control.control_name = new_name

        if "verified_text" in data:
            new_text = (data.get("verified_text") or "").strip()
            if not new_text:
                return jsonify({"success": False, "error": "verified_text cannot be empty"}), 400
            control.verified_text = new_text

        if "status" in data:
            status = (data.get("status") or "").strip().lower()
            if status not in ["verified", "rejected"]:
                return jsonify({
                    "success": False,
                    "error": "status must be 'verified' or 'rejected'"
                }), 400
            control.status = status

        db.session.commit()
        return jsonify({"success": True, "data": control.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# ====================================================
# Delete Verified Control
# ====================================================
@bp.route("/<int:control_id>", methods=["DELETE"])
def delete_verified_control(control_id):
    try:
        control = VerifiedControl.query.get_or_404(control_id)

        db.session.delete(control)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Verified control deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500