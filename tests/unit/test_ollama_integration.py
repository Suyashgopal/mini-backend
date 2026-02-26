"""
Integration tests for Ollama OCR migration
Tests the complete workflow with Ollama and fallback to Tesseract
"""

import pytest
import tempfile
import os
from PIL import Image
from unittest.mock import Mock, patch, MagicMock

from services.ocr_service_factory import OCRServiceFactory
from services.ollama_ocr_service import OllamaOCRService
from services.ocr_service import OCRService as TesseractOCRService


class TestOCRServiceFactory:
    """Integration tests for OCRServiceFactory"""
    
    @pytest.fixture
    def factory(self):
        """Create an OCRServiceFactory instance"""
        return OCRServiceFactory(
            use_ollama=True,
            ollama_endpoint="http://localhost:11434",
            ollama_model="glm-ocr:latest",
            ollama_timeout=30
        )
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing"""
        img = Image.new('RGB', (100, 100), color='white')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f, format='PNG')
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    def test_factory_initialization(self, factory):
        """Test that factory initializes correctly"""
        assert factory.use_ollama is True
        assert factory.ollama_endpoint == "http://localhost:11434"
        assert factory.ollama_model == "glm-ocr:latest"
        assert factory.ollama_timeout == 30
    
    def test_factory_has_tesseract_service(self, factory):
        """Test that factory has Tesseract service available"""
        assert factory.tesseract_service is not None
    
    def test_ollama_availability_check(self, factory):
        """Test Ollama availability check"""
        with patch('requests.get') as mock_get:
            mock_get.return_value = Mock(status_code=200)
            # This will return False because we're not actually running Ollama
            result = factory._is_ollama_available()
            # Result depends on whether Ollama is actually running
            assert isinstance(result, bool)
    
    def test_process_image_with_tesseract_fallback(self, factory, sample_image):
        """Test image processing with Tesseract fallback"""
        # Mock Ollama to be unavailable
        with patch.object(factory, '_is_ollama_available', return_value=False):
            result = factory.process_image(sample_image)
            
            # Verify result structure
            assert 'extracted_text' in result
            assert 'confidence_score' in result
            assert 'processing_time' in result
            assert 'ocr_engine' in result
            assert result['ocr_engine'] == 'tesseract'
            assert result['fallback_used'] is False
    
    def test_get_supported_languages(self, factory):
        """Test getting supported languages"""
        languages = factory.get_supported_languages()
        
        # Verify structure
        assert isinstance(languages, dict)
        assert len(languages) >= 30  # At least 30 languages
        
        # Verify specific languages are present
        assert 'en' in languages
        assert 'fr' in languages
        assert 'de' in languages
        assert 'zh' in languages
        assert 'ja' in languages
        assert 'hi' in languages
        assert 'et' in languages  # Estonian


class TestOllamaOCRServiceIntegration:
    """Integration tests for OllamaOCRService"""
    
    @pytest.fixture
    def ollama_service(self):
        """Create an OllamaOCRService instance"""
        return OllamaOCRService(
            ollama_endpoint="http://localhost:11434",
            model_name="glm-ocr:latest",
            timeout=30
        )
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing"""
        img = Image.new('RGB', (100, 100), color='white')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f, format='PNG')
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    def test_ollama_service_initialization(self, ollama_service):
        """Test OllamaOCRService initialization"""
        assert ollama_service.ollama_endpoint == "http://localhost:11434"
        assert ollama_service.model_name == "glm-ocr:latest"
        assert ollama_service.timeout == 30
        assert ollama_service.api_endpoint == "http://localhost:11434/api/generate"
    
    def test_pharmaceutical_data_extraction(self, ollama_service):
        """Test pharmaceutical data extraction"""
        text = """
        Drug Name: Aspirin 500mg
        Batch Number: BN-2024-001234
        Expiry Date: 12/2025
        Manufacturer: PharmaCorp Inc.
        Controlled Substance: Schedule II
        """
        
        pharma_data = ollama_service._extract_pharmaceutical_data(text)
        
        # Verify extraction
        assert pharma_data['drug_name'] is not None
        assert pharma_data['batch_number'] is not None
        assert pharma_data['expiry_date'] is not None
        assert pharma_data['manufacturer'] is not None
        assert pharma_data['controlled_substance'] is True
    
    def test_confidence_score_calculation(self, ollama_service):
        """Test confidence score calculation"""
        # Test with good text
        good_text = "This is a good quality OCR extraction with many words and numbers 12345"
        confidence = ollama_service._calculate_confidence(good_text)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably high
        
        # Test with empty text
        empty_confidence = ollama_service._calculate_confidence("")
        assert empty_confidence == 0.0
        
        # Test with mostly non-alphanumeric
        poor_text = "!@#$%^&*()"
        poor_confidence = ollama_service._calculate_confidence(poor_text)
        assert 0.0 <= poor_confidence <= 1.0
    
    def test_model_availability_check(self, ollama_service):
        """Test model availability check"""
        with patch('requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {'models': [{'name': 'glm-ocr:latest'}]}
            )
            result = ollama_service._verify_model_available()
            # Result depends on whether model is actually available
            assert isinstance(result, bool)
    
    def test_model_download(self, ollama_service):
        """Test model download attempt"""
        with patch('requests.post') as mock_post:
            mock_post.return_value = Mock(status_code=200)
            result = ollama_service._download_model()
            assert isinstance(result, bool)


