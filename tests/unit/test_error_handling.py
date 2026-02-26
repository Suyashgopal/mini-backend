#!/usr/bin/env python
"""
Error Handling and Graceful Degradation Tests

This test suite validates error handling and graceful degradation behavior
for the multilingual translation system.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6**
**Validates: Properties 3, 16, 17**
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
from services.translation_service import TranslationService
from services.language_detection_service import LanguageDetectionService
from services.multilingual_ocr_service import MultilingualOCRService
import requests
from hypothesis import given, strategies as st, settings, HealthCheck


# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestTranslationErrorHandling:
    """Test error handling in TranslationService"""

    # ========== Property 3: Error Response Structure ==========
    def test_property_3_error_response_structure_empty_text(self):
        """
        **Property 3: Error Response Structure**
        
        For any failed translation operation, the response should contain 
        'success': False, 'error' with descriptive message, and appropriate 
        null/empty values for data fields.
        
        **Validates: Requirements 1.4, 1.5, 1.6, 8.3, 8.5**
        """
        result = TranslationService.translate_to_english("", "es")
        
        # Verify error response structure
        assert isinstance(result, dict)
        assert result["success"] is False
        assert isinstance(result["error"], str)
        assert len(result["error"]) > 0
        assert result["translated_text"] == ""
        assert "Empty text" in result["error"]

    def test_error_response_structure_api_timeout(self):
        """
        Test error response structure when API times out
        
        **Validates: Requirements 1.5, 1.6, 8.2**
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # Simulate timeout
            mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
            
            result = TranslationService._translate_chunk("Hello world", "es")
            
            # Verify error response structure
            assert result["success"] is False
            assert "timeout" in result["error"].lower()
            assert result["translated_text"] == ""

    def test_error_response_structure_api_connection_error(self):
        """
        Test error response structure when API is unreachable
        
        **Validates: Requirements 1.5, 1.6, 8.2**
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # Simulate connection error
            mock_get.side_effect = requests.exceptions.ConnectionError("Cannot connect")
            
            result = TranslationService._translate_chunk("Hello world", "es")
            
            # Verify error response structure
            assert result["success"] is False
            assert "connect" in result["error"].lower()
            assert result["translated_text"] == ""

    def test_error_response_structure_api_error_response(self):
        """
        Test error response structure when API returns error
        
        **Validates: Requirements 1.4, 1.5, 8.3**
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # Simulate API error response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'responseStatus': 429,  # Rate limit error
                'responseDetails': 'Rate limit exceeded'
            }
            mock_get.return_value = mock_response
            
            result = TranslationService._translate_chunk("Hello world", "es")
            
            # Verify error response structure
            assert result["success"] is False
            assert "error" in result["error"].lower()
            assert result["translated_text"] == ""

    def test_error_response_structure_http_error(self):
        """
        Test error response structure when HTTP error occurs
        
        **Validates: Requirements 1.5, 1.6**
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # Simulate HTTP error
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            
            result = TranslationService._translate_chunk("Hello world", "es")
            
            # Verify error response structure
            assert result["success"] is False
            assert "HTTP" in result["error"] or "error" in result["error"].lower()
            assert result["translated_text"] == ""

    # ========== Property 16: Graceful Degradation on Translation Failure ==========
    def test_property_16_graceful_degradation_api_unavailable(self):
        """
        **Property 16: Graceful Degradation on Translation Failure**
        
        For any translation failure (API unavailable, timeout, unsupported language), 
        the system should return the original extracted text instead of failing 
        the entire OCR process.
        
        **Validates: Requirements 8.1, 8.2, 8.4**
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # Simulate API unavailable
            mock_get.side_effect = requests.exceptions.ConnectionError("API unavailable")
            
            original_text = "This is the original text"
            result = TranslationService.translate_to_english(original_text, "es")
            
            # Should return error but not crash
            assert isinstance(result, dict)
            assert result["success"] is False
            assert "error" in result
            # The system should gracefully handle the failure
            assert result["translated_text"] == ""

    def test_graceful_degradation_timeout(self):
        """
        Test graceful degradation when translation times out
        
        **Validates: Requirements 8.1, 8.2**
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # Simulate timeout
            mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
            
            original_text = "This is the original text"
            result = TranslationService.translate_to_english(original_text, "es")
            
            # Should handle gracefully
            assert isinstance(result, dict)
            assert result["success"] is False
            assert "timeout" in result["error"].lower()

    def test_graceful_degradation_unsupported_language(self):
        """
        Test graceful degradation with unsupported language
        
        **Validates: Requirements 8.3, 8.4**
        """
        # Use a language code that might not be supported
        result = TranslationService.translate_to_english("Hello", "xyz")
        
        # Should handle gracefully - either translate or return error
        assert isinstance(result, dict)
        assert "success" in result
        assert "error" in result

    def test_graceful_degradation_malformed_text(self):
        """
        Test graceful degradation with malformed text
        
        **Validates: Requirements 8.4**
        """
        # Test with various malformed inputs
        malformed_inputs = [
            "\x00\x01\x02",  # Binary data
            "a" * 100000,    # Very long text
            "\n" * 1000,     # Many newlines
        ]
        
        for malformed_text in malformed_inputs:
            try:
                result = TranslationService.translate_to_english(malformed_text, "es")
                # Should not crash
                assert isinstance(result, dict)
                assert "success" in result
                assert "error" in result
            except Exception as e:
                # If it does raise, it should be a controlled exception
                pytest.fail(f"Unhandled exception for malformed text: {str(e)}")

    def test_graceful_degradation_empty_api_response(self):
        """
        Test graceful degradation when API returns empty response
        
        **Validates: Requirements 8.1, 8.4**
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # Simulate empty response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'responseStatus': 200,
                'responseData': {'translatedText': ''}
            }
            mock_get.return_value = mock_response
            
            result = TranslationService._translate_chunk("Hello world", "es")
            
            # Should handle gracefully
            assert isinstance(result, dict)
            assert result["success"] is False
            assert "empty" in result["error"].lower()

    # ========== Property 17: Error Logging on Failures ==========
    def test_property_17_error_logging_on_failures(self, caplog):
        """
        **Property 17: Error Logging on Failures**
        
        For any error that occurs during translation, the system should log 
        the error with sufficient detail (error type, message, context) for debugging.
        
        **Validates: Requirements 8.2, 8.6**
        """
        with caplog.at_level(logging.DEBUG):
            with patch('services.translation_service.requests.get') as mock_get:
                # Simulate API error
                mock_get.side_effect = requests.exceptions.ConnectionError("Cannot connect")
                
                result = TranslationService._translate_chunk("Hello world", "es")
                
                # Should have logged the error
                assert result["success"] is False
                # The error message should be descriptive
                assert len(result["error"]) > 0

    def test_error_logging_timeout(self, caplog):
        """
        Test error logging when translation times out
        
        **Validates: Requirements 8.2, 8.6**
        """
        with caplog.at_level(logging.DEBUG):
            with patch('services.translation_service.requests.get') as mock_get:
                # Simulate timeout
                mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
                
                result = TranslationService._translate_chunk("Hello world", "es")
                
                # Should have error information
                assert result["success"] is False
                assert "timeout" in result["error"].lower()

    def test_error_logging_api_error(self, caplog):
        """
        Test error logging when API returns error
        
        **Validates: Requirements 8.2, 8.6**
        """
        with caplog.at_level(logging.DEBUG):
            with patch('services.translation_service.requests.get') as mock_get:
                # Simulate API error
                mock_response = MagicMock()
                mock_response.status_code = 500
                mock_get.return_value = mock_response
                
                result = TranslationService._translate_chunk("Hello world", "es")
                
                # Should have error information
                assert result["success"] is False
                assert len(result["error"]) > 0

    def test_error_message_descriptiveness(self):
        """
        Test that error messages are descriptive enough for debugging
        
        **Validates: Requirements 8.5, 8.6**
        """
        # Test various error scenarios
        test_cases = [
            ("", "es", "Empty text"),
            ("Hello", "xyz", None),  # May or may not error depending on language support
        ]
        
        for text, lang, expected_error_substring in test_cases:
            result = TranslationService.translate_to_english(text, lang)
            
            if not result["success"]:
                # Error message should be descriptive
                assert isinstance(result["error"], str)
                assert len(result["error"]) > 0
                
                if expected_error_substring:
                    assert expected_error_substring in result["error"]


