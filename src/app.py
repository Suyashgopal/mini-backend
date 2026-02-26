from flask import Flask, jsonify
from flask_cors import CORS
import os
import platform
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

# -----------------------------
# Windows Poppler Setup (PDF)
# -----------------------------
if platform.system() == "Windows":
    poppler_paths = [
        r"C:\Users\KIIT0001\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin",
        r"C:\Program Files\poppler\Library\bin",
        r"C:\Program Files (x86)\poppler\Library\bin",
    ]
    for path in poppler_paths:
        if os.path.exists(path):
            os.environ["POPPLER_PATH"] = path
            break


# -----------------------------
# Create Flask App
# -----------------------------
app = Flask(__name__)
CORS(app)


# -----------------------------
# Configuration
# -----------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///label_verification.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "pdf", "tiff"}


# -----------------------------
# Database Initialization
# -----------------------------
from config.database import db
db.init_app(app)

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# -----------------------------
# Register Blueprints
# -----------------------------
from routes.ocr_routes import bp as ocr_bp
from routes.verified_routes import bp as verified_bp
from routes.comparison_routes import bp as comparison_bp
from routes.validation_routes import validation_bp

app.register_blueprint(ocr_bp)
app.register_blueprint(verified_bp)
app.register_blueprint(comparison_bp)
app.register_blueprint(validation_bp)


# -----------------------------
# Health Check Route
# -----------------------------
@app.route("/health", methods=["GET"])
def health_check():
    from services.ocr_engine import ocr_engine
    return jsonify({
        "status": "healthy",
        "ocr_engine": ocr_engine.active_engine,   # "gemini" | "ollama" | "none"
        "message": "Label Verification API running"
    }), 200


# -----------------------------
# Global Error Handler
# -----------------------------
@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({
        "success": False,
        "error": str(e)
    }), 500


# -----------------------------
# Root Endpoint
# -----------------------------
@app.route("/")
def root():
    return {
        "status": "Backend running",
        "available_endpoints": [
            "/api/ocr/",
            "/api/verified/",
            "/api/comparison/"
        ]
    }


# -----------------------------
# Run Application
# -----------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )