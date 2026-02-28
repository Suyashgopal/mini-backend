"""
app.py — Flask Application Entry Point

SPRING BOOT EQUIVALENT: This file is your main() + SpringApplication.run()
+ WebMvcConfigurer + application.properties all in one place.

HOW FLASK STARTS (read this once, remember it forever):
  1. Python runs this file top-to-bottom
  2. load_dotenv()        → reads your .env file into os.environ (like application.properties)
  3. _configure_logging() → sets up logging so you can see output in terminal
  4. app = Flask(...)     → creates the web server instance (like new SpringApplication())
  5. CORS(app)            → allows your frontend to call this backend
  6. app.config[...]      → sets configuration values (like @Value in Spring)
  7. db.init_app(app)     → connects SQLAlchemy ORM to this app (like DataSource bean)
  8. register_blueprint() → registers your route controllers (like @RestController scanning)
  9. app.run()            → starts listening for HTTP requests on port 5000
"""

import logging
import os
import platform

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

# Step 1: Load .env file
load_dotenv()


# ── Step 2: Configure logging ─────────────────────────────────────────────────
# Without this, every logger.info() and logger.warning() call in your services
# is silently thrown away. This makes them print to the terminal.
# FORMAT: timestamp | level | which file | message

def _configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

_configure_logging()
logger = logging.getLogger(__name__)


# ── Step 3: Poppler path setup (Windows only, PDF processing) if ollama fallback is enabled
if platform.system() == "Windows":
    poppler_path = os.getenv("POPPLER_PATH")  # read from .env if set
#if not found installes poppler
    if not poppler_path:
        # Standard installation locations — no personal paths
        standard_paths = [
            r"C:\Program Files\poppler\Library\bin",
            r"C:\Program Files (x86)\poppler\Library\bin",
            r"C:\poppler\bin",
        ]
        for path in standard_paths:
            if os.path.exists(path):
                poppler_path = path
                break

    if poppler_path and os.path.exists(poppler_path):
        os.environ["POPPLER_PATH"] = poppler_path
        logger.info("Poppler found at: %s", poppler_path)
    else:
        logger.warning(
            "Poppler not found. PDF fallback via Ollama may fail. "
            "Set POPPLER_PATH in .env or install Poppler to C:\\Program Files\\poppler"
        )


# ── Step 4: Create the Flask app ──────────────────────────────────────────────
# Flask(__name__) creates your web application.
# __name__ tells Flask where your project root is so it can find templates/static files.
# SPRING BOOT EQUIVALENT: new SpringApplication(App.class)
app = Flask(__name__)


# ── Step 5: Enable CORS ───────────────────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) allows your frontend (running on port 3000
# or 5173) to call this backend (running on port 5000).
# Without this, the browser blocks all frontend → backend requests.
#
# CORS_ORIGINS in .env controls which origins are allowed:
#   CORS_ORIGINS=*                           → allow everything (development)
#   CORS_ORIGINS=http://localhost:3000       → allow only your frontend (production)
cors_origins = os.getenv("CORS_ORIGINS", "*")
CORS(app, origins=cors_origins)


# ── Step 6: App configuration ─────────────────────────────────────────────────
# These are key=value settings that Flask and its extensions read.
# SPRING BOOT EQUIVALENT: application.properties / @Value annotations
#
# All values now read from .env with sensible defaults — nothing is hardcoded.
app.config["SECRET_KEY"]                  = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"]     = os.getenv("DATABASE_URL", "sqlite:///label_verification.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False   # disables a Flask-SQLAlchemy warning
app.config["UPLOAD_FOLDER"]              = os.getenv("UPLOAD_FOLDER", "uploads")
app.config["MAX_CONTENT_LENGTH"]         = int(os.getenv("MAX_UPLOAD_MB", "16")) * 1024 * 1024


