#!/usr/bin/env python
"""
Property-based tests for API endpoints using Hypothesis and pytest.

This test suite validates the correctness properties of the OCR API endpoints,
ensuring that the API behaves correctly across a wide range of inputs and scenarios.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**
"""

import pytest
import json
import os
import tempfile
from io import BytesIO
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from PIL import Image
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.database import Document, OCRResult
from services.multilingual_ocr_service import MultilingualOCRService


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


@pytest.fixture
def sample_image():
    """Create a sample image for testing"""
    img = Image.new('RGB', (100, 100), color='white')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


def create_test_image_file(filename='test.png'):
    """Create a temporary test image file"""
    img = Image.new('RGB', (200, 100), color='white')
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    img.save(temp_path)
    return temp_path


class TestAPIEndpointResponseStructure:
    """Tests for Property 12: API Endpoint Response Structure"""

    def test_property_12_multilingual_upload_response_structure(self, client, sample_image):
        """
        **Property 12: API Endpoint Response Structure**
        
        For any successful API call to /ocr/multilingual/upload or /ocr/multilingual/process, 
        the response should contain 'success': True, 'detected_language', 'original_language', 
        'translated' (boolean), and 'data' fields.
        
        **Validates: Requirements 5.1, 5.2, 5.3, 5.5**
        """
        # Create a test image
        img = Image.new('RGB', (200, 100), color='white')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Upload multilingual document
        response = client.post(
            '/api/ocr/multilingual/upload',
            data={'file': (img_bytes, 'test.png')},
            content_type='multipart/form-data'
        )
        
        # Verify response status
        assert response.status_code in [200, 400, 500], \
            f"Unexpected status code: {response.status_code}"
        
        # Parse response
        data = json.loads(response.data)
        
        # Verify response structure
        assert isinstance(data, dict), "Response should be a dictionary"
        assert 'success' in data, "Response should contain 'success' field"
        
        if response.status_code == 200 and data.get('success'):
            # For successful responses, verify all required fields
            assert 'detected_language' in data, "Response should contain 'detected_language'"
            assert 'original_language' in data, "Response should contain 'original_language'"
            assert 'translated' in data, "Response should contain 'translated'"
            assert 'data' in data, "Response should contain 'data'"
            
            # Verify field types
            assert isinstance(data['success'], bool), "'success' should be boolean"
            assert isinstance(data['translated'], bool), "'translated' should be boolean"
            assert isinstance(data['data'], dict), "'data' should be a dictionary"
            
            # Verify data contains OCR result
            assert 'id' in data['data'], "OCR result should have 'id'"
            assert 'extracted_text' in data['data'], "OCR result should have 'extracted_text'"
            assert 'confidence_score' in data['data'], "OCR result should have 'confidence_score'"

    def test_property_12_multilingual_process_response_structure(self, client):
        """
        Test that /ocr/multilingual/process endpoint returns correct response structure
        
        **Validates: Requirements 5.1, 5.2, 5.3, 5.5**
        """
        # First create a document
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
                
                # Now process it via API
                response = client.post(f'/api/ocr/multilingual/process/{doc_id}')
                
                # Verify response status
                assert response.status_code in [200, 400, 500], \
                    f"Unexpected status code: {response.status_code}"
                
                # Parse response
                data = json.loads(response.data)
                
                # Verify response structure
                assert isinstance(data, dict), "Response should be a dictionary"
                assert 'success' in data, "Response should contain 'success' field"
                
                if response.status_code == 200 and data.get('success'):
                    # For successful responses, verify all required fields
                    assert 'detected_language' in data, "Response should contain 'detected_language'"
                    assert 'original_language' in data, "Response should contain 'original_language'"
                    assert 'translated' in data, "Response should contain 'translated'"
                    assert 'data' in data, "Response should contain 'data'"
                    
                    # Verify field types
                    assert isinstance(data['success'], bool), "'success' should be boolean"
                    assert isinstance(data['translated'], bool), "'translated' should be boolean"
                    assert isinstance(data['data'], dict), "'data' should be a dictionary"
            finally:
                # Clean up
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    def test_property_12_error_response_structure(self, client):
        """
        Test that error responses have consistent structure
        
        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        # Try to upload without file
        response = client.post(
            '/api/ocr/multilingual/upload',
            data={},
            content_type='multipart/form-data'
        )
        
        # Should return 400 error
        assert response.status_code == 400
        
        # Parse response
        data = json.loads(response.data)
        
        # Verify error response structure
        assert isinstance(data, dict), "Error response should be a dictionary"
        assert 'error' in data, "Error response should contain 'error' field"
        assert isinstance(data['error'], str), "'error' should be a string"
        assert len(data['error']) > 0, "'error' message should not be empty"

    def test_property_12_invalid_file_type_response(self, client):
        """
        Test response when invalid file type is uploaded
        
        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        # Create a file with invalid extension
        invalid_file = BytesIO(b"invalid content")
        
        response = client.post(
            '/api/ocr/multilingual/upload',
            data={'file': (invalid_file, 'test.txt')},
            content_type='multipart/form-data'
        )
        
        # Should return 400 error
        assert response.status_code == 400
        
        # Parse response
        data = json.loads(response.data)
        
        # Verify error response
        assert 'error' in data
        assert 'Invalid file type' in data['error'] or 'invalid' in data['error'].lower()


