#!/usr/bin/env python
"""
Reset the database:
- Deletes existing SQLite database
- Recreates schema using SQLAlchemy models
"""

import os
import sys
from urllib.parse import urlparse


print("🔄 Resetting database...")

try:
    from app import app
    from database import db

    # Get database URI from app config
    with app.app_context():
        db_uri = app.config["SQLALCHEMY_DATABASE_URI"]

    print(f"📁 Database URI: {db_uri}")

    # Only support SQLite reset
    if not db_uri.startswith("sqlite:///"):
        print("❌ Reset script only supports SQLite databases.")
        sys.exit(1)

    # Extract file path from URI
    parsed = urlparse(db_uri)
    db_path = parsed.path.lstrip("/")

    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"✅ Deleted existing database: {db_path}")
        except Exception as e:
            print(f"❌ Failed to delete database: {e}")
            print("   Ensure no process is using the DB file.")
            sys.exit(1)
    else:
        print("ℹ️ Database file does not exist. Creating new one...")

    # Recreate DB
    with app.app_context():
        db.create_all()

    print("\n✅ Database recreated successfully!")
    print("📊 Tables created from current models:")
    print("   - documents")
    print("   - ocr_results")

    print("\n🚀 You can now start the server:")
    print("   python app.py")

except Exception as e:
    print(f"\n❌ Database reset failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)