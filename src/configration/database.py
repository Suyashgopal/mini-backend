"""
Database initialization module to avoid circular imports
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
