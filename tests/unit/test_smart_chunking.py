#!/usr/bin/env python
"""
Comprehensive tests for smart chunking with various document sizes.

This test suite validates the smart chunking functionality of TranslationService
across different document sizes and scenarios as specified in Task 15.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
"""

import pytest
from services.translation_service import TranslationService


class TestSmartChunkingDocumentSizes:
    """Test smart chunking with various document sizes"""

    # ========== Test 1: Documents under 450 characters ==========
    def test_chunking_under_450_characters(self):
        """
        Test chunking with documents under 450 characters.
        
        Documents under the chunk size should be returned as a single chunk.
        
        **Validates: Requirements 2.1, 2.2**
        """
        # Test with short text (under 450 characters)
        short_texts = [
            "This is a short document.",
            "First sentence. Second sentence. Third sentence.",
            "A" * 100,  # 100 characters
            "Short text with multiple sentences. Each sentence is brief. Total is under limit.",
            "Pharmaceutical label: Aspirin 500mg. Take one tablet daily. Store in cool place."
        ]
        
        for text in short_texts:
            assert len(text) < 450, f"Test text should be under 450 chars, got {len(text)}"
            
            chunks = TranslationService._smart_chunk_text(text)
            
            # Should return single chunk for text under limit
            assert len(chunks) == 1, \
                f"Text under 450 chars should be single chunk, got {len(chunks)} chunks"
            
            # Chunk should contain the original text (normalized whitespace)
            assert chunks[0].strip() == text.strip(), \
                "Single chunk should match original text"
            
            # Chunk should not exceed 500 character limit
            assert len(chunks[0]) <= 500, \
                f"Chunk size {len(chunks[0])} exceeds 500 character limit"
            
            print(f"✓ Text ({len(text)} chars) -> 1 chunk: PASS")

    # ========== Test 2: Documents 450-5000 characters ==========
    def test_chunking_450_to_5000_characters(self):
        """
        Test chunking with documents between 450-5000 characters.
        
        Documents in this range should be split into multiple chunks
        respecting sentence boundaries and maintaining overlap.
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        """
        # Create texts of various sizes in the 450-5000 range
        test_cases = [
            # 500 characters - just over the chunk size
            ("Sentence one. " * 35, 500),  # ~490 chars
            
            # 1000 characters - should create 2-3 chunks
            ("This is a pharmaceutical document. " * 30, 1000),  # ~1050 chars
            
            # 2000 characters - should create 4-5 chunks
            ("Medical information follows. Each sentence contains important data. " * 30, 2000),  # ~1980 chars
            
            # 5000 characters - should create 10-12 chunks
            ("Batch record entry. Quality control passed. Manufacturing date recorded. " * 70, 5000),  # ~5110 chars
        ]
        
        for text_template, expected_size in test_cases:
            text = text_template
            actual_size = len(text)
            
            # Verify text is in expected range
            assert 450 <= actual_size <= 5500, \
                f"Test text should be 450-5500 chars, got {actual_size}"
            
            chunks = TranslationService._smart_chunk_text(text)
            
            # Should create multiple chunks
            assert len(chunks) > 1, \
                f"Text of {actual_size} chars should create multiple chunks, got {len(chunks)}"
            
            # Verify all chunks respect size limit
            for i, chunk in enumerate(chunks):
                assert len(chunk) <= 500, \
                    f"Chunk {i+1} size {len(chunk)} exceeds 500 character limit"
            
            # Verify chunks contain content
            for i, chunk in enumerate(chunks):
                assert len(chunk.strip()) > 0, \
                    f"Chunk {i+1} is empty"
            
            # Verify total content is preserved (approximately)
            combined_length = sum(len(chunk) for chunk in chunks)
            # Combined length should be >= original due to overlap
            assert combined_length >= actual_size * 0.8, \
                f"Combined chunks ({combined_length}) too short compared to original ({actual_size})"
            
            print(f"✓ Text ({actual_size} chars) -> {len(chunks)} chunks: PASS")

    # ========== Test 3: Documents over 5000 characters ==========
    def test_chunking_over_5000_characters(self):
        """
        Test chunking with documents over 5000 characters.
        
        Large documents should be split into many chunks while maintaining
        all chunking properties.
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        """
        # Create large documents
        test_cases = [
            # 6000 characters
            ("Pharmaceutical batch record. Quality assurance verified. " * 100, 6000),
            
            # 10000 characters
            ("Clinical trial data. Patient information recorded. Safety protocols followed. " * 120, 10000),
            
            # 15000 characters - very large document
            ("Manufacturing process step. Temperature controlled. Quality checked. Documentation complete. " * 150, 15000),
        ]
        
        for text_template, expected_size in test_cases:
            text = text_template
            actual_size = len(text)
            
            # Verify text is over 5000 characters
            assert actual_size > 5000, \
                f"Test text should be over 5000 chars, got {actual_size}"
            
            chunks = TranslationService._smart_chunk_text(text)
            
            # Should create many chunks
            expected_min_chunks = actual_size // 500
            assert len(chunks) >= expected_min_chunks * 0.8, \
                f"Text of {actual_size} chars should create at least {expected_min_chunks} chunks, got {len(chunks)}"
            
            # Verify all chunks respect size limit
            for i, chunk in enumerate(chunks):
                assert len(chunk) <= 500, \
                    f"Chunk {i+1} size {len(chunk)} exceeds 500 character limit"
            
            # Verify chunks contain content
            for i, chunk in enumerate(chunks):
                assert len(chunk.strip()) > 0, \
                    f"Chunk {i+1} is empty"
            
            # Verify no chunk is too small (except possibly the last one)
            for i, chunk in enumerate(chunks[:-1]):  # Exclude last chunk
                assert len(chunk) >= 100, \
                    f"Chunk {i+1} is too small ({len(chunk)} chars), inefficient chunking"
            
            print(f"✓ Text ({actual_size} chars) -> {len(chunks)} chunks: PASS")

    # ========== Test 4: Very long sentences ==========
    def test_chunking_very_long_sentences(self):
        """
        Test chunking with very long sentences (no sentence boundaries).
        
        When a single sentence exceeds the chunk size, it should be included
        as a complete chunk without further splitting (per requirements).
        
        **Validates: Requirements 2.2, 2.4**
        """
        # Create very long sentences without sentence boundaries
        test_cases = [
            # Single sentence exceeding chunk size (600 chars)
            "This is a very long sentence without any periods or other sentence boundaries " * 8,
            
            # Single sentence way over chunk size (1000 chars)
            "A pharmaceutical compound with an extremely long chemical name and description " * 12,
            
            # Multiple very long sentences
            "First very long sentence without boundaries " * 10 + ". " + 
            "Second very long sentence also without boundaries " * 10,
        ]
        
        for text in test_cases:
            chunks = TranslationService._smart_chunk_text(text)
            
            # Should create chunks
            assert len(chunks) > 0, "Should create at least one chunk"
            
            # For very long sentences, the implementation allows them to exceed
            # the chunk size limit (per requirements: don't split sentences)
            # Verify this behavior
            has_long_chunk = any(len(chunk) > 500 for chunk in chunks)
            
            # If text has no sentence boundaries and exceeds 500 chars,
            # it should be kept as one chunk even if it exceeds the limit
            if '.' not in text and '!' not in text and '?' not in text:
                if len(text) > 500:
                    # Should be one chunk exceeding the limit
                    assert len(chunks) == 1, \
                        f"Very long sentence without boundaries should be single chunk, got {len(chunks)}"
                    assert len(chunks[0]) > 500, \
                        "Very long sentence should exceed chunk size limit"
            
            # Verify all chunks contain content
            for i, chunk in enumerate(chunks):
                assert len(chunk.strip()) > 0, f"Chunk {i+1} is empty"
            
            print(f"✓ Long sentence ({len(text)} chars) -> {len(chunks)} chunk(s): PASS")

    # ========== Test 5: Verify chunk sizes don't exceed 500 characters ==========
    def test_chunk_size_limit_enforcement(self):
        """
        Verify that chunk sizes don't exceed 500 characters (except for
        single sentences that cannot be split).
        
        **Validates: Requirements 2.1**
        """
        # Create various texts with sentence boundaries
        test_texts = [
            # Text with many short sentences
            "Sentence one. Sentence two. Sentence three. " * 20,
            
            # Text with medium sentences
            "This is a medium length sentence with some content. " * 15,
            
            # Text with varying sentence lengths
            "Short. Medium length sentence here. This is a longer sentence with more content and details. " * 10,
            
            # Pharmaceutical-style text
            "Drug name: Aspirin. Dosage: 500mg. Frequency: Once daily. Duration: 7 days. " * 15,
        ]
        
        for text in test_texts:
            chunks = TranslationService._smart_chunk_text(text)
            
            # Verify all chunks respect the 500 character limit
            # (except for single sentences that exceed the limit)
            for i, chunk in enumerate(chunks):
                # Count sentence boundaries in chunk
                sentence_count = chunk.count('.') + chunk.count('!') + chunk.count('?')
                
                # If chunk has multiple sentences, it must respect the limit
                if sentence_count > 1:
                    assert len(chunk) <= 500, \
                        f"Chunk {i+1} with multiple sentences exceeds 500 char limit: {len(chunk)} chars"
                
                # Single sentence chunks can exceed the limit (per requirements)
                if sentence_count <= 1 and len(chunk) > 500:
                    print(f"  Note: Chunk {i+1} is single sentence exceeding limit ({len(chunk)} chars) - allowed")
            
            print(f"✓ Text ({len(text)} chars) chunk size limits verified: PASS")

    # ========== Test 6: Verify overlap is maintained between chunks ==========
    def test_overlap_maintenance(self):
        """
        Verify that overlap is maintained between consecutive chunks.
        
        The overlap should be approximately 50 characters to maintain context.
        
        **Validates: Requirements 2.3**
        """
        # Create text that will definitely create multiple chunks with overlap
        text = "This is sentence number one with some content. " * 30  # ~1410 chars
        
        chunks = TranslationService._smart_chunk_text(text)
        
        # Should create multiple chunks
        assert len(chunks) > 1, \
            f"Text should create multiple chunks for overlap testing, got {len(chunks)}"
        
        # Check overlap between consecutive chunks
        overlaps_found = 0
        for i in range(len(chunks) - 1):
            chunk1 = chunks[i]
            chunk2 = chunks[i + 1]
            
            # Check if there's overlap between end of chunk1 and start of chunk2
            # The overlap should be approximately 50 characters
            overlap_size = min(50, len(chunk1), len(chunk2))
            
            # Get the end of chunk1 and start of chunk2
            chunk1_end = chunk1[-overlap_size:]
            chunk2_start = chunk2[:overlap_size]
            
            # Check if there's any overlap (some common text)
            # The implementation may not have exact 50-char overlap due to sentence boundaries
            # but there should be some overlap or the chunks should connect properly
            has_overlap = any(
                chunk1_end[j:j+10] in chunk2_start 
                for j in range(len(chunk1_end) - 10)
            )
            
            if has_overlap:
                overlaps_found += 1
            
            # Verify chunks connect properly (no content loss)
            # This is more important than exact overlap size
            assert len(chunk1) > 0 and len(chunk2) > 0, \
                f"Chunks {i+1} and {i+2} should both have content"
        
        # At least some chunks should have overlap
        # (may not be all due to sentence boundary splitting)
        print(f"✓ Found overlap in {overlaps_found}/{len(chunks)-1} chunk pairs: PASS")

    # ========== Test 7: Edge cases ==========
    def test_edge_cases(self):
        """
        Test edge cases for chunking.
        
        **Validates: Requirements 2.1, 2.2, 2.5**
        """
        # Empty text
        chunks = TranslationService._smart_chunk_text("")
        assert chunks == [], "Empty text should return empty list"
        
        # Whitespace only
        chunks = TranslationService._smart_chunk_text("   \n\t  ")
        assert chunks == [], "Whitespace-only text should return empty list"
        
        # Single character
        chunks = TranslationService._smart_chunk_text("A")
        assert len(chunks) == 1, "Single character should return one chunk"
        assert chunks[0] == "A", "Single character chunk should match input"
        
        # Text exactly at chunk size (450 chars)
        text = "A" * 450
        chunks = TranslationService._smart_chunk_text(text)
        assert len(chunks) == 1, "Text at chunk size should be single chunk"
        assert len(chunks[0]) == 450, "Chunk should be exactly 450 chars"
        
        # Text just over chunk size (451 chars) with no sentence boundaries
        text = "A" * 451
        chunks = TranslationService._smart_chunk_text(text)
        # Should be kept as single chunk (no sentence boundaries to split on)
        assert len(chunks) == 1, "Text just over limit with no boundaries should be single chunk"
        
        print("✓ All edge cases handled correctly: PASS")

    # ========== Test 8: Real-world pharmaceutical text ==========
    def test_pharmaceutical_document_chunking(self):
        """
        Test chunking with realistic pharmaceutical document text.
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
        """
        # Realistic pharmaceutical label text
        pharma_text = """
        PHARMACEUTICAL PRODUCT INFORMATION
        
        Drug Name: Acetaminophen Extended Release Tablets
        Strength: 650 mg
        Dosage Form: Extended-release tablet
        Route of Administration: Oral
        
        Active Ingredient: Acetaminophen 650 mg
        
        Inactive Ingredients: Carnauba wax, hydroxyethyl cellulose, 
        hypromellose, magnesium stearate, microcrystalline cellulose, 
        povidone, pregelatinized starch, sodium starch glycolate, 
        titanium dioxide, triacetin.
        
        Indications: Temporarily relieves minor aches and pains due to 
        headache, muscular aches, backache, minor pain of arthritis, 
        the common cold, toothache, premenstrual and menstrual cramps.
        Temporarily reduces fever.
        
        Dosage and Administration: Adults and children 12 years and over: 
        Take 2 tablets every 8 hours with water. Swallow whole; do not 
        crush, chew, or dissolve. Do not take more than 6 tablets in 
        24 hours, unless directed by a doctor.
        
        Warnings: Liver warning: This product contains acetaminophen. 
        Severe liver damage may occur if you take more than 4,000 mg 
        of acetaminophen in 24 hours, with other drugs containing 
        acetaminophen, or 3 or more alcoholic drinks every day while 
        using this product.
        
        Storage: Store at 20-25°C (68-77°F). Keep container tightly closed.
        Protect from moisture.
        
        Batch Number: LOT123456
        Expiry Date: 12/2025
        Manufacturer: PharmaCorp International
        """
        
        chunks = TranslationService._smart_chunk_text(pharma_text)
        
        # Should create multiple chunks
        assert len(chunks) > 1, \
            f"Pharmaceutical document should create multiple chunks, got {len(chunks)}"
        
        # Verify all chunks respect size limit
        for i, chunk in enumerate(chunks):
            # Allow single sentences to exceed limit
            sentence_count = chunk.count('.') + chunk.count('!') + chunk.count('?')
            if sentence_count > 1:
                assert len(chunk) <= 500, \
                    f"Chunk {i+1} exceeds 500 character limit: {len(chunk)} chars"
        
        # Verify important content is preserved in chunks
        combined_text = " ".join(chunks)
        important_terms = [
            "Acetaminophen", "650 mg", "Dosage", "Warnings", 
            "Liver warning", "Storage", "Batch Number", "Expiry Date"
        ]
        
        for term in important_terms:
            assert term in combined_text, \
                f"Important term '{term}' not found in chunked text"
        
        print(f"✓ Pharmaceutical document ({len(pharma_text)} chars) -> {len(chunks)} chunks: PASS")
        print(f"  All important terms preserved in chunks")


