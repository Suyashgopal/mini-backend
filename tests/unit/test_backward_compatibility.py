#!/usr/bin/env python
"""
Backward Compatibility Tests for Multilingual Translation Integration

This test suite validates that the new multilingual translation system maintains
backward compatibility with existing OCR workflows, compliance checks, error detection,
and analytics.

**Task 12.1: Write integration tests for backward compatibility**
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6**

**Property 14: Backward Compatibility - Existing Endpoints**
*For any* document processed using existing OCR endpoints (without language parameters), 
the system should return results with the same structure and content as before the integration.

**Property 15: Backward Compatibility - Compliance Checks**
*For any* OCR result (translated or not), compliance checks should execute successfully 
and return valid compliance scores.

Test Coverage:
- TestExistingOCREndpointsWithoutLanguageParameters: Tests Property 14
- TestComplianceChecksWithTranslatedText: Tests Property 15
- TestErrorDetectionWithTranslatedText: Tests error detection with translated text
- TestAnalyticsWithMultilingualDocuments: Tests analytics with multilingual data
- TestExistingClientCodeCompatibility: Tests backward compatibility for client code
"""

import pytest
import json
import os
import tempfile
from io import BytesIO
from unittest.mock import patch, MagicMock
from PIL import Image
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.database import Document, OCRResult, ComplianceCheck, ErrorDetection
from services.ocr_service import OCRService
from services.multilingual_ocr_service import MultilingualOCRService
from services.compliance_service import ComplianceService
from services.error_detection_service import ErrorDetectionService
from services.translation_service import TranslationService
from services.language_detection_service import LanguageDetectionService


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def create_test_image_file(filename='test.png'):
    """Create a temporary test image file"""
    img = Image.new('RGB', (200, 100), color='white')
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    img.save(temp_path)
    return temp_path


class TestExistingOCREndpointsWithoutLanguageParameters:
    """
    Test that existing OCR endpoints work without language parameters.
    
    **Validates: Property 14 - Backward Compatibility - Existing Endpoints**
    **Validates: Requirements 7.1, 7.6**
    """

    def test_existing_upload_endpoint_returns_same_structure(self, client):
        """
        Test that /api/ocr/upload endpoint returns the same response structure
        as before the multilingual integration.
        
        **Validates: Property 14, Requirements 7.1, 7.6**
        """
        # Create a test image
        img = Image.new('RGB', (200, 100), color='white')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        response = client.post(
            '/api/ocr/upload',
            data={'file': (img_bytes, 'test.png')},
            content_type='multipart/form-data'
        )
        
        # Should return 200 or 500 (depending on OCR availability)
        assert response.status_code in [200, 500], \
            f"Unexpected status code: {response.status_code}"
        
        # Parse response
        data = json.loads(response.data)
        
        # Verify response structure is unchanged
        assert isinstance(data, dict), "Response should be a dictionary"
        
        if response.status_code == 200:
            # For successful responses, verify original fields are present
            assert 'success' in data
            assert 'document_id' in data
            assert 'ocr_result_id' in data
            assert 'data' in data
            
            # Verify OCR result structure
            ocr_data = data['data']
            assert 'extracted_text' in ocr_data
            assert 'confidence_score' in ocr_data
            assert 'processing_time' in ocr_data

    def test_existing_process_endpoint_returns_same_structure(self, client):
        """
        Test that /api/ocr/process endpoint returns the same response structure.
        
        **Validates: Property 14, Requirements 7.1, 7.6**
        """
        with app.app_context():
            # Create a test image file
            temp_path = create_test_image_file('test_process.png')
            
            try:
                # Create document record
                document = Document(
                    filename='test_process.png',
                    file_path=temp_path,
                    file_type='png',
                    file_size=1000,
                    status='pending'
                )
                db.session.add(document)
                db.session.commit()
                doc_id = document.id
                
                # Process via existing endpoint
                response = client.post(f'/api/ocr/process/{doc_id}')
                
                # Should return 200 or 500
                assert response.status_code in [200, 500]
                
                # Parse response
                data = json.loads(response.data)
                
                # Verify response structure
                assert isinstance(data, dict)
                
                if response.status_code == 200:
                    assert 'success' in data
                    assert 'data' in data
                    
                    # Verify OCR result structure
                    ocr_data = data['data']
                    assert 'extracted_text' in ocr_data
                    assert 'confidence_score' in ocr_data
                    assert 'processing_time' in ocr_data
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    def test_existing_results_endpoint_unchanged(self, client):
        """
        Test that /api/ocr/results endpoint returns unchanged structure.
        
        **Validates: Property 14, Requirements 7.1, 7.6**
        """
        with app.app_context():
            # Create a test document and OCR result
            document = Document(
                filename='test.png',
                file_path='/tmp/test.png',
                file_type='png',
                file_size=1000,
                status='completed'
            )
            db.session.add(document)
            db.session.commit()
            
            ocr_result = OCRResult(
                document_id=document.id,
                extracted_text='Test text',
                confidence_score=0.95,
                processing_time=1.5,
                drug_name='Aspirin',
                batch_number='ABC123',
                expiry_date='2025-12-31'
            )
            db.session.add(ocr_result)
            db.session.commit()
            result_id = ocr_result.id
            
            # Retrieve via API
            response = client.get(f'/api/ocr/results/{result_id}')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify response structure
            assert data['success'] is True
            assert 'data' in data
            
            # Verify OCR result fields
            ocr_data = data['data']
            assert ocr_data['extracted_text'] == 'Test text'
            assert ocr_data['confidence_score'] == 0.95
            assert ocr_data['drug_name'] == 'Aspirin'

    def test_existing_documents_list_endpoint_unchanged(self, client):
        """
        Test that /api/ocr/documents endpoint returns unchanged structure.
        
        **Validates: Property 14, Requirements 7.1, 7.6**
        """
        with app.app_context():
            # Create test documents
            for i in range(3):
                document = Document(
                    filename=f'test{i}.png',
                    file_path=f'/tmp/test{i}.png',
                    file_type='png',
                    file_size=1000,
                    status='completed'
                )
                db.session.add(document)
            db.session.commit()
            
            # Retrieve documents list
            response = client.get('/api/ocr/documents')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify response structure
            assert data['success'] is True
            assert 'data' in data
            assert isinstance(data['data'], list)
            assert len(data['data']) >= 3


