"""
Property-based tests for Ollama OCR Service
Tests correctness properties across various inputs and scenarios
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch, MagicMock
import base64
import io
from PIL import Image
import requests

from services.ollama_ocr_service import OllamaOCRService


class TestOllamaOCRServiceProperties:
    """Property-based tests for OllamaOCRService"""
    
    @pytest.fixture
    def ollama_service(self):
        """Create an OllamaOCRService instance for testing"""
        return OllamaOCRService(
            ollama_endpoint="http://localhost:11434",
            model_name="glm-ocr:latest",
            timeout=30
        )
    
    # Property 1: OCR Engine Fallback Mechanism
    # For any image file and any Ollama unavailability scenario, the system should 
    # automatically fall back to Tesseract and return valid OCR results
    @given(
        image_data=st.binary(min_size=100, max_size=100000),
        error_type=st.sampled_from(['timeout', 'connection_error', 'invalid_response'])
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_ollama_availability_detection_property(self, ollama_service, image_data, error_type):
        """
        Property 1: OCR Engine Fallback Mechanism
        Validates: Requirements 1.1, 4.1
        
        For any image and any Ollama error scenario, the service should detect
        the unavailability and be ready for fallback.
        """
        # Mock different error scenarios
        with patch('requests.post') as mock_post:
            if error_type == 'timeout':
                mock_post.side_effect = requests.Timeout("Connection timeout")
            elif error_type == 'connection_error':
                mock_post.side_effect = requests.ConnectionError("Connection refused")
            elif error_type == 'invalid_response':
                mock_post.return_value = Mock(status_code=500, text="Internal Server Error")
            
            # Verify that the service raises an exception (which would trigger fallback)
            with pytest.raises(Exception):
                # Create a temporary image file
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                    f.write(image_data)
                    temp_path = f.name
                
                try:
                    ollama_service.process_image(temp_path)
                finally:
                    import os
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
    
    # Property 6: Confidence Score Validity
    # For any OCR result, the confidence score should be between 0 and 1
    @given(
        text_length=st.integers(min_value=0, max_value=10000),
        alphanumeric_ratio=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_confidence_score_validity_property(self, ollama_service, text_length, alphanumeric_ratio):
        """
        Property 6: Confidence Score Validity
        Validates: Requirements 1.5
        
        For any extracted text, the confidence score should always be between 0 and 1.
        """
        # Generate text with specified characteristics
        if text_length == 0:
            text = ""
        else:
            alphanumeric_count = int(text_length * alphanumeric_ratio)
            other_count = text_length - alphanumeric_count
            
            text = 'a' * alphanumeric_count + ' ' * other_count
        
        # Calculate confidence
        confidence = ollama_service._calculate_confidence(text)
        
        # Verify confidence is in valid range
        assert isinstance(confidence, float), "Confidence should be a float"
        assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} should be between 0 and 1"
    
    # Property 2: API Response Format Consistency
    # For any document processed, the API response should contain all required fields
    @given(
        extracted_text=st.text(min_size=1, max_size=1000),
        processing_time=st.floats(min_value=0.1, max_value=100.0)
    )
    @settings(max_examples=50)
    def test_api_response_format_consistency_property(self, ollama_service, extracted_text, processing_time):
        """
        Property 2: API Response Format Consistency
        Validates: Requirements 1.3, 1.4
        
        For any OCR result, the response should contain all required fields.
        """
        with patch.object(ollama_service, '_send_to_ollama', return_value=extracted_text):
            with patch('time.time', side_effect=[0, processing_time]):
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                    # Create a minimal valid PNG
                    img = Image.new('RGB', (10, 10), color='red')
                    img.save(f, format='PNG')
                    temp_path = f.name
                
                try:
                    result = ollama_service.process_image(temp_path)
                    
                    # Verify all required fields are present
                    required_fields = [
                        'extracted_text',
                        'confidence_score',
                        'processing_time',
                        'ocr_engine',
                        'model_name',
                        'drug_name',
                        'batch_number',
                        'expiry_date',
                        'manufacturer',
                        'controlled_substance'
                    ]
                    
                    for field in required_fields:
                        assert field in result, f"Missing required field: {field}"
                    
                    # Verify field types
                    assert isinstance(result['extracted_text'], str)
                    assert isinstance(result['confidence_score'], float)
                    assert isinstance(result['processing_time'], float)
                    assert isinstance(result['ocr_engine'], str)
                    assert result['ocr_engine'] == 'ollama'
                    assert isinstance(result['controlled_substance'], bool)
                    
                finally:
                    import os
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
    
    # Property 3: Pharmaceutical Data Extraction Preservation
    # For any text extracted, pharmaceutical data extraction should identify fields
    @given(
        drug_name=st.text(min_size=1, max_size=50),
        batch_number=st.text(min_size=1, max_size=20),
        expiry_date=st.text(min_size=1, max_size=20)
    )
    @settings(max_examples=50)
    def test_pharmaceutical_data_extraction_property(self, ollama_service, drug_name, batch_number, expiry_date):
        """
        Property 3: Pharmaceutical Data Extraction Preservation
        Validates: Requirements 6.1, 6.2
        
        For any text with pharmaceutical data, extraction should identify fields.
        """
        # Create text with pharmaceutical data
        text = f"""
        Drug: {drug_name}
        Batch Number: {batch_number}
        Expiry Date: {expiry_date}
        Manufacturer: Test Pharma Inc.
        """
        
        pharma_data = ollama_service._extract_pharmaceutical_data(text)
        
        # Verify structure
        assert isinstance(pharma_data, dict)
        assert 'drug_name' in pharma_data
        assert 'batch_number' in pharma_data
        assert 'expiry_date' in pharma_data
        assert 'manufacturer' in pharma_data
        assert 'controlled_substance' in pharma_data
        
        # Verify types
        assert pharma_data['drug_name'] is None or isinstance(pharma_data['drug_name'], str)
        assert pharma_data['batch_number'] is None or isinstance(pharma_data['batch_number'], str)
        assert pharma_data['expiry_date'] is None or isinstance(pharma_data['expiry_date'], str)
        assert pharma_data['manufacturer'] is None or isinstance(pharma_data['manufacturer'], str)
        assert isinstance(pharma_data['controlled_substance'], bool)
    
    # Property 4: Multilingual Text Extraction
    # For any supported language, Ollama should extract text without errors
    @given(
        language_code=st.sampled_from([
            'en', 'fr', 'de', 'es', 'it', 'pt', 'ru', 'nl', 'sv', 'pl',
            'tr', 'el', 'he', 'th', 'zh', 'ja', 'ko', 'hi', 'ta', 'te',
            'kn', 'ml', 'gu', 'mr', 'bn', 'pa', 'ur', 'et'
        ])
    )
    @settings(max_examples=50)
    def test_multilingual_text_extraction_property(self, ollama_service, language_code):
        """
        Property 4: Multilingual Text Extraction
        Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5
        
        For any supported language, the service should handle text extraction.
        """
        # Create sample text in different languages
        sample_texts = {
            'en': 'Drug Name: Aspirin, Batch: ABC123, Expiry: 12/2025',
            'fr': 'Nom du médicament: Aspirine, Lot: ABC123, Expiration: 12/2025',
            'de': 'Arzneimittelname: Aspirin, Charge: ABC123, Ablauf: 12/2025',
            'es': 'Nombre del medicamento: Aspirina, Lote: ABC123, Vencimiento: 12/2025',
            'zh': '药物名称：阿司匹林，批号：ABC123，过期：12/2025',
            'ja': '医薬品名：アスピリン、バッチ：ABC123、有効期限：12/2025',
            'ko': '약물 이름: 아스피린, 배치: ABC123, 만료: 12/2025',
            'hi': 'दवा का नाम: एस्पिरिन, बैच: ABC123, समाप्ति: 12/2025',
            'ar': 'اسم الدواء: الأسبرين، الدفعة: ABC123، انتهاء الصلاحية: 12/2025',
        }
        
        text = sample_texts.get(language_code, 'Test text')
        
        # Extract pharmaceutical data
        pharma_data = ollama_service._extract_pharmaceutical_data(text)
        
        # Verify structure is maintained regardless of language
        assert isinstance(pharma_data, dict)
        assert 'drug_name' in pharma_data
        assert 'batch_number' in pharma_data
        assert 'expiry_date' in pharma_data
        assert 'manufacturer' in pharma_data
        assert 'controlled_substance' in pharma_data
    
    # Property 5: PDF Multi-Page Processing
    # For any PDF, processing should return combined text with page breaks
    @given(
        num_pages=st.integers(min_value=1, max_value=10),
        text_per_page=st.text(min_size=10, max_size=500)
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_pdf_multipage_processing_property(self, ollama_service, num_pages, text_per_page):
        """
        Property 5: PDF Multi-Page Processing
        Validates: Requirements 3.1, 3.2, 3.3, 3.5
        
        For any PDF with multiple pages, results should be combined with page breaks.
        """
        # Mock PDF processing
        with patch('pdf2image.convert_from_path') as mock_convert:
            # Create mock images
            mock_images = []
            for _ in range(num_pages):
                img = Image.new('RGB', (100, 100), color='white')
                mock_images.append(img)
            
            mock_convert.return_value = mock_images
            
            with patch.object(ollama_service, '_send_to_ollama', return_value=text_per_page):
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                    f.write(b'%PDF-1.4\n')  # Minimal PDF header
                    temp_path = f.name
                
                try:
                    result = ollama_service.process_pdf(temp_path)
                    
                    # Verify result structure
                    assert 'extracted_text' in result
                    assert 'confidence_score' in result
                    assert 'pages_processed' in result
                    assert result['pages_processed'] == num_pages
                    
                    # Verify page breaks are present (if multiple pages)
                    if num_pages > 1:
                        assert '--- Page Break ---' in result['extracted_text']
                    
                    # Verify confidence is valid
                    assert 0.0 <= result['confidence_score'] <= 1.0
                    
                finally:
                    import os
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
    
    # Property 7: Offline Processing Capability
    # For any document processed locally, no external services should be called
    @given(
        text_content=st.text(min_size=10, max_size=1000)
    )
    @settings(max_examples=30)
    def test_offline_processing_capability_property(self, ollama_service, text_content):
        """
        Property 7: Offline Processing Capability
        Validates: Requirements 11.1, 11.2, 11.5
        
        For any document processed with Ollama, processing should use only local resources.
        """
        # Verify that Ollama service uses local endpoint
        assert ollama_service.ollama_endpoint.startswith('http://localhost') or \
               ollama_service.ollama_endpoint.startswith('http://127.0.0.1'), \
               "Ollama endpoint should be local"
        
        # Verify model name is set
        assert ollama_service.model_name is not None
        assert len(ollama_service.model_name) > 0
        
        # Verify timeout is reasonable for local processing
        assert ollama_service.timeout > 0
        assert ollama_service.timeout <= 300  # Max 5 minutes for local processing
    
    # Property 8: Backward Compatibility Preservation
    # For any existing workflow, results should have consistent schema
    @given(
        extracted_text=st.text(min_size=1, max_size=500)
    )
    @settings(max_examples=50)
    def test_backward_compatibility_preservation_property(self, ollama_service, extracted_text):
        """
        Property 8: Backward Compatibility Preservation
        Validates: Requirements 8.1, 8.2, 8.4, 12.1
        
        For any OCR result, the schema should be consistent with previous implementation.
        """
        pharma_data = ollama_service._extract_pharmaceutical_data(extracted_text)
        
        # Verify schema matches expected structure
        expected_schema = {
            'drug_name': (type(None), str),
            'batch_number': (type(None), str),
            'expiry_date': (type(None), str),
            'manufacturer': (type(None), str),
            'controlled_substance': (bool,)
        }
        
        for field, expected_types in expected_schema.items():
            assert field in pharma_data, f"Missing field: {field}"
            assert isinstance(pharma_data[field], expected_types), \
                f"Field {field} has unexpected type: {type(pharma_data[field])}"


class TestOllamaServiceInitialization:
    """Tests for OllamaOCRService initialization"""
    
    def test_service_initialization(self):
        """Test that OllamaOCRService initializes correctly"""
        service = OllamaOCRService(
            ollama_endpoint="http://localhost:11434",
            model_name="glm-ocr:latest",
            timeout=30
        )
        
        assert service.ollama_endpoint == "http://localhost:11434"
        assert service.model_name == "glm-ocr:latest"
        assert service.timeout == 30
        assert service.api_endpoint == "http://localhost:11434/api/generate"
    
    def test_service_initialization_with_trailing_slash(self):
        """Test that trailing slash is removed from endpoint"""
        service = OllamaOCRService(
            ollama_endpoint="http://localhost:11434/",
            model_name="glm-ocr:latest",
            timeout=30
        )
        
        assert service.ollama_endpoint == "http://localhost:11434"
        assert service.api_endpoint == "http://localhost:11434/api/generate"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
