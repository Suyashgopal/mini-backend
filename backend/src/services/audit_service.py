"""
audit_service.py — Minimal audit service for tamper detection.

This service generates and verifies cryptographic hashes for comparison results
to detect tampering and identify duplicate submissions.
"""

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AuditService:
    """Service for generating audit hashes and verifying record integrity."""
    
    # Secret key for HMAC (in production, this should be from environment)
    _SECRET_KEY = "audit-secret-key-change-in-production"
    
    @classmethod
    def generate_audit_hash(
        cls,
        extracted_text: str,
        match_percentage: float,
        status: str,
        final_decision: str,
        authenticity_score: float,
        compared_at: str,
        submitter_ip: str
    ) -> str:
        """
        Generate audit hash including timestamp and IP for tamper detection.
        
        This hash changes if any field is modified, including when/where it was created.
        """
        # Create canonical string representation
        data_string = f"{extracted_text}|{match_percentage}|{status}|{final_decision}|{authenticity_score}|{compared_at}|{submitter_ip}"
        
        # Generate HMAC-SHA256 hash
        audit_hash = hmac.new(
            cls._SECRET_KEY.encode('utf-8'),
            data_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        logger.debug("Generated audit hash for comparison at %s", compared_at)
        return audit_hash
    
    @classmethod
    def generate_content_hash(
        cls,
        extracted_text: str,
        match_percentage: float,
        status: str
    ) -> str:
        """
        Generate content hash without timestamp/IP for duplicate detection.
        
        This hash is the same for identical label content, regardless of when/where processed.
        """
        # Create canonical string representation (no timestamp/IP)
        data_string = f"{extracted_text}|{match_percentage}|{status}"
        
        # Generate SHA256 hash (no HMAC needed for duplicate detection)
        content_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
        
        logger.debug("Generated content hash for duplicate detection")
        return content_hash
    
    @classmethod
    def verify_record(cls, record: Dict[str, Any], stored_hash: str) -> Dict[str, Any]:
        """
        Verify if a record has been tampered with by comparing hashes.
        
        Args:
            record: Dict containing the record fields
            stored_hash: The hash that was stored when the record was created
            
        Returns:
            Dict containing verification results
        """
        try:
            # Regenerate hash from current record data
            current_hash = cls.generate_audit_hash(
                extracted_text=record.get("extracted_text", ""),
                match_percentage=record.get("match_percentage", 0.0),
                status=record.get("status", ""),
                final_decision=record.get("final_decision", ""),
                authenticity_score=record.get("authenticity_score", 0.0),
                compared_at=record.get("compared_at", ""),
                submitter_ip=record.get("submitter_ip", "")
            )
            
            # Compare hashes
            is_tampered = current_hash != stored_hash
            
            result = {
                "tampered": is_tampered,
                "verified_at": datetime.utcnow().isoformat(),
                "current_hash": current_hash,
                "stored_hash": stored_hash
            }
            
            if is_tampered:
                result["reason"] = "Hash mismatch - record may have been modified"
                logger.warning("Tamper detection: Hash mismatch for record")
            else:
                result["reason"] = "Hash match - record appears authentic"
                logger.info("Tamper detection: Record verified as authentic")
            
            return result
            
        except Exception as exc:
            logger.exception("Failed to verify record integrity")
            return {
                "tampered": None,
                "reason": f"Verification failed: {str(exc)}",
                "verified_at": datetime.utcnow().isoformat()
            }