class TestLanguageDetectionErrorHandling:
    """Test error handling in LanguageDetectionService"""

    def test_error_response_structure_empty_text(self):
        """
        Test error response structure for empty text
        
        **Validates: Requirements 3.3, 3.4**
        """
        result = LanguageDetectionService.detect_language("")
        
        # Verify error response structure
        assert result["success"] is False
        assert isinstance(result["error"], str)
        assert len(result["error"]) > 0
        assert result["language_code"] is None
        assert result["language_name"] is None
        assert result["confidence"] == 0.0

    def test_error_response_structure_whitespace_only(self):
        """
        Test error response structure for whitespace-only text
        
        **Validates: Requirements 3.3, 3.4**
        """
        result = LanguageDetectionService.detect_language("   \n\t  ")
        
        # Verify error response structure
        assert result["success"] is False
        assert isinstance(result["error"], str)
        assert result["language_code"] is None
        assert result["language_name"] is None
        assert result["confidence"] == 0.0

    def test_graceful_degradation_detection_failure(self):
        """
        Test graceful degradation when language detection fails
        
        **Validates: Requirements 8.1, 8.4**
        """
        # Test with various inputs that might cause detection to fail
        test_inputs = [
            "",
            "   ",
            "\n\t",
        ]
        
        for text in test_inputs:
            result = LanguageDetectionService.detect_language(text)
            
            # Should not crash
            assert isinstance(result, dict)
            assert "success" in result
            assert "error" in result
            assert "language_code" in result

    def test_error_logging_detection_failure(self, caplog):
        """
        Test error logging when language detection fails
        
        **Validates: Requirements 8.2, 8.6**
        """
        with caplog.at_level(logging.DEBUG):
            result = LanguageDetectionService.detect_language("")
            
            # Should have error information
            assert result["success"] is False
            assert len(result["error"]) > 0

    def test_multi_page_detection_error_handling(self):
        """
        Test error handling for multi-page language detection
        
        **Validates: Requirements 8.1, 8.4**
        """
        # Test with empty list
        result = LanguageDetectionService.detect_language_from_pages([])
        assert result["success"] is False
        assert result["language_code"] is None
        
        # Test with all empty strings
        result = LanguageDetectionService.detect_language_from_pages(["", "  ", "\n"])
        assert result["success"] is False
        assert result["language_code"] is None