# ── Step 7: Database initialization ──────────────────────────────────────────
# db is the SQLAlchemy instance created in config/database.py.
# db.init_app(app) connects it to THIS Flask app.
# SPRING BOOT EQUIVALENT: @EnableJpaRepositories + DataSource autoconfiguration
#
# db.create_all() creates all database tables if they don't exist yet.
# SPRING BOOT EQUIVALENT: spring.jpa.hibernate.ddl-auto=update
#
# WHAT WAS WRONG: Original had db.create_all() inside "if __name__ == '__main__'"
# which means it only ran when you started with "python app.py".
# If you ever use gunicorn (production server), __main__ never runs → no tables → crash.
# FIX: Run it inside app_context() at module level so it always runs on startup.
from config.database import db  # noqa: E402  (import after app creation is intentional)
db.init_app(app)

with app.app_context():
    db.create_all()
    logger.info("Database tables created/verified.")

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# ── Step 8: Register Blueprints (route controllers) ───────────────────────────
# A Blueprint is Flask's version of @RestController.
# Each Blueprint owns a group of related endpoints under a URL prefix.
# SPRING BOOT EQUIVALENT: @RestController + @RequestMapping("/api/ocr")
#
# registering a blueprint = "hey Flask, these routes exist, add them to the app"
from routes.ocr_routes       import bp           as ocr_bp         # /api/ocr/...
from routes.verified_routes  import bp           as verified_bp    # /api/verified/...
from routes.comparison_routes import bp          as comparison_bp  # /api/comparison/...
from routes.validation_routes import validation_bp                 # /api/validation/...

app.register_blueprint(ocr_bp)
app.register_blueprint(verified_bp)
app.register_blueprint(comparison_bp)
app.register_blueprint(validation_bp)

logger.info("All blueprints registered.")


# ── Step 9: Import OCR engine once at module level ────────────────────────────
# WHAT WAS WRONG: Original imported ocr_engine INSIDE the health_check function.
# That means Python re-ran the import statement on every single health poll.
# Python caches imports so it doesn't re-execute the file, but it's still
# unnecessary work and bad practice. Import once at the top, use everywhere.
from services.ocr_engine import ocr_engine  # noqa: E402


# ── Routes defined directly in app.py ────────────────────────────────────────
# These are simple utility routes that don't belong to any specific Blueprint.

@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint — used by frontend status bar to show if API is alive.
    Also reports which OCR engine is currently active (gemini / ollama / none).

    SPRING BOOT EQUIVALENT: Spring Actuator /actuator/health
    """
    return jsonify({
        "status":     "healthy",
        "ocr_engine": ocr_engine.active_engine,  # "gemini" | "ollama" | "none"
        "message":    "Label Verification API running",
    }), 200


@app.route("/", methods=["GET"])
def root():
    """
    Root endpoint — quick sanity check that the server is up.
    SPRING BOOT EQUIVALENT: a basic @GetMapping("/") on your main controller.
    """
    return jsonify({
        "status": "Backend running",
        "available_endpoints": [
            "/health",
            "/api/ocr/image",
            "/api/ocr/pdf",
            "/api/verified/",
            "/api/comparison/run/<control_id>/<ocr_result_id>",
            "/api/validation/validate-text",
        ],
    }), 200


@app.errorhandler(Exception)
def handle_exception(e):
    """
    Global error handler — catches any unhandled exception from any route
    and returns a clean JSON error instead of an HTML crash page.

    SPRING BOOT EQUIVALENT: @ControllerAdvice + @ExceptionHandler(Exception.class)
    """
    logger.exception("Unhandled exception: %s", str(e))
    return jsonify({
        "success": False,
        "error":   str(e),
    }), 500


# ── Step 10: Start the server ─────────────────────────────────────────────────
# "if __name__ == '__main__'" means: only run this block when you start the file
# directly with "python app.py". It does NOT run when imported by another module
# or when a production server like gunicorn loads this file.
#
# SPRING BOOT EQUIVALENT: SpringApplication.run(App.class, args)
#
# debug=True  → auto-restarts server when you save a file (dev only, never production)
# host="0.0.0.0" → accepts connections from any IP, not just localhost
# port=5000   → port number (read from .env if set)
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    logger.info("Starting server on port %d", port)
    app.run(
        debug=os.getenv("FLASK_DEBUG", "true").lower() == "true",
        host="0.0.0.0",
        port=port,
    )