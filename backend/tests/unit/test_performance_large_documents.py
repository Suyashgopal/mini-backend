#!/usr/bin/env python
"""
Performance tests for large document processing.

This test suite validates the performance characteristics of the multilingual
translation system when processing large documents (100+ pages).

**Validates: Requirements 1.1, 3.1**

Test Coverage:
- Translation of 100+ page PDFs
- Language detection with large documents
- Response time verification
- Memory usage verification
"""

import pytest
import time
import psutil
import os
from unittest.mock import Mock, patch, MagicMock
from services.translation_service import TranslationService
from services.language_detection_service import LanguageDetectionService
from services.multilingual_ocr_service import MultilingualOCRService


class TestLargeDocumentPerformance:
    """Performance tests for large document processing"""

    def test_translation_100_page_pdf_simulation(self):
        """
        Test translation of 100+ page PDFs.
        
        Simulates processing a 100-page PDF document with translation.
        Verifies that the system can handle large documents without
        crashing or excessive delays.
        
        **Validates: Requirement 1.1**
        """
        # Simulate 100 pages of text (each page ~500 characters)
        page_text = "Drug Name: Aspirin. Batch Number: ABC123. Expiry Date: 2025-12-31. " * 7
        pages = [page_text for _ in range(100)]
        
        # Measure translation time
        start_time = time.time()
        
        # Test translation service with multiple pages
        result = TranslationService.translate_pages(pages, "es")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify result structure
        assert result["success"] is True
        assert "translated_texts" in result
        assert len(result["translated_texts"]) == 100
        
        # Performance assertion: should complete within reasonable time
        # Allow 5 seconds per page for API calls (very generous)
        max_time = 500  # 5 seconds * 100 pages
        assert processing_time < max_time, \
            f"Translation took {processing_time:.2f}s, expected < {max_time}s"
        
        print(f"\n[PERFORMANCE] 100-page translation: {processing_time:.2f}s")
        print(f"[PERFORMANCE] Average per page: {processing_time/100:.2f}s")

    def test_translation_large_single_document(self):
        """
        Test translation of a single very large document.
        
        Tests translation of a document with 50,000+ characters that
        requires extensive chunking.
        
        **Validates: Requirement 1.1**
        """
        # Create a large document (50,000 characters)
        large_text = "This is a pharmaceutical document. " * 1500  # ~52,500 chars
        
        # Measure translation time
        start_time = time.time()
        
        result = TranslationService.translate_to_english(large_text, "es")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify result
        assert isinstance(result, dict)
        assert "success" in result
        assert "translated_text" in result
        
        # Performance assertion: should complete within reasonable time
        # Allow 2 minutes for very large document
        max_time = 120
        assert processing_time < max_time, \
            f"Translation took {processing_time:.2f}s, expected < {max_time}s"
        
        print(f"\n[PERFORMANCE] Large document ({len(large_text)} chars): {processing_time:.2f}s")

    def test_language_detection_large_document(self):
        """
        Test language detection with large documents.
        
        Verifies that language detection performs efficiently even
        with very large text inputs.
        
        **Validates: Requirement 3.1**
        """
        # Create a large document (100,000 characters)
        large_text = "This is a pharmaceutical document with detailed information. " * 1600
        
        # Measure detection time
        start_time = time.time()
        
        result = LanguageDetectionService.detect_language(large_text)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify result
        assert result["success"] is True
        assert "language_code" in result
        assert "confidence" in result
        
        # Performance assertion: language detection should be fast
        # Even for large documents, should complete within 5 seconds
        max_time = 5
        assert processing_time < max_time, \
            f"Language detection took {processing_time:.2f}s, expected < {max_time}s"
        
        print(f"\n[PERFORMANCE] Language detection ({len(large_text)} chars): {processing_time:.2f}s")

    def test_language_detection_100_pages(self):
        """
        Test language detection with 100+ pages.
        
        Tests the detect_language_from_pages method with a large
        number of pages.
        
        **Validates: Requirement 3.1**
        """
        # Simulate 100 pages of text
        page_text = "Drug Name: Aspirin. Batch Number: ABC123. " * 10
        pages = [page_text for _ in range(100)]
        
        # Measure detection time
        start_time = time.time()
        
        result = LanguageDetectionService.detect_language_from_pages(pages)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify result
        assert result["success"] is True
        assert "language_code" in result
        
        # Performance assertion: should be fast even with many pages
        max_time = 10
        assert processing_time < max_time, \
            f"Multi-page detection took {processing_time:.2f}s, expected < {max_time}s"
        
        print(f"\n[PERFORMANCE] 100-page language detection: {processing_time:.2f}s")

    def test_memory_usage_large_document_translation(self):
        """
        Test memory usage during large document translation.
        
        Verifies that memory usage remains reasonable when processing
        large documents and doesn't cause memory issues.
        
        **Validates: Requirement 1.1**
        """
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create a large document (10,000 characters)
        large_text = "Pharmaceutical document content. " * 300
        
        # Process the document
        result = TranslationService.translate_to_english(large_text, "es")
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Verify result
        assert isinstance(result, dict)
        
        # Memory assertion: should not increase by more than 100MB
        max_memory_increase = 100
        assert memory_increase < max_memory_increase, \
            f"Memory increased by {memory_increase:.2f}MB, expected < {max_memory_increase}MB"
        
        print(f"\n[MEMORY] Initial: {initial_memory:.2f}MB, Final: {final_memory:.2f}MB")
        print(f"[MEMORY] Increase: {memory_increase:.2f}MB")

    def test_memory_usage_100_page_processing(self):
        """
        Test memory usage during 100-page document processing.
        
        Verifies that processing many pages doesn't cause memory leaks
        or excessive memory consumption.
        
        **Validates: Requirement 1.1, 3.1**
        """
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate 100 pages
        page_text = "Drug information. " * 50
        pages = [page_text for _ in range(100)]
        
        # Process pages
        translation_result = TranslationService.translate_pages(pages, "es")
        detection_result = LanguageDetectionService.detect_language_from_pages(pages)
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Verify results
        assert translation_result["success"] is True
        assert detection_result["success"] is True
        
        # Memory assertion: should not increase by more than 200MB for 100 pages
        max_memory_increase = 200
        assert memory_increase < max_memory_increase, \
            f"Memory increased by {memory_increase:.2f}MB, expected < {max_memory_increase}MB"
        
        print(f"\n[MEMORY] 100-page processing - Initial: {initial_memory:.2f}MB, Final: {final_memory:.2f}MB")
        print(f"[MEMORY] Increase: {memory_increase:.2f}MB")

    def test_response_time_acceptable_for_single_page(self):
        """
        Test that response time is acceptable for single page processing.
        
        Establishes baseline performance for single page processing.
        
        **Validates: Requirement 1.1, 3.1**
        """
        # Single page text
        page_text = "Drug Name: Aspirin. Batch Number: ABC123. Expiry Date: 2025-12-31. " * 5
        
        # Measure translation time
        start_time = time.time()
        translation_result = TranslationService.translate_to_english(page_text, "es")
        translation_time = time.time() - start_time
        
        # Measure detection time
        start_time = time.time()
        detection_result = LanguageDetectionService.detect_language(page_text)
        detection_time = time.time() - start_time
        
        # Verify results
        assert isinstance(translation_result, dict)
        assert isinstance(detection_result, dict)
        
        # Performance assertions
        # Translation should complete within 10 seconds for single page
        assert translation_time < 10, \
            f"Single page translation took {translation_time:.2f}s, expected < 10s"
        
        # Detection should complete within 1 second
        assert detection_time < 1, \
            f"Single page detection took {detection_time:.2f}s, expected < 1s"
        
        print(f"\n[PERFORMANCE] Single page translation: {translation_time:.2f}s")
        print(f"[PERFORMANCE] Single page detection: {detection_time:.2f}s")

    def test_chunking_performance_large_document(self):
        """
        Test chunking performance with large documents.
        
        Verifies that the smart chunking algorithm performs efficiently
        even with very large documents.
        
        **Validates: Requirement 1.1**
        """
        # Create a very large document (100,000 characters)
        large_text = "This is sentence one. This is sentence two. This is sentence three. " * 1500
        
        # Measure chunking time
        start_time = time.time()
        
        chunks = TranslationService._smart_chunk_text(large_text)
        
        end_time = time.time()
        chunking_time = end_time - start_time
        
        # Verify chunks
        assert len(chunks) > 0
        for chunk in chunks:
            assert len(chunk) <= 500
        
        # Performance assertion: chunking should be fast
        # Should complete within 2 seconds even for 100k chars
        max_time = 2
        assert chunking_time < max_time, \
            f"Chunking took {chunking_time:.2f}s, expected < {max_time}s"
        
        print(f"\n[PERFORMANCE] Chunking {len(large_text)} chars into {len(chunks)} chunks: {chunking_time:.2f}s")

    def test_multilingual_ocr_service_large_pdf_simulation(self):
        """
        Test MultilingualOCRService with simulated large PDF.
        
        Tests the complete workflow with a large multi-page document.
        
        **Validates: Requirement 1.1, 3.1**
        """
        service = MultilingualOCRService()
        
        # Simulate processing a large PDF
        with patch.object(service.__class__.__bases__[0], 'process_pdf') as mock_process:
            # Simulate 100 pages of extracted text
            large_text = "Drug information. Batch details. Expiry information. " * 2000
            
            mock_process.return_value = {
                'extracted_text': large_text,
                'confidence_score': 0.95,
                'processing_time': 10.0,
                'pages': 100
            }
            
            with patch.object(LanguageDetectionService, 'detect_language') as mock_lang:
                mock_lang.return_value = {
                    'success': True,
                    'language_code': 'es',
                    'language_name': 'Spanish',
                    'confidence': 0.95,
                    'error': None
                }
                
                with patch.object(TranslationService, 'translate_to_english') as mock_trans:
                    mock_trans.return_value = {
                        'success': True,
                        'translated_text': 'Drug information. Batch details. Expiry information. ' * 2000,
                        'error': None,
                        'source_language': 'es',
                        'target_language': 'en',
                        'chunks_count': 50,
                        'processing_time_ms': 5000
                    }
                    
                    # Measure processing time
                    start_time = time.time()
                    
                    result = service.process_pdf_multilingual('large_test.pdf')
                    
                    end_time = time.time()
                    processing_time = end_time - start_time
                    
                    # Verify result
                    assert result['translated'] is True
                    assert len(result['extracted_text']) > 0
                    
                    # Performance assertion: should complete quickly (mocked)
                    max_time = 5
                    assert processing_time < max_time, \
                        f"Processing took {processing_time:.2f}s, expected < {max_time}s"
                    
                    print(f"\n[PERFORMANCE] Large PDF processing (mocked): {processing_time:.2f}s")

    def test_concurrent_page_processing_simulation(self):
        """
        Test processing multiple pages concurrently.
        
        Simulates concurrent processing of multiple pages to verify
        the system can handle parallel workloads.
        
        **Validates: Requirement 1.1, 3.1**
        """
        # Simulate processing 10 pages
        pages = [f"Page {i} content. Drug information. " * 20 for i in range(10)]
        
        # Measure time for sequential processing
        start_time = time.time()
        
        results = []
        for page in pages:
            result = TranslationService.translate_to_english(page, "es")
            results.append(result)
        
        end_time = time.time()
        sequential_time = end_time - start_time
        
        # Verify all results
        assert len(results) == 10
        for result in results:
            assert isinstance(result, dict)
        
        # Performance note: actual concurrent processing would be faster
        print(f"\n[PERFORMANCE] Sequential processing of 10 pages: {sequential_time:.2f}s")
        print(f"[PERFORMANCE] Average per page: {sequential_time/10:.2f}s")

    def test_no_memory_leak_repeated_processing(self):
        """
        Test for memory leaks during repeated processing.
        
        Processes the same document multiple times to verify no
        memory leaks occur.
        
        **Validates: Requirement 1.1, 3.1**
        """
        process = psutil.Process(os.getpid())
        
        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process the same document 20 times
        test_text = "Drug information. " * 100
        
        for i in range(20):
            result = TranslationService.translate_to_english(test_text, "es")
            assert isinstance(result, dict)
        
        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory should not increase significantly
        # Allow 50MB increase for 20 iterations
        max_memory_increase = 50
        assert memory_increase < max_memory_increase, \
            f"Memory increased by {memory_increase:.2f}MB after 20 iterations, expected < {max_memory_increase}MB"
        
        print(f"\n[MEMORY] Repeated processing (20x) - Increase: {memory_increase:.2f}MB")


