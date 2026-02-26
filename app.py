from flask import Flask, jsonify
from flask_cors import CORS
import os
import platform

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
from database import db
db.init_app(app)

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# -----------------------------
# Register Blueprints
# -----------------------------
from routes import ocr_routes
from routes import verified_routes

app.register_blueprint(ocr_routes.bp)
app.register_blueprint(verified_routes.bp)


# -----------------------------
# Health Check Route
# -----------------------------
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
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