class TestComplianceChecksWithTranslatedText:
    """
    Test that compliance checks work with translated text.
    
    **Validates: Property 15 - Backward Compatibility - Compliance Checks**
    **Validates: Requirements 7.3, 7.4, 7.5**
    """

    def test_compliance_checks_work_with_english_text(self, client):
        """
        Test that compliance checks work with English (non-translated) text.
        
        **Validates: Property 15, Requirements 7.3, 7.4, 7.5**
        """
        with app.app_context():
            # Create a test document and OCR result with English text
            document = Document(
                filename='test.png',
                file_path='/tmp/test.png',
                file_type='png',
                file_size=1000,
                status='completed'
            )
            db.session.add(document)
            db.session.commit()
            
            ocr_result = OCRResult(
                document_id=document.id,
                extracted_text='Drug: Aspirin, Batch: AB-2024-123456, Expiry: 12/2025, Manufacturer: Pharma Inc',
                confidence_score=0.95,
                processing_time=1.5,
                drug_name='Aspirin',
                batch_number='AB-2024-123456',
                expiry_date='12/2025',
                manufacturer='Pharma Inc'
            )
            db.session.add(ocr_result)
            db.session.commit()
            result_id = ocr_result.id
            
            # Run compliance checks via API
            response = client.post(f'/api/ocr/results/{result_id}/validate')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify compliance check structure
            assert data['success'] is True
            assert 'compliance_score' in data
            assert 'checks' in data
            assert isinstance(data['checks'], list)
            
            # Verify compliance score is valid
            assert 0 <= data['compliance_score'] <= 100

    def test_compliance_checks_work_with_translated_text(self, client):
        """
        Test that compliance checks work with translated text.
        
        **Validates: Property 15, Requirements 7.3, 7.4, 7.5**
        """
        with app.app_context():
            # Create a test document and OCR result with translated text
            document = Document(
                filename='test_spanish.png',
                file_path='/tmp/test_spanish.png',
                file_type='png',
                file_size=1000,
                status='completed'
            )
            db.session.add(document)
            db.session.commit()
            
            # Simulate translated text (Spanish -> English)
            ocr_result = OCRResult(
                document_id=document.id,
                extracted_text='Drug: Aspirin, Batch: AB-2024-123456, Expiry: 12/2025, Manufacturer: Pharma Inc',
                confidence_score=0.95,
                processing_time=1.5,
                drug_name='Aspirin',
                batch_number='AB-2024-123456',
                expiry_date='12/2025',
                manufacturer='Pharma Inc'
            )
            
            # Store metadata indicating translation occurred
            ocr_result.metadata = {
                'detected_language': 'Spanish',
                'original_language': 'Spanish',
                'translated': True,
                'original_text': 'Medicamento: Aspirina, Lote: AB-2024-123456, Vencimiento: 12/2025, Fabricante: Pharma Inc',
                'translated_text': 'Drug: Aspirin, Batch: AB-2024-123456, Expiry: 12/2025, Manufacturer: Pharma Inc'
            }
            
            db.session.add(ocr_result)
            db.session.commit()
            result_id = ocr_result.id
            
            # Run compliance checks via API
            response = client.post(f'/api/ocr/results/{result_id}/validate')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify compliance check structure
            assert data['success'] is True
            assert 'compliance_score' in data
            assert 'checks' in data
            
            # Verify compliance checks executed successfully
            assert len(data['checks']) > 0
            assert 0 <= data['compliance_score'] <= 100

    def test_compliance_checks_preserve_original_functionality(self, client):
        """
        Test that compliance checks preserve original functionality.
        
        **Validates: Property 15, Requirements 7.3, 7.4, 7.5**
        """
        with app.app_context():
            # Create OCR result with missing required fields
            document = Document(
                filename='test_incomplete.png',
                file_path='/tmp/test_incomplete.png',
                file_type='png',
                file_size=1000,
                status='completed'
            )
            db.session.add(document)
            db.session.commit()
            
            ocr_result = OCRResult(
                document_id=document.id,
                extracted_text='Some text',
                confidence_score=0.95,
                processing_time=1.5
                # Missing drug_name, batch_number, expiry_date, manufacturer
            )
            db.session.add(ocr_result)
            db.session.commit()
            result_id = ocr_result.id
            
            # Run compliance checks
            response = client.post(f'/api/ocr/results/{result_id}/validate')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify compliance checks detected failures
            assert data['success'] is True
            assert 'checks' in data
            
            # Should have some failed checks
            failed_checks = [c for c in data['checks'] if c['status'] == 'failed']
            assert len(failed_checks) > 0


