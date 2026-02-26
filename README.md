# Backend: Label Verification OCR API

A Flask-based OCR (Optical Character Recognition) and label verification system that supports multiple OCR engines and multilingual text processing.

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Dependencies & Versions](#dependencies--versions)
3. [Architecture](#architecture)
4. [API Endpoints](#api-endpoints)
5. [Database Models](#database-models)
6. [Services](#services)
7. [Configuration](#configuration)
8. [Installation & Usage](#installation--usage)
9. [Environment Setup](#environment-setup)

---

## 🎯 Project Overview

The Label Verification OCR Backend is a Flask application designed to:
- **Extract text** from images and PDFs using OCR (optical character recognition)
- **Support multiple OCR engines** (Ollama primary, Tesseract fallback)
- **Verify and classify** extracted text using verification controls
- **Store and manage** OCR results and verified data in SQLite database
- **Handle multilingual** text detection and processing
- **Process large documents** with smart chunking for PDFs

### Key Features:
- ✅ Image OCR (PNG, JPG, JPEG, BMP, TIFF)
- ✅ PDF OCR processing with page-by-page extraction
- ✅ Dual OCR engine support (Ollama LLM + Tesseract fallback)
- ✅ Text translation and normalization
- ✅ Language detection
- ✅ Verified control management
- ✅ REST API with CORS support
- ✅ Comprehensive error handling

---

## 📦 Dependencies & Versions

### Core Framework
| Package | Version | Purpose |
|---------|---------|---------|
| `Flask` | 3.0.0 | Web framework |
| `Flask-CORS` | 4.0.0 | Cross-origin request handling |
| `Flask-SQLAlchemy` | 3.1.1 | ORM for database management |
| `Werkzeug` | 3.0.1 | WSGI utilities |
| `SQLAlchemy` | 2.0.23 | SQL toolkit and ORM |

### OCR & Image Processing
| Package | Version | Purpose |
|---------|---------|---------|
| `pytesseract` | 0.3.10 | Tesseract OCR Python wrapper (Fallback engine) |
| `Pillow` | 10.1.0 | Image processing library |
| `opencv-python` | 4.8.1.78 | Computer vision and image processing |
| `numpy` | 1.26.2 | Numerical computing |

### PDF Processing
| Package | Version | Purpose |
|---------|---------|---------|
| `PyPDF2` | 3.0.1 | PDF file operations |
| `pdf2image` | 1.16.3 | Convert PDF pages to images |
| `reportlab` | 4.4.7 | PDF generation |

### Text & Language Processing
| Package | Version | Purpose |
|---------|---------|---------|
| `textblob` | 0.19.0 | Text processing, NLP |
| `langdetect` | 1.0.9 | Language detection |
| `requests` | 2.32.5 | HTTP requests (Ollama API calls) |
| `python-dotenv` | 1.0.0 | Environment variable management |

### Testing & Utilities
| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | 7.4.3 | Testing framework |
| `hypothesis` | 6.92.1 | Property-based testing |
| `psutil` | 5.9.8 | System/process utilities |

### External Dependencies
- **Tesseract OCR**: System package (requires separate installation)
- **Poppler**: PDF rendering engine
  - Windows: `poppler-25.12.0` (from Release-25.12.0-0)
  - Linux/Mac: Available via package managers
- **Ollama**: LLM server for primary OCR engine
  - Endpoint: `http://localhost:11434` (default)
  - Model: `glm-ocr:latest` (default)

---

## 🏗️ Architecture

### Directory Structure
```
backend/
├── app.py                      # Flask application entry point
├── config.py                   # Configuration management
├── database.py                 # SQLAlchemy database instance
├── requirements.txt            # Python dependencies
├── setup.py                    # Database reset script
├── reset_db.py                 # Alternative database reset
├── example_usage.py            # Usage examples
├── interfaces.py               # Type hints/interfaces
│
├── models/
│   ├── __init__.py
│   └── database.py            # SQLAlchemy model definitions
│
├── routes/
│   ├── __init__.py
│   ├── ocr_routes.py          # OCR API endpoints
│   ├── verified_routes.py     # Verified control endpoints
│   └── comparison_routes.py   # Text comparison endpoints
│
├── services/
│   ├── __init__.py
│   ├── ollama_ocr_service.py  # Ollama OCR implementation
│   └── comparison_service.py  # Text comparison logic
│
├── test/
│   ├── test_api_endpoints.py
│   ├── test_ocr.py
│   ├── test_ollama_integration.py
│   ├── test_performance_large_documents.py
│   ├── test_backward_compatibility.py
│   ├── test_error_handling.py
│   └── ...other test files
│
├── uploads/                    # File upload directory
├── instance/                   # Instance-specific files
├── __pycache__/               # Python cache
└── samples/                    # Sample documents for testing
```

### Application Flow
```
Request → Flask App
  ↓
Routes (OCR/Verified/Comparison)
  ↓
Services (Ollama/Tesseract OCR, Comparison Logic)
  ↓
Database (SQLAlchemy Models)
  ↓
SQLite Database
```

---

## 🔌 API Endpoints

### Health Check
```
GET /health
```
Returns the API health status.

### OCR Endpoints (`/api/ocr`)

#### Extract Text from Image
```
POST /api/ocr/image
Content-Type: multipart/form-data

Body:
  file: <image_file> (PNG, JPG, JPEG, BMP, TIFF)

Response:
{
  "success": true,
  "data": {
    "extracted_text": "...",
    "translated_text": "...",
    "language": "en",
    "processing_time": 5.23,
    "model_used": "glm-ocr:latest"
  }
}
```

#### Extract Text from PDF
```
POST /api/ocr/pdf
Content-Type: multipart/form-data

Body:
  file: <pdf_file>

Response:
{
  "success": true,
  "data": {
    "pages": [
      {
        "page_number": 1,
        "extracted_text": "...",
        "translated_text": "..."
      },
      ...
    ]
  }
}
```

### Verified Controls Endpoints (`/api/verified`)

#### Create Verified Control
```
POST /api/verified/create/<ocr_result_id>
Content-Type: application/json

Body:
{
  "control_name": "drug_name",
  "status": "verified"  // "verified" or "rejected"
}

Response:
{
  "success": true,
  "data": {
    "id": 1,
    "control_name": "drug_name",
    "verified_text": "...",
    "status": "verified",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

#### List Verified Controls (Paginated)
```
GET /api/verified/list?page=1&per_page=20

Response:
{
  "success": true,
  "data": [
    { verified control objects },
    ...
  ],
  "total": 100,
  "pages": 5
}
```

---

## 🗄️ Database Models

### Document Model
Represents uploaded document files.

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `filename` | String(255) | Original filename |
| `file_path` | String(500) | Storage path |
| `file_type` | String(50) | File extension (pdf, png, jpg, etc.) |
| `file_size` | Integer | File size in bytes |
| `uploaded_at` | DateTime | Upload timestamp |

### OCRResult Model
Stores OCR processing results.

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `document_id` | Integer (FK) | Reference to Document |
| `extracted_text` | Text | Raw OCR output |
| `translated_text` | Text | Processed/normalized text |
| `ocr_engine` | String(50) | Engine used (ollama/tesseract) |
| `model_name` | String(100) | Model name (glm-ocr, etc.) |
| `processing_time` | Float | Time taken in seconds |
| `processed_at` | DateTime | Processing timestamp |

### VerifiedControl Model
Stores verified and classified text controls.

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `control_name` | String(255) | Control identifier name |
| `source_document_id` | Integer (FK) | Reference to Document |
| `verified_text` | Text | The verified/classified text |
| `status` | String(50) | Status (verified/rejected) |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

---

## ⚙️ Services

### OllamaOCRService
**File**: `services/ollama_ocr_service.py`  
**Purpose**: Extract text from images and PDFs using Ollama LLM

**Key Methods**:
- `process_image(image_path)`: Extract text from image file
- `process_pdf(pdf_path)`: Extract text from all PDF pages
- `_preprocess_image(image_path)`: Image preprocessing (resize, grayscale, etc.)
- `_call_ollama_api(image_base64)`: Make API call to Ollama with retry logic

**Configuration**:
- Endpoint: `OLLAMA_ENDPOINT` (default: `http://localhost:11434`)
- Model: `OLLAMA_MODEL` (default: `glm-ocr:latest`)
- Timeout: `OLLAMA_TIMEOUT` (default: 30s)
- Max Retries: `OLLAMA_RETRIES` (default: 3)

**Features**:
- Base64 image encoding
- Automatic retry with exponential backoff
- Timeout handling for CPU-friendly operations
- Error recovery and logging

### ComparisonService
**File**: `services/comparison_service.py`  
**Purpose**: Compare and analyze text similarity

**Usage**:
- Text comparison operations
- Similarity scoring
- Diff analysis

---

## ⚙️ Configuration

The application uses environment variables for configuration. See `config.py` for all available settings.

### Key Environment Variables

```bash
# Flask Settings
FLASK_ENV=development
SECRET_KEY=your-secret-key

# Database
DATABASE_URI=sqlite:///label_verification.db

# Upload Settings
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216  # 16MB

# OCR Engine Selection
OCR_PRIMARY_ENGINE=ollama      # Primary: ollama or tesseract
OCR_FALLBACK_ENGINE=tesseract  # Fallback: tesseract

# Ollama Configuration
OLLAMA_ENABLED=true
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=glm-ocr:latest
OLLAMA_TIMEOUT=30

# Tesseract Configuration
TESSERACT_CMD=/usr/bin/tesseract  # Linux/Mac
TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe  # Windows

# Offline Mode
OFFLINE_MODE=false
```

---

## 🚀 Installation & Usage

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Setup External Dependencies

**Tesseract OCR** (optional, as fallback):
- Windows: Download installer from [GitHub Tesseract Releases](https://github.com/UB-Mannheim/tesseract/wiki)
- Linux: `sudo apt-get install tesseract-ocr`
- macOS: `brew install tesseract`

**Poppler** (for PDF processing):
- Windows: Already configured in `app.py` for path `C:\Users\KIIT0001\Downloads\Release-25.12.0-0\poppler-25.12.0`
- Linux: `sudo apt-get install poppler-utils`
- macOS: `brew install poppler`

**Ollama** (primary OCR engine):
- Download from [ollama.ai](https://ollama.ai)
- Install and run: `ollama serve`
- Pull model: `ollama pull glm-ocr`

### 3. Initialize Database
```bash
python reset_db.py
# or
python setup.py
```

### 4. Run the Application

**Windows**:
```bash
start_server.bat
# or
python app.py
```

**Linux/macOS**:
```bash
bash start_server.sh
# or
python app.py
```

The API will be available at `http://localhost:5000`

### 5. Running Tests
```bash
pytest test/
pytest test/test_ocr.py -v
pytest test/test_api_endpoints.py -v
```

---

## 🔧 Environment Setup

### Windows Setup
1. Ensure Python 3.8+ is installed
2. Create virtual environment: `python -m venv venv`
3. Activate: `venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Download Poppler from [Release-25.12.0](https://github.com/oschwartz10612/poppler-windows/releases/tag/v25.12.0)
6. Extract to `C:\Users\KIIT0001\Downloads\Release-25.12.0-0\`
7. Configure `POPPLER_PATH` or let `app.py` auto-detect
8. Install Ollama and run: `ollama serve`
9. Pull model: `ollama pull glm-ocr`
10. Start server: `python app.py`

### Linux/macOS Setup
1. Create virtual environment: `python3 -m venv venv`
2. Activate: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Install system dependencies: `brew install poppler tesseract` (macOS) or `sudo apt-get install poppler-utils tesseract-ocr` (Linux)
5. Install Ollama: Download from ollama.ai
6. Pull model: `ollama pull glm-ocr`
7. Start server: `python app.py`

---

## 📊 Database

### Database Type
- **SQLite** (default): `label_verification.db`
- Configurable via `DATABASE_URI` environment variable

### Creating/Resetting Database
```bash
# Option 1: Using setup.py
python setup.py

# Option 2: Using reset_db.py
python reset_db.py

# Option 3: In Python
from app import app, db
with app.app_context():
    db.create_all()
```

---

## 🧪 Testing

### Available Test Suites
- `test_api_endpoints.py` - API endpoint testing
- `test_ocr.py` - OCR functionality
- `test_ollama_integration.py` - Ollama integration
- `test_ollama_ocr_properties.py` - Property-based OCR tests
- `test_smart_chunking.py` - PDF chunking logic
- `test_performance_large_documents.py` - Performance testing
- `test_error_handling.py` - Error handling
- `test_backward_compatibility.py` - Backward compatibility

### Running Tests
```bash
# Run all tests
pytest

# Run specific test
pytest test/test_ocr.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=.
```

---

## 📝 Example Usage

See `example_usage.py` for complete usage examples including:
- Uploading images for OCR
- Processing PDFs
- Creating verified controls
- Listing results with pagination

```bash
python example_usage.py
```

---

## 🐛 Troubleshooting

### Ollama Connection Error
```
Error: Could not connect to Ollama at http://localhost:11434
```
**Solution**: Ensure Ollama is running: `ollama serve`

### Poppler Not Found
```
Error: pdftoppm is not installed or it is not in the PATH.
```
**Solution**: Install Poppler and set `POPPLER_PATH` environment variable

### Tesseract Not Found
```
Error: (2, 'No such file or directory')
```
**Solution**: Install Tesseract and set `TESSERACT_CMD` environment variable

### Database Locked
```
Error: database is locked
```
**Solution**: Close other connections or run `python reset_db.py`

---

## 📚 Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Ollama API Docs](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [PyPDF2 Documentation](https://pypdf2.readthedocs.io/)

---

## 📄 License

[Add your license here]

---

**Last Updated**: February 26, 2026  
**Maintained by**: [Your Team]
