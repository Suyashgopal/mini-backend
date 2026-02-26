from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseOCRService(ABC):
    """
    Base interface for OCR services.

    All OCR engines (Ollama, Tesseract, etc.)
    must implement these methods.
    """

    @abstractmethod
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process a single image and return OCR result.

        Returns:
            {
                "extracted_text": str,
                "translated_text": str,
                "confidence_score": float,
                "processing_time": float,
                "model_name": str
            }
        """
        pass

    @abstractmethod
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process a PDF file and return OCR result.

        Returns:
            {
                "extracted_text": str,
                "translated_text": str,
                "confidence_score": float,
                "processing_time": float,
                "model_name": str
            }
        """
        pass