class TestPerformanceEdgeCases:
    """Edge case performance tests"""

    def test_empty_pages_list_performance(self):
        """Test performance with empty pages list"""
        start_time = time.time()
        
        result = TranslationService.translate_pages([], "es")
        
        processing_time = time.time() - start_time
        
        assert result["success"] is True
        assert processing_time < 0.1  # Should be instant
        
        print(f"\n[PERFORMANCE] Empty pages list: {processing_time:.4f}s")

    def test_single_character_pages_performance(self):
        """Test performance with many single-character pages"""
        pages = ["a" for _ in range(100)]
        
        start_time = time.time()
        
        result = TranslationService.translate_pages(pages, "es")
        
        processing_time = time.time() - start_time
        
        assert isinstance(result, dict)
        
        # Should complete within reasonable time
        assert processing_time < 100  # 1 second per page max
        
        print(f"\n[PERFORMANCE] 100 single-char pages: {processing_time:.2f}s")

    def test_maximum_chunk_size_document(self):
        """Test performance with document at maximum chunk size"""
        # Create document exactly at chunk size limit
        text = "a" * 450
        
        start_time = time.time()
        
        chunks = TranslationService._smart_chunk_text(text)
        
        processing_time = time.time() - start_time
        
        assert len(chunks) > 0
        assert processing_time < 0.1  # Should be very fast
        
        print(f"\n[PERFORMANCE] Max chunk size document: {processing_time:.4f}s")