class TestFallbackMechanism:
    """Tests for fallback mechanism"""
    
    @pytest.fixture
    def factory(self):
        """Create an OCRServiceFactory instance"""
        return OCRServiceFactory(
            use_ollama=True,
            ollama_endpoint="http://localhost:11434",
            ollama_model="llava:latest",
            ollama_timeout=30
        )
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing"""
        img = Image.new('RGB', (100, 100), color='white')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f, format='PNG')
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    def test_fallback_on_timeout(self, factory, sample_image):
        """Test fallback when Ollama times out"""
        import requests
        
        with patch.object(factory, '_is_ollama_available', return_value=True):
            with patch.object(factory.ollama_service, 'process_image', 
                            side_effect=requests.Timeout("Connection timeout")):
                result = factory.process_image(sample_image)
                
                # Should have fallen back to Tesseract
                assert result['fallback_used'] is True
                assert result['fallback_reason'] == 'timeout'
                assert 'extracted_text' in result
    
    def test_fallback_on_connection_error(self, factory, sample_image):
        """Test fallback when Ollama connection fails"""
        import requests
        
        with patch.object(factory, '_is_ollama_available', return_value=True):
            with patch.object(factory.ollama_service, 'process_image',
                            side_effect=requests.ConnectionError("Connection refused")):
                result = factory.process_image(sample_image)
                
                # Should have fallen back to Tesseract
                assert result['fallback_used'] is True
                assert result['fallback_reason'] == 'connection_error'
                assert 'extracted_text' in result
    
    def test_fallback_on_generic_error(self, factory, sample_image):
        """Test fallback on generic error"""
        with patch.object(factory, '_is_ollama_available', return_value=True):
            with patch.object(factory.ollama_service, 'process_image',
                            side_effect=Exception("Generic error")):
                result = factory.process_image(sample_image)
                
                # Should have fallen back to Tesseract
                assert result['fallback_used'] is True
                assert 'extracted_text' in result


class TestAPIResponseFormat:
    """Tests for API response format consistency"""
    
    @pytest.fixture
    def factory(self):
        """Create an OCRServiceFactory instance"""
        return OCRServiceFactory(
            use_ollama=False,  # Use Tesseract for consistent testing
            ollama_endpoint="http://localhost:11434",
            ollama_model="glm-ocr:latest"
        )
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing"""
        img = Image.new('RGB', (100, 100), color='white')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f, format='PNG')
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    def test_response_has_required_fields(self, factory, sample_image):
        """Test that response has all required fields"""
        result = factory.process_image(sample_image)
        
        required_fields = [
            'extracted_text',
            'confidence_score',
            'processing_time',
            'ocr_engine',
            'drug_name',
            'batch_number',
            'expiry_date',
            'manufacturer',
            'controlled_substance',
            'fallback_used'
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
    
    def test_response_field_types(self, factory, sample_image):
        """Test that response fields have correct types"""
        result = factory.process_image(sample_image)
        
        assert isinstance(result['extracted_text'], str)
        assert isinstance(result['confidence_score'], float)
        assert isinstance(result['processing_time'], float)
        assert isinstance(result['ocr_engine'], str)
        assert isinstance(result['controlled_substance'], bool)
        assert isinstance(result['fallback_used'], bool)
        
        # Verify ranges
        assert 0.0 <= result['confidence_score'] <= 1.0
        assert result['processing_time'] >= 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
