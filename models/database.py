from database import db
from datetime import datetime
import json


# ============================================================
# DOCUMENT MODEL
# ============================================================

class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    ocr_results = db.relationship(
        "OCRResult",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy=True,
    )

    verified_controls = db.relationship(
        "VerifiedControl",
        back_populates="source_document",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "uploaded_at": self.uploaded_at.isoformat(),
        }


# ============================================================
# OCR RESULT MODEL
# ============================================================

class OCRResult(db.Model):
    __tablename__ = "ocr_results"

    id = db.Column(db.Integer, primary_key=True)

    document_id = db.Column(
        db.Integer,
        db.ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    extracted_text = db.Column(db.Text, nullable=False)
    translated_text = db.Column(db.Text, nullable=False)

    ocr_engine = db.Column(db.String(50))     # ollama / tesseract
    model_name = db.Column(db.String(100))    # llava, mistral, etc
    processing_time = db.Column(db.Float)
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    document = db.relationship("Document", back_populates="ocr_results")

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "extracted_text": self.extracted_text,
            "translated_text": self.translated_text,
            "ocr_engine": self.ocr_engine,
            "model_name": self.model_name,
            "processing_time": self.processing_time,
            "processed_at": self.processed_at.isoformat(),
        }


# ============================================================
# VERIFIED CONTROL (THIS IS YOUR RULE)
# ============================================================

class VerifiedControl(db.Model):
    __tablename__ = "verified_controls"

    id = db.Column(db.Integer, primary_key=True)

    control_name = db.Column(db.String(255), nullable=False)

    source_document_id = db.Column(
        db.Integer,
        db.ForeignKey("documents.id", ondelete="SET NULL"),
        index=True,
    )

    verified_text = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(50), default="verified")  
    # verified / rejected (for safety)

    approved_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    source_document = db.relationship(
        "Document",
        back_populates="verified_controls"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "control_name": self.control_name,
            "verified_text": self.verified_text,
            "status": self.status,
            "approved_at": self.approved_at.isoformat(),
        }


# ============================================================
# COMPARISON RESULT (NOT USED YET)
# ============================================================

class ComparisonResult(db.Model):
    __tablename__ = "comparison_results"

    id = db.Column(db.Integer, primary_key=True)

    verified_control_id = db.Column(
        db.Integer,
        db.ForeignKey("verified_controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ocr_result_id = db.Column(
        db.Integer,
        db.ForeignKey("ocr_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    match_percentage = db.Column(db.Float)

    deviations = db.Column(db.Text)  # Stored as JSON string

    status = db.Column(db.String(50))  # PASS / FAIL

    compared_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "verified_control_id": self.verified_control_id,
            "ocr_result_id": self.ocr_result_id,
            "match_percentage": self.match_percentage,
            "deviations": json.loads(self.deviations)
            if self.deviations else [],
            "status": self.status,
            "compared_at": self.compared_at.isoformat(),
        }