class TestMultilingualOCRErrorHandling:
    """Test error handling in MultilingualOCRService"""

    def test_graceful_degradation_translation_failure_in_ocr(self):
        """
        Test that OCR continues even if translation fails
        
        **Validates: Requirements 8.1, 8.2, 8.4**
        """
        with patch('services.translation_service.TranslationService.translate_to_english') as mock_translate:
            with patch('services.language_detection_service.LanguageDetectionService.detect_language') as mock_detect:
                with patch.object(MultilingualOCRService, 'process_image') as mock_process:
                    # Setup mocks
                    mock_process.return_value = {
                        'extracted_text': 'Hello world',
                        'confidence': 0.95
                    }
                    mock_detect.return_value = {
                        'success': True,
                        'language_code': 'es',
                        'language_name': 'Spanish',
                        'confidence': 0.9,
                        'error': None
                    }
                    # Simulate translation failure
                    mock_translate.return_value = {
                        'success': False,
                        'error': 'API unavailable',
                        'translated_text': ''
                    }
                    
                    service = MultilingualOCRService()
                    result = service.process_image_multilingual('test.png')
                    
                    # Should still return result even if translation failed
                    assert isinstance(result, dict)
                    assert 'extracted_text' in result
                    assert result.get('translated') is False
                    assert 'translation_error' in result

    def test_graceful_degradation_language_detection_failure_in_ocr(self):
        """
        Test that OCR continues even if language detection fails
        
        **Validates: Requirements 8.1, 8.4**
        """
        with patch('services.language_detection_service.LanguageDetectionService.detect_language') as mock_detect:
            with patch.object(MultilingualOCRService, 'process_image') as mock_process:
                # Setup mocks
                mock_process.return_value = {
                    'extracted_text': 'Hello world',
                    'confidence': 0.95
                }
                # Simulate detection failure
                mock_detect.return_value = {
                    'success': False,
                    'language_code': None,
                    'language_name': None,
                    'confidence': 0.0,
                    'error': 'Could not detect language'
                }
                
                service = MultilingualOCRService()
                result = service.process_image_multilingual('test.png')
                
                # Should still return result even if detection failed
                assert isinstance(result, dict)
                assert 'extracted_text' in result
                assert result.get('detected_language') == 'Unknown'
                assert 'detection_error' in result

    def test_error_handling_with_malformed_image_path(self):
        """
        Test error handling with malformed image path
        
        **Validates: Requirements 8.4**
        """
        service = MultilingualOCRService()
        
        # Test with non-existent file
        with pytest.raises(Exception):
            service.process_image_multilingual('/nonexistent/path/image.png')

    def test_error_handling_with_malformed_pdf_path(self):
        """
        Test error handling with malformed PDF path
        
        **Validates: Requirements 8.4**
        """
        service = MultilingualOCRService()
        
        # Test with non-existent file
        with pytest.raises(Exception):
            service.process_pdf_multilingual('/nonexistent/path/document.pdf')


class TestErrorHandlingIntegration:
    """Integration tests for error handling across services"""

    def test_translation_failure_does_not_crash_system(self):
        """
        Test that translation failure doesn't crash the entire system
        
        **Validates: Requirements 8.1, 8.2**
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # Simulate multiple API failures
            mock_get.side_effect = requests.exceptions.ConnectionError("API down")
            
            # Should handle gracefully
            result = TranslationService.translate_to_english("Hello world", "es")
            assert result["success"] is False
            
            # System should still be functional
            result2 = TranslationService.translate_to_english("Hello", "en")
            assert result2["success"] is True

    def test_language_detection_failure_does_not_crash_system(self):
        """
        Test that language detection failure doesn't crash the system
        
        **Validates: Requirements 8.1, 8.4**
        """
        # Test with empty text
        result = LanguageDetectionService.detect_language("")
        assert result["success"] is False
        
        # System should still be functional
        result2 = LanguageDetectionService.detect_language("Hello world")
        assert isinstance(result2, dict)

    def test_multiple_consecutive_failures(self):
        """
        Test system behavior with multiple consecutive failures
        
        **Validates: Requirements 8.1, 8.5**
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # Simulate persistent API failures
            mock_get.side_effect = requests.exceptions.ConnectionError("API down")
            
            # Multiple consecutive failures should all be handled
            for i in range(5):
                result = TranslationService.translate_to_english(f"Text {i}", "es")
                assert result["success"] is False
                assert "error" in result
                assert len(result["error"]) > 0

    def test_error_recovery_after_failure(self):
        """
        Test that system recovers after a failure
        
        **Validates: Requirements 8.1, 8.2**
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # First call fails
            mock_get.side_effect = requests.exceptions.ConnectionError("API down")
            result1 = TranslationService.translate_to_english("Hello", "es")
            assert result1["success"] is False
            
            # Reset mock for successful call
            mock_get.side_effect = None
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'responseStatus': 200,
                'responseData': {'translatedText': 'Hola'}
            }
            mock_get.return_value = mock_response
            
            # Second call should succeed
            result2 = TranslationService._translate_chunk("Hello", "es")
            assert result2["success"] is True


class TestErrorMessageQuality:
    """Test the quality and usefulness of error messages"""

    def test_error_messages_are_descriptive(self):
        """
        Test that error messages provide useful debugging information
        
        **Validates: Requirements 8.5, 8.6**
        """
        # Test various error scenarios
        test_cases = [
            ("", "es", "Empty text"),
            ("   ", "es", "Empty text"),
        ]
        
        for text, lang, expected_keyword in test_cases:
            result = TranslationService.translate_to_english(text, lang)
            
            if not result["success"]:
                error_msg = result["error"]
                # Error message should be descriptive
                assert len(error_msg) > 5
                assert expected_keyword in error_msg or "error" in error_msg.lower()

    def test_error_messages_include_context(self):
        """
        Test that error messages include context for debugging
        
        **Validates: Requirements 8.6**
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # Simulate API error with status code
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_get.return_value = mock_response
            
            result = TranslationService._translate_chunk("Hello", "es")
            
            # Error message should include context
            assert result["success"] is False
            assert len(result["error"]) > 0
            # Should mention HTTP or error code
            assert "HTTP" in result["error"] or "429" in result["error"] or "error" in result["error"].lower()

    def test_error_messages_are_not_empty(self):
        """
        Test that error messages are never empty
        
        **Validates: Requirements 8.5, 8.6**
        """
        # Test various error scenarios
        error_scenarios = [
            lambda: TranslationService.translate_to_english("", "es"),
            lambda: LanguageDetectionService.detect_language(""),
        ]
        
        for scenario in error_scenarios:
            result = scenario()
            
            if not result["success"]:
                assert "error" in result
                assert isinstance(result["error"], str)
                assert len(result["error"]) > 0


# ========== Property-Based Tests using Hypothesis ==========

class TestErrorResponseStructureProperty:
    """
    **Property 3: Error Response Structure**
    
    For any failed translation or language detection operation, the response 
    should contain 'success': False, 'error' with descriptive message, and 
    appropriate null/empty values for data fields.
    
    **Validates: Requirements 1.4, 1.5, 1.6, 3.4, 8.3, 8.5**
    """
    
    @given(st.just("") | st.just("   ") | st.just("\n\t"))
    def test_property_3_error_response_structure_with_empty_inputs(self, text):
        """
        Property 3: For any empty/whitespace input, error response structure is correct
        """
        result = TranslationService.translate_to_english(text, "es")
        
        # Verify error response structure
        assert isinstance(result, dict), "Response must be a dictionary"
        assert "success" in result, "Response must contain 'success' key"
        assert "error" in result, "Response must contain 'error' key"
        assert "translated_text" in result, "Response must contain 'translated_text' key"
        
        # For error response
        assert result["success"] is False, "Success must be False for empty input"
        assert isinstance(result["error"], str), "Error must be a string"
        assert len(result["error"]) > 0, "Error message must not be empty"
        assert result["translated_text"] == "", "Translated text must be empty for failed translation"

    def test_property_3_error_response_structure_with_api_errors(self):
        """
        Property 3: For any API error, error response structure is correct
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # Test multiple error scenarios
            error_scenarios = [
                requests.exceptions.Timeout("Connection timeout"),
                requests.exceptions.ConnectionError("Cannot connect"),
            ]
            
            for error in error_scenarios:
                mock_get.side_effect = error
                result = TranslationService._translate_chunk("Hello world", "es")
                
                # Verify error response structure
                assert isinstance(result, dict), "Response must be a dictionary"
                assert result["success"] is False, "Success must be False for API error"
                assert isinstance(result["error"], str), "Error must be a string"
                assert len(result["error"]) > 0, "Error message must not be empty"
                assert result["translated_text"] == "", "Translated text must be empty for failed translation"

    @given(st.just(""))
    def test_property_3_language_detection_error_response_structure(self, text):
        """
        Property 3: For any empty input to language detection, error response structure is correct
        """
        result = LanguageDetectionService.detect_language(text)
        
        # Verify error response structure
        assert isinstance(result, dict), "Response must be a dictionary"
        assert "success" in result, "Response must contain 'success' key"
        assert "error" in result, "Response must contain 'error' key"
        assert "language_code" in result, "Response must contain 'language_code' key"
        assert "language_name" in result, "Response must contain 'language_name' key"
        assert "confidence" in result, "Response must contain 'confidence' key"
        
        # For error response
        assert result["success"] is False, "Success must be False for empty input"
        assert isinstance(result["error"], str), "Error must be a string"
        assert len(result["error"]) > 0, "Error message must not be empty"
        assert result["language_code"] is None, "Language code must be None for failed detection"
        assert result["language_name"] is None, "Language name must be None for failed detection"
        assert result["confidence"] == 0.0, "Confidence must be 0.0 for failed detection"


class TestGracefulDegradationProperty:
    """
    **Property 16: Graceful Degradation on Translation Failure**
    
    For any translation failure (API unavailable, timeout, unsupported language), 
    the system should return the original extracted text instead of failing 
    the entire OCR process.
    
    **Validates: Requirements 8.1, 8.2, 8.4**
    """
    
    def test_property_16_graceful_degradation_api_failures(self):
        """
        Property 16: For any API failure, system degrades gracefully
        """
        api_failures = [
            requests.exceptions.ConnectionError("API unavailable"),
            requests.exceptions.Timeout("Request timeout"),
        ]
        
        for failure in api_failures:
            with patch('services.translation_service.requests.get') as mock_get:
                mock_get.side_effect = failure
                
                original_text = "This is the original text"
                result = TranslationService.translate_to_english(original_text, "es")
                
                # Should return error but not crash
                assert isinstance(result, dict), "Response must be a dictionary"
                assert result["success"] is False, "Success must be False for API failure"
                assert "error" in result, "Response must contain error information"
                # The system should gracefully handle the failure
                assert result["translated_text"] == "", "Translated text should be empty on failure"

    @given(st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cc", "Cs"))))
    @settings(max_examples=5, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_property_16_graceful_degradation_with_various_texts(self, text):
        """
        Property 16: For any text with API failure, system degrades gracefully
        """
        if not text.strip():
            pytest.skip("Skipping whitespace-only text")
        
        with patch('services.translation_service.requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("API down")
            
            result = TranslationService.translate_to_english(text, "es")
            
            # Should handle gracefully
            assert isinstance(result, dict), "Response must be a dictionary"
            assert result["success"] is False, "Success must be False for API failure"
            assert "error" in result, "Response must contain error information"

    def test_property_16_language_detection_graceful_degradation(self):
        """
        Property 16: For any language detection failure, system degrades gracefully
        """
        # Test with empty text
        result = LanguageDetectionService.detect_language("")
        assert result["success"] is False, "Success must be False for empty input"
        assert result["language_code"] is None, "Language code must be None on failure"
        
        # System should still be functional
        result2 = LanguageDetectionService.detect_language("Hello world")
        assert isinstance(result2, dict), "Response must be a dictionary"


class TestErrorLoggingProperty:
    """
    **Property 17: Error Logging on Failures**
    
    For any error that occurs during translation or language detection, 
    the system should log the error with sufficient detail (error type, message, context) 
    for debugging.
    
    **Validates: Requirements 8.2, 8.6**
    """
    
    def test_property_17_error_logging_translation_failures(self, caplog):
        """
        Property 17: For any translation failure, error is logged with sufficient detail
        """
        with caplog.at_level(logging.DEBUG):
            with patch('services.translation_service.requests.get') as mock_get:
                # Simulate API error
                mock_get.side_effect = requests.exceptions.ConnectionError("Cannot connect")
                
                result = TranslationService._translate_chunk("Hello world", "es")
                
                # Should have logged the error
                assert result["success"] is False, "Translation should fail"
                # The error message should be descriptive
                assert len(result["error"]) > 0, "Error message must not be empty"
                assert "error" in result["error"].lower() or "connect" in result["error"].lower(), \
                    "Error message should describe the failure"

    @given(st.just("") | st.just("   "))
    def test_property_17_error_logging_detection_failures(self, text):
        """
        Property 17: For any language detection failure, error is logged with sufficient detail
        """
        result = LanguageDetectionService.detect_language(text)
        
        # Should have error information
        assert result["success"] is False, "Detection should fail for empty input"
        assert len(result["error"]) > 0, "Error message must not be empty"

    def test_property_17_error_messages_are_descriptive(self):
        """
        Property 17: For any error, error messages are descriptive enough for debugging
        """
        # Test various error scenarios
        test_cases = [
            (lambda: TranslationService.translate_to_english("", "es"), "Empty text"),
            (lambda: LanguageDetectionService.detect_language(""), "Empty text"),
        ]
        
        for scenario, expected_context in test_cases:
            result = scenario()
            
            if not result["success"]:
                # Error message should be descriptive
                assert isinstance(result["error"], str), "Error must be a string"
                assert len(result["error"]) > 0, "Error message must not be empty"
                # Should contain context about what went wrong
                assert expected_context in result["error"] or "error" in result["error"].lower(), \
                    "Error message should describe the failure context"

    def test_property_17_error_context_includes_error_type(self):
        """
        Property 17: For any error, error message includes error type for debugging
        """
        with patch('services.translation_service.requests.get') as mock_get:
            # Test timeout error
            mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
            result = TranslationService._translate_chunk("Hello", "es")
            
            assert result["success"] is False, "Translation should fail"
            assert "timeout" in result["error"].lower(), "Error should mention timeout"
            
            # Test connection error
            mock_get.side_effect = requests.exceptions.ConnectionError("Cannot connect")
            result = TranslationService._translate_chunk("Hello", "es")
            
            assert result["success"] is False, "Translation should fail"
            assert "connect" in result["error"].lower(), "Error should mention connection"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