class TestPerformanceBenchmarks:
    """Benchmark tests for performance comparison"""

    def test_benchmark_translation_service(self):
        """
        Benchmark translation service performance.
        
        Provides performance metrics for different document sizes.
        """
        test_cases = [
            ("Small (100 chars)", "Drug information. " * 5, 100),
            ("Medium (1000 chars)", "Drug information. " * 50, 1000),
            ("Large (5000 chars)", "Drug information. " * 250, 5000),
            ("Very Large (10000 chars)", "Drug information. " * 500, 10000),
        ]
        
        print("\n[BENCHMARK] Translation Service Performance:")
        print("-" * 60)
        
        for name, text, expected_size in test_cases:
            start_time = time.time()
            
            result = TranslationService.translate_to_english(text, "es")
            
            processing_time = time.time() - start_time
            
            assert isinstance(result, dict)
            
            print(f"{name:25} | {processing_time:6.3f}s | {len(text):6} chars")

    def test_benchmark_language_detection(self):
        """
        Benchmark language detection performance.
        
        Provides performance metrics for different document sizes.
        """
        test_cases = [
            ("Small (100 chars)", "Drug information. " * 5),
            ("Medium (1000 chars)", "Drug information. " * 50),
            ("Large (5000 chars)", "Drug information. " * 250),
            ("Very Large (10000 chars)", "Drug information. " * 500),
        ]
        
        print("\n[BENCHMARK] Language Detection Performance:")
        print("-" * 60)
        
        for name, text in test_cases:
            start_time = time.time()
            
            result = LanguageDetectionService.detect_language(text)
            
            processing_time = time.time() - start_time
            
            assert isinstance(result, dict)
            
            print(f"{name:25} | {processing_time:6.3f}s | {len(text):6} chars")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