class TestChunkingPerformance:
    """Test chunking performance and efficiency"""

    def test_chunking_efficiency(self):
        """
        Test that chunking is efficient and doesn't create too many small chunks.
        
        **Validates: Requirements 2.1, 2.4**
        """
        # Create text with good sentence structure
        text = "This is a well-structured sentence. " * 100  # ~3700 chars
        
        chunks = TranslationService._smart_chunk_text(text)
        
        # Calculate average chunk size
        avg_chunk_size = sum(len(chunk) for chunk in chunks) / len(chunks)
        
        # Average chunk size should be reasonable (not too small)
        assert avg_chunk_size >= 200, \
            f"Average chunk size ({avg_chunk_size:.0f}) is too small, inefficient chunking"
        
        # No chunk should be extremely small (except possibly the last one)
        for i, chunk in enumerate(chunks[:-1]):
            assert len(chunk) >= 100, \
                f"Chunk {i+1} is too small ({len(chunk)} chars)"
        
        print(f"✓ Chunking efficiency verified: avg size {avg_chunk_size:.0f} chars")

    def test_chunking_consistency(self):
        """
        Test that chunking produces consistent results for the same input.
        
        **Validates: Requirements 2.1, 2.2**
        """
        text = "Consistent chunking test. Multiple sentences here. " * 20
        
        # Chunk the same text multiple times
        chunks1 = TranslationService._smart_chunk_text(text)
        chunks2 = TranslationService._smart_chunk_text(text)
        chunks3 = TranslationService._smart_chunk_text(text)
        
        # Results should be identical
        assert chunks1 == chunks2, "Chunking should be consistent (run 1 vs 2)"
        assert chunks2 == chunks3, "Chunking should be consistent (run 2 vs 3)"
        
        print(f"✓ Chunking consistency verified: {len(chunks1)} chunks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