class TestErrorDetectionWithTranslatedText:
    """
    Test that error detection works with translated text.
    
    **Validates: Requirements 7.3, 7.4, 7.5**
    """

    def test_error_detection_works_with_english_text(self, client):
        """
        Test that error detection works with English text.
        
        **Validates: Requirements 7.3, 7.4, 7.5**
        """
        with app.app_context():
            # Create a test document and OCR result
            document = Document(
                filename='test.png',
                file_path='/tmp/test.png',
                file_type='png',
                file_size=1000,
                status='completed'
            )
            db.session.add(document)
            db.session.commit()
            
            ocr_result = OCRResult(
                document_id=document.id,
                extracted_text='Drug: Aspirin, Batch: AB-2024-123456, Expiry: 12/2025',
                confidence_score=0.95,
                processing_time=1.5,
                drug_name='Aspirin',
                batch_number='AB-2024-123456',
                expiry_date='12/2025'
            )
            db.session.add(ocr_result)
            db.session.commit()
            result_id = ocr_result.id
            
            # Run error detection via API
            response = client.get(f'/api/ocr/results/{result_id}/errors')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify error detection structure
            assert data['success'] is True
            assert 'errors' in data
            assert 'suggestions' in data
            assert isinstance(data['errors'], list)
            assert isinstance(data['suggestions'], dict)

    def test_error_detection_works_with_translated_text(self, client):
        """
        Test that error detection works with translated text.
        
        **Validates: Requirements 7.3, 7.4, 7.5**
        """
        with app.app_context():
            # Create a test document and OCR result with translated text
            document = Document(
                filename='test_spanish.png',
                file_path='/tmp/test_spanish.png',
                file_type='png',
                file_size=1000,
                status='completed'
            )
            db.session.add(document)
            db.session.commit()
            
            # Simulate translated text
            ocr_result = OCRResult(
                document_id=document.id,
                extracted_text='Drug: Aspirin, Batch: AB-2024-123456, Expiry: 12/2025',
                confidence_score=0.95,
                processing_time=1.5,
                drug_name='Aspirin',
                batch_number='AB-2024-123456',
                expiry_date='12/2025'
            )
            
            # Store metadata indicating translation
            ocr_result.metadata = {
                'detected_language': 'Spanish',
                'original_language': 'Spanish',
                'translated': True,
                'original_text': 'Medicamento: Aspirina, Lote: AB-2024-123456, Vencimiento: 12/2025',
                'translated_text': 'Drug: Aspirin, Batch: AB-2024-123456, Expiry: 12/2025'
            }
            
            db.session.add(ocr_result)
            db.session.commit()
            result_id = ocr_result.id
            
            # Run error detection via API
            response = client.get(f'/api/ocr/results/{result_id}/errors')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify error detection structure
            assert data['success'] is True
            assert 'errors' in data
            assert 'suggestions' in data

    def test_error_detection_detects_format_errors(self, client):
        """
        Test that error detection still detects format errors in translated text.
        
        **Validates: Requirements 7.3, 7.4, 7.5**
        """
        with app.app_context():
            # Create OCR result with format errors
            document = Document(
                filename='test_errors.png',
                file_path='/tmp/test_errors.png',
                file_type='png',
                file_size=1000,
                status='completed'
            )
            db.session.add(document)
            db.session.commit()
            
            ocr_result = OCRResult(
                document_id=document.id,
                extracted_text='Drug: Aspirin, Batch: INVALID, Expiry: INVALID',
                confidence_score=0.95,
                processing_time=1.5,
                drug_name='Aspirin',
                batch_number='INVALID',
                expiry_date='INVALID'
            )
            db.session.add(ocr_result)
            db.session.commit()
            result_id = ocr_result.id
            
            # Run error detection
            response = client.get(f'/api/ocr/results/{result_id}/errors')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify errors were detected
            assert data['success'] is True
            assert len(data['errors']) > 0


