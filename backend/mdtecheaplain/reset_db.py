"""
Setup script for initializing the OCR Compliance System backend
"""

import os
import sys

def create_directories():
    """Create necessary directories"""
    directories = ['uploads', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def initialize_database():
    """Initialize the database with tables"""
    from app import app
    from database import db
    
    with app.app_context():
        db.create_all()
        print("✓ Database tables created")

def seed_default_rules():
    """Seed database with default compliance rules"""
    from app import app
    from database import db
    from models.database import ComplianceRule
    
    with app.app_context():
        # Check if rules already exist
        if ComplianceRule.query.count() > 0:
            print("✓ Compliance rules already exist")
            return
        
        default_rules = [
            {
                'rule_name': 'Drug Name Required',
                'rule_type': 'content',
                'description': 'Pharmaceutical labels must contain drug name',
                'pattern': None,
                'severity': 'critical'
            },
            {
                'rule_name': 'Batch Number Format',
                'rule_type': 'format',
                'description': 'Batch number must follow standard format (BN-YYYY-NNNNNN)',
                'pattern': r'^[A-Z]{2}-\d{4}-\d{6}$',
                'severity': 'high'
            },
            {
                'rule_name': 'Expiry Date Required',
                'rule_type': 'content',
                'description': 'Expiry date must be present on label',
                'pattern': None,
                'severity': 'critical'
            },
            {
                'rule_name': 'Manufacturer Information',
                'rule_type': 'content',

                'description': 'Manufacturer name must be present',
                'pattern': None,
                'severity': 'high'
            },
            {
                'rule_name': 'Controlled Substance Marking',
                'rule_type': 'regulatory',
                'description': 'Controlled substances must display schedule information',
                'pattern': r'schedule\s+[I-V]+',
                'severity': 'critical'
            },
            {
                'rule_name': 'Dosage Information',
                'rule_type': 'content',
                'description': 'Dosage instructions should be clear and present',
                'pattern': None,
                'severity': 'medium'
            },
            {
                'rule_name': 'Storage Instructions',
                'rule_type': 'content',
                'description': 'Storage conditions should be specified',
                'pattern': None,
                'severity': 'low'
            }
        ]
        
        for rule_data in default_rules:
            rule = ComplianceRule(**rule_data)
            db.session.add(rule)
        
        db.session.commit()
        print(f"✓ Seeded {len(default_rules)} default compliance rules")

def create_env_file():
    """Create .env file if it doesn't exist"""
    if not os.path.exists('.env'):
        with open('.env.example', 'r') as example:
            with open('.env', 'w') as env:
                env.write(example.read())
        print("✓ Created .env file from template")
    else:
        print("✓ .env file already exists")

def main():
    """Run all setup tasks"""
    print("\n=== OCR Compliance System - Backend Setup ===\n")
    
    try:
        print("1. Creating directories...")
        create_directories()
        
        print("\n2. Creating environment file...")
        create_env_file()
        
        print("\n3. Initializing database...")
        initialize_database()
        
        print("\n4. Seeding default compliance rules...")
        seed_default_rules()
        
        print("\n=== Setup Complete! ===\n")
        print("Next steps:")
        print("1. Edit .env file with your configuration")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run the application: python app.py")
        print("\nAPI will be available at: http://localhost:5000")
        
    except Exception as e:
        print(f"\n✗ Setup failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