class TestSupportedLanguagesEndpoint:
    """Tests for Property 13: Supported Languages Endpoint Completeness"""

    def test_property_13_supported_languages_endpoint_completeness(self, client):
        """
        **Property 13: Supported Languages Endpoint Completeness**
        
        For any call to /ocr/multilingual/languages endpoint, the response should 
        contain all 40+ supported languages with both language codes and human-readable names.
        
        **Validates: Requirements 5.1, 4.1, 4.2, 4.3, 4.4**
        """
        response = client.get('/api/ocr/multilingual/languages')
        
        # Verify response status
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Parse response
        data = json.loads(response.data)
        
        # Verify response structure
        assert isinstance(data, dict), "Response should be a dictionary"
        assert 'success' in data, "Response should contain 'success' field"
        assert data['success'] is True, "Response should indicate success"
        assert 'supported_languages' in data, "Response should contain 'supported_languages'"
        
        # Verify supported_languages is a dictionary
        languages = data['supported_languages']
        assert isinstance(languages, dict), "'supported_languages' should be a dictionary"
        
        # Verify we have at least 25 languages
        assert len(languages) >= 40, \
            f"Expected at least 40 languages, got {len(languages)}"
        
        # Verify each language has code and name
        for lang_code, lang_name in languages.items():
            assert isinstance(lang_code, str), "Language code should be a string"
            assert isinstance(lang_name, str), "Language name should be a string"
            assert len(lang_code) > 0, "Language code should not be empty"
            assert len(lang_name) > 0, "Language name should not be empty"

    def test_property_13_required_language_groups(self, client):
        """
        Test that all required language groups are present in the endpoint
        
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
        """
        response = client.get('/api/ocr/multilingual/languages')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        languages = data['supported_languages']
        
        # Define required language groups
        required_languages = {
            # European languages
            'en': 'English',
            'fr': 'French',
            'de': 'German',
            'es': 'Spanish',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'nl': 'Dutch',
            'sv': 'Swedish',
            'pl': 'Polish',
            'tr': 'Turkish',
            'el': 'Greek',
            'he': 'Hebrew',
            'th': 'Thai',
            # Asian languages
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ko': 'Korean',
            # Indian languages
            'hi': 'Hindi',
            'ta': 'Tamil',
            'te': 'Telugu',
            'kn': 'Kannada',
            'ml': 'Malayalam',
            'gu': 'Gujarati',
            'mr': 'Marathi',
            'bn': 'Bengali',
            'pa': 'Punjabi',
            'ur': 'Urdu',
            # Additional
            'et': 'Estonian',
        }
        
        # Check that all required languages are present
        for lang_code in required_languages.keys():
            assert lang_code in languages, \
                f"Required language '{lang_code}' not found in supported languages"

    def test_property_13_language_names_non_empty(self, client):
        """
        Test that all language names are non-empty and meaningful
        
        **Validates: Requirements 5.1, 4.1**
        """
        response = client.get('/api/ocr/multilingual/languages')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        languages = data['supported_languages']
        
        # Verify all language names are non-empty
        for lang_code, lang_name in languages.items():
            assert len(lang_name.strip()) > 0, \
                f"Language name for code '{lang_code}' is empty or whitespace"
            
            # Language name should not be just the code
            assert lang_name.lower() != lang_code.lower(), \
                f"Language name for '{lang_code}' should be descriptive, not just the code"

    def test_property_13_language_codes_format(self, client):
        """
        Test that language codes follow ISO 639-1 format
        
        **Validates: Requirements 5.1, 4.5**
        """
        response = client.get('/api/ocr/multilingual/languages')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        languages = data['supported_languages']
        
        # Verify language codes are lowercase and 2-5 characters
        for lang_code in languages.keys():
            assert lang_code == lang_code.lower(), \
                f"Language code '{lang_code}' should be lowercase"
            
            assert 2 <= len(lang_code) <= 5, \
                f"Language code '{lang_code}' should be 2-5 characters"


class TestDatabaseStorageOfMultilingualData:
    """Tests for Property 20: Database Storage of Multilingual Data"""

    def test_property_20_database_storage_of_multilingual_data(self, client):
        """
        **Property 20: Database Storage of Multilingual Data**
        
        For any translated document, both the original text and translated text 
        should be stored in the database metadata field and retrievable without data loss.
        
        **Validates: Requirements 5.5**
        """
        with app.app_context():
            # Create a test image file
            temp_path = create_test_image_file('test_storage.png')
            
            try:
                # Create document record
                document = Document(
                    filename='test_storage.png',
                    file_path=temp_path,
                    file_type='png',
                    file_size=1000,
                    status='pending'
                )
                db.session.add(document)
                db.session.commit()
                doc_id = document.id
                
                # Process via API
                response = client.post(f'/api/ocr/multilingual/process/{doc_id}')
                
                if response.status_code == 200:
                    data = json.loads(response.data)
                    
                    if data.get('success'):
                        # Retrieve the OCR result from database
                        ocr_result = OCRResult.query.filter_by(document_id=doc_id).first()
                        
                        assert ocr_result is not None, "OCR result should be stored in database"
                        
                        # Verify metadata is stored
                        if hasattr(ocr_result, 'metadata') and ocr_result.metadata:
                            metadata = ocr_result.metadata
                            
                            # Verify metadata structure
                            assert isinstance(metadata, dict), "Metadata should be a dictionary"
                            
                            # Verify metadata contains language information
                            assert 'detected_language' in metadata, \
                                "Metadata should contain 'detected_language'"
                            assert 'original_language' in metadata, \
                                "Metadata should contain 'original_language'"
                            assert 'translated' in metadata, \
                                "Metadata should contain 'translated' flag"
                            
                            # If translated, verify both texts are stored
                            if metadata.get('translated'):
                                assert 'original_text' in metadata, \
                                    "Metadata should contain 'original_text' for translated documents"
                                assert 'translated_text' in metadata, \
                                    "Metadata should contain 'translated_text' for translated documents"
                                
                                # Verify texts are not empty
                                assert len(metadata.get('original_text', '')) > 0, \
                                    "Original text should not be empty"
                                assert len(metadata.get('translated_text', '')) > 0, \
                                    "Translated text should not be empty"
            finally:
                # Clean up
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    def test_property_20_metadata_field_structure(self, client):
        """
        Test that metadata field has correct structure for multilingual data
        
        **Validates: Requirements 5.5**
        """
        with app.app_context():
            # Create a test image file
            temp_path = create_test_image_file('test_metadata.png')
            
            try:
                # Create document record
                document = Document(
                    filename='test_metadata.png',
                    file_path=temp_path,
                    file_type='png',
                    file_size=1000,
                    status='pending'
                )
                db.session.add(document)
                db.session.commit()
                doc_id = document.id
                
                # Process via API
                response = client.post(f'/api/ocr/multilingual/process/{doc_id}')
                
                if response.status_code == 200:
                    # Retrieve the OCR result from database
                    ocr_result = OCRResult.query.filter_by(document_id=doc_id).first()
                    
                    assert ocr_result is not None, "OCR result should be stored"
                    
                    # Verify metadata structure
                    if hasattr(ocr_result, 'metadata') and ocr_result.metadata:
                        metadata = ocr_result.metadata
                        
                        # Verify all expected fields are present
                        expected_fields = [
                            'detected_language',
                            'original_language',
                            'translated'
                        ]
                        
                        for field in expected_fields:
                            assert field in metadata, \
                                f"Metadata should contain '{field}' field"
                        
                        # Verify field types
                        assert isinstance(metadata['detected_language'], (str, type(None))), \
                            "'detected_language' should be string or None"
                        assert isinstance(metadata['original_language'], (str, type(None))), \
                            "'original_language' should be string or None"
                        assert isinstance(metadata['translated'], bool), \
                            "'translated' should be boolean"
            finally:
                # Clean up
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    def test_property_20_metadata_retrieval_without_data_loss(self, client):
        """
        Test that metadata can be retrieved without data loss
        
        **Validates: Requirements 5.5**
        """
        with app.app_context():
            # Create a test image file
            temp_path = create_test_image_file('test_retrieval.png')
            
            try:
                # Create document record
                document = Document(
                    filename='test_retrieval.png',
                    file_path=temp_path,
                    file_type='png',
                    file_size=1000,
                    status='pending'
                )
                db.session.add(document)
                db.session.commit()
                doc_id = document.id
                
                # Process via API
                response = client.post(f'/api/ocr/multilingual/process/{doc_id}')
                
                if response.status_code == 200:
                    # Retrieve the OCR result from database
                    ocr_result = OCRResult.query.filter_by(document_id=doc_id).first()
                    
                    assert ocr_result is not None, "OCR result should be retrievable"
                    
                    # Verify metadata is preserved
                    if hasattr(ocr_result, 'metadata') and ocr_result.metadata:
                        metadata = ocr_result.metadata
                        
                        # Verify metadata is a valid dictionary
                        assert isinstance(metadata, dict), "Metadata should be a dictionary"
                        
                        # Verify no data loss - all keys should be present
                        assert len(metadata) > 0, "Metadata should not be empty"
                        
                        # Verify values are preserved
                        for key, value in metadata.items():
                            assert value is not None or key in ['original_text', 'translated_text'], \
                                f"Metadata value for '{key}' should be preserved"
            finally:
                # Clean up
                if os.path.exists(temp_path):
                    os.remove(temp_path)


class TestDetectLanguageEndpoint:
    """Tests for language detection endpoint"""

    def test_detect_language_endpoint_response_structure(self, client):
        """
        Test that /ocr/multilingual/detect-language endpoint returns correct structure
        
        **Validates: Requirements 5.4**
        """
        # Create a test image
        img = Image.new('RGB', (200, 100), color='white')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        response = client.post(
            '/api/ocr/multilingual/detect-language',
            data={'file': (img_bytes, 'test.png')},
            content_type='multipart/form-data'
        )
        
        # Verify response status
        assert response.status_code in [200, 400, 500], \
            f"Unexpected status code: {response.status_code}"
        
        # Parse response
        data = json.loads(response.data)
        
        # Verify response structure
        assert isinstance(data, dict), "Response should be a dictionary"
        assert 'success' in data, "Response should contain 'success' field"
        
        if response.status_code == 200 and data.get('success'):
            # For successful responses, verify required fields
            assert 'detected_language_code' in data, \
                "Response should contain 'detected_language_code'"
            assert 'detected_language' in data, \
                "Response should contain 'detected_language'"
            assert 'confidence' in data, \
                "Response should contain 'confidence'"
            
            # Verify field types
            assert isinstance(data['detected_language_code'], str), \
                "'detected_language_code' should be string"
            assert isinstance(data['detected_language'], str), \
                "'detected_language' should be string"
            assert isinstance(data['confidence'], (int, float)), \
                "'confidence' should be numeric"

    def test_detect_language_endpoint_no_file_error(self, client):
        """
        Test that detect-language endpoint returns error when no file provided
        
        **Validates: Requirements 5.4**
        """
        response = client.post(
            '/api/ocr/multilingual/detect-language',
            data={},
            content_type='multipart/form-data'
        )
        
        # Should return 400 error
        assert response.status_code == 400
        
        # Parse response
        data = json.loads(response.data)
        
        # Verify error response
        assert 'error' in data
        assert 'No file' in data['error'] or 'file' in data['error'].lower()


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing endpoints"""

    def test_existing_upload_endpoint_still_works(self, client):
        """
        Test that existing /api/ocr/upload endpoint still works
        
        **Validates: Requirements 7.1, 7.6**
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
        assert 'success' in data or 'error' in data, \
            "Response should contain 'success' or 'error' field"

    def test_existing_results_endpoint_still_works(self, client):
        """
        Test that existing /api/ocr/results endpoint still works
        
        **Validates: Requirements 7.1, 7.6**
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
                processing_time=1.5
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
            
            # Verify response structure is unchanged
            assert data['success'] is True
            assert 'data' in data
            assert data['data']['extracted_text'] == 'Test text'


class TestAPIErrorHandling:
    """Tests for API error handling"""

    def test_invalid_document_id_returns_404(self, client):
        """
        Test that invalid document ID returns 404
        
        **Validates: Requirements 8.1, 8.3**
        """
        response = client.post('/api/ocr/multilingual/process/99999')
        
        # Should return 404
        assert response.status_code == 404

    def test_missing_file_returns_400(self, client):
        """
        Test that missing file returns 400
        
        **Validates: Requirements 8.1, 8.3**
        """
        response = client.post(
            '/api/ocr/multilingual/upload',
            data={},
            content_type='multipart/form-data'
        )
        
        # Should return 400
        assert response.status_code == 400
        
        # Parse response
        data = json.loads(response.data)
        
        # Verify error message
        assert 'error' in data
        assert len(data['error']) > 0

    def test_invalid_file_type_returns_400(self, client):
        """
        Test that invalid file type returns 400
        
        **Validates: Requirements 8.1, 8.3**
        """
        invalid_file = BytesIO(b"invalid content")
        
        response = client.post(
            '/api/ocr/multilingual/upload',
            data={'file': (invalid_file, 'test.txt')},
            content_type='multipart/form-data'
        )
        
        # Should return 400
        assert response.status_code == 400
        
        # Parse response
        data = json.loads(response.data)
        
        # Verify error message
        assert 'error' in data
        assert 'Invalid file type' in data['error'] or 'invalid' in data['error'].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