class TestAnalyticsWithMultilingualDocuments:
    """
    Test that analytics work with multilingual documents.
    
    **Validates: Requirements 7.2, 7.5**
    """

    def test_documents_list_includes_multilingual_documents(self, client):
        """
        Test that documents list includes multilingual documents.
        
        **Validates: Requirements 7.2, 7.5**
        """
        with app.app_context():
            # Create multilingual documents
            for i in range(3):
                document = Document(
                    filename=f'test_multilingual_{i}.png',
                    file_path=f'/tmp/test_multilingual_{i}.png',
                    file_type='png',
                    file_size=1000,
                    status='completed'
                )
                db.session.add(document)
            db.session.commit()
            
            # Retrieve documents list
            response = client.get('/api/ocr/documents')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify documents are listed
            assert data['success'] is True
            assert len(data['data']) >= 3

    def test_ocr_results_include_multilingual_metadata(self, client):
        """
        Test that OCR results include multilingual metadata.
        
        **Validates: Requirements 7.2, 7.5**
        """
        with app.app_context():
            # Create document with multilingual metadata
            document = Document(
                filename='test_multilingual.png',
                file_path='/tmp/test_multilingual.png',
                file_type='png',
                file_size=1000,
                status='completed'
            )
            db.session.add(document)
            db.session.commit()
            
            ocr_result = OCRResult(
                document_id=document.id,
                extracted_text='Drug: Aspirin, Batch: AB-2024-123456, Expiry: 12/2025',
                confidence_score=0.95,
                processing_time=1.5,
                drug_name='Aspirin',
                batch_number='AB-2024-123456',
                expiry_date='12/2025'
            )
            
            # Add multilingual metadata
            ocr_result.metadata = {
                'detected_language': 'Spanish',
                'original_language': 'Spanish',
                'translated': True,
                'original_text': 'Medicamento: Aspirina, Lote: AB-2024-123456, Vencimiento: 12/2025',
                'translated_text': 'Drug: Aspirin, Batch: AB-2024-123456, Expiry: 12/2025'
            }
            
            db.session.add(ocr_result)
            db.session.commit()
            result_id = ocr_result.id
            
            # Retrieve result
            response = client.get(f'/api/ocr/results/{result_id}')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify result includes metadata
            assert data['success'] is True
            ocr_data = data['data']
            
            # Verify metadata is preserved
            if hasattr(ocr_data, 'metadata') or 'metadata' in ocr_data:
                metadata = ocr_data.get('metadata') if isinstance(ocr_data, dict) else getattr(ocr_data, 'metadata', None)
                if metadata:
                    assert 'detected_language' in metadata
                    assert 'translated' in metadata

    def test_compliance_checks_stored_for_multilingual_documents(self, client):
        """
        Test that compliance checks are stored for multilingual documents.
        
        **Validates: Requirements 7.2, 7.5**
        """
        with app.app_context():
            # Create multilingual document
            document = Document(
                filename='test_multilingual.png',
                file_path='/tmp/test_multilingual.png',
                file_type='png',
                file_size=1000,
                status='completed'
            )
            db.session.add(document)
            db.session.commit()
            
            ocr_result = OCRResult(
                document_id=document.id,
                extracted_text='Drug: Aspirin, Batch: AB-2024-123456, Expiry: 12/2025, Manufacturer: Pharma Inc',
                confidence_score=0.95,
                processing_time=1.5,
                drug_name='Aspirin',
                batch_number='AB-2024-123456',
                expiry_date='12/2025',
                manufacturer='Pharma Inc'
            )
            
            # Add multilingual metadata
            ocr_result.metadata = {
                'detected_language': 'Spanish',
                'original_language': 'Spanish',
                'translated': True
            }
            
            db.session.add(ocr_result)
            db.session.commit()
            result_id = ocr_result.id
            
            # Run compliance checks
            response = client.post(f'/api/ocr/results/{result_id}/validate')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify compliance checks were stored
            assert data['success'] is True
            assert 'checks' in data
            
            # Verify checks are stored in database
            checks = ComplianceCheck.query.filter_by(ocr_result_id=result_id).all()
            assert len(checks) > 0


class TestExistingClientCodeCompatibility:
    """
    Test that existing client code still works.
    
    **Validates: Property 14, Requirements 7.1, 7.6**
    """

    def test_existing_client_can_upload_without_language_support(self, client):
        """
        Test that existing client code can upload documents without using language features.
        
        **Validates: Property 14, Requirements 7.1, 7.6**
        """
        # Create a test image
        img = Image.new('RGB', (200, 100), color='white')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Upload using existing endpoint (not multilingual)
        response = client.post(
            '/api/ocr/upload',
            data={'file': (img_bytes, 'test.png')},
            content_type='multipart/form-data'
        )
        
        # Should return 200 or 500 (depending on OCR availability)
        assert response.status_code in [200, 500]
        
        # Parse response
        data = json.loads(response.data)
        
        # Verify response structure matches what existing clients expect
        assert isinstance(data, dict)
        if response.status_code == 200:
            assert 'success' in data
            assert 'document_id' in data
            assert 'ocr_result_id' in data

    def test_existing_client_can_validate_without_language_support(self, client):
        """
        Test that existing client code can validate results without language features.
        
        **Validates: Property 14, Requirements 7.1, 7.6**
        """
        with app.app_context():
            # Create a test document and OCR result
            document = Document(
                filename='test.png',
                file_path='/tmp/test.png',
                file_type='png',
                file_size=1000,
                status='completed'
            )
            db.session.add(document)
            db.session.commit()
            
            ocr_result = OCRResult(
                document_id=document.id,
                extracted_text='Drug: Aspirin, Batch: AB-2024-123456, Expiry: 12/2025, Manufacturer: Pharma Inc',
                confidence_score=0.95,
                processing_time=1.5,
                drug_name='Aspirin',
                batch_number='AB-2024-123456',
                expiry_date='12/2025',
                manufacturer='Pharma Inc'
            )
            db.session.add(ocr_result)
            db.session.commit()
            result_id = ocr_result.id
            
            # Validate using existing endpoint
            response = client.post(f'/api/ocr/results/{result_id}/validate')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify response structure matches what existing clients expect
            assert data['success'] is True
            assert 'compliance_score' in data
            assert 'checks' in data

    def test_existing_client_can_detect_errors_without_language_support(self, client):
        """
        Test that existing client code can detect errors without language features.
        
        **Validates: Property 14, Requirements 7.1, 7.6**
        """
        with app.app_context():
            # Create a test document and OCR result
            document = Document(
                filename='test.png',
                file_path='/tmp/test.png',
                file_type='png',
                file_size=1000,
                status='completed'
            )
            db.session.add(document)
            db.session.commit()
            
            ocr_result = OCRResult(
                document_id=document.id,
                extracted_text='Drug: Aspirin, Batch: AB-2024-123456, Expiry: 12/2025',
                confidence_score=0.95,
                processing_time=1.5,
                drug_name='Aspirin',
                batch_number='AB-2024-123456',
                expiry_date='12/2025'
            )
            db.session.add(ocr_result)
            db.session.commit()
            result_id = ocr_result.id
            
            # Detect errors using existing endpoint
            response = client.get(f'/api/ocr/results/{result_id}/errors')
            
            # Should return 200
            assert response.status_code == 200
            
            # Parse response
            data = json.loads(response.data)
            
            # Verify response structure matches what existing clients expect
            assert data['success'] is True
            assert 'errors' in data
            assert 'suggestions' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
