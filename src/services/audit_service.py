"""
Two hash types — understanding why both exist:

  audit_hash   → "Was THIS specific stored record tampered with?"
                  Includes timestamp + IP. Changes every submission.
                  Protects a single row from being silently edited.

  content_hash → "Has this exact label content been seen before?"
                  No timestamp, no IP. Pure content only.
                  Same label submitted 100 times = same content_hash every time.
                  Used for duplicate detection across time.

WHY separation matters (the discovery we made):
  If we used only one hash with timestamp inside it, then:
    Day 1 submission  → hash("text + 97.5 + 2025-01-01") = a3f8...
    Day 12 submission → hash("text + 97.5 + 2025-01-12") = 7b4d...
  These look different even though the label content is identical.
  That makes duplicate detection impossible.

  So we split into two:
    audit_hash   = hash(everything including time) → tamper detection per row
    content_hash = hash(content only, no time)     → duplicate detection across time
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AuditService:

    # ----------------------------------------------------------------
    # HASH 1: audit_hash
    # Detects if a stored row was edited after saving.
    # Includes timestamp + IP so it is unique per submission.
    # ----------------------------------------------------------------

    @staticmethod
    def generate_audit_hash(
        extracted_text:     str,
        match_percentage:   float,
        status:             str,
        final_decision:     str,
        authenticity_score: int,
        compared_at:        str,   # ISO timestamp — included on purpose
        submitter_ip:       str,   # IP — included on purpose
    ) -> str:
        """
        Generate a per-row tamper-detection fingerprint.

        Timestamp and IP are intentionally included — they make this
        hash unique to this exact submission at this exact moment.
        If ANYONE edits any field in this row later, hash will
        no longer match when recomputed.

        Returns: 64-character SHA-256 hex string
        """
        payload = json.dumps({
            "extracted_text":     extracted_text     or "",
            "match_percentage":   round(float(match_percentage), 4),
            "status":             status             or "",
            "final_decision":     final_decision     or "",
            "authenticity_score": int(authenticity_score),
            "compared_at":        compared_at        or "",
            "submitter_ip":       submitter_ip       or "unknown",
        }, sort_keys=True, ensure_ascii=True)

        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ----------------------------------------------------------------
    # HASH 2: content_hash
    # Detects duplicate or resubmitted labels across any time period.
    # No timestamp, no IP — purely label content and its result.
    # ----------------------------------------------------------------

    @staticmethod
    def generate_content_hash(
        extracted_text:  str,
        match_percentage: float,
        status:          str,
    ) -> str:
        """
        Generate a content-only fingerprint — no timestamp, no IP.

        Same label + same match score + same status will ALWAYS produce
        same content_hash regardless of when or who submitted it.

        Use cases:
          - "Has this exact label been submitted before?"
          - "Show me all submissions of this label across time"
          - "Is this a duplicate submission?"

        Returns: 64-character SHA-256 hex string
        """
        payload = json.dumps({
            "extracted_text":  extracted_text  or "",
            "match_percentage": round(float(match_percentage), 4),
            "status":          status          or "",
        }, sort_keys=True, ensure_ascii=True)

        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ----------------------------------------------------------------
    # VERIFY: check if a stored row was tampered with
    # Uses audit_hash (the one with timestamp + IP)
    # ----------------------------------------------------------------

    @staticmethod
    def verify_record(record: Dict[str, Any], stored_audit_hash: Optional[str]) -> Dict[str, Any]:
        """
        Re-compute audit_hash from current record data and compare
        to the stored hash. If they differ — something was changed.

        Args:
            record:            to_dict() output of a ComparisonResult row
            stored_audit_hash: audit_hash value stored in the DB

        Returns dict with:
            tampered    → False (intact) | True (modified) | None (no hash yet)
            verified_at → ISO timestamp of when this check ran
            reason      → plain English explanation
        """
        if not stored_audit_hash:
            return {
                "tampered":    None,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "stored_hash": None,
                "reason": (
                    "No audit hash found — this record was created before "
                    "the audit system was added. Cannot verify integrity."
                ),
            }

        try:
            recomputed = AuditService.generate_audit_hash(
                extracted_text     = record.get("extracted_text",     ""),
                match_percentage   = record.get("match_percentage",   0.0),
                status             = record.get("status",             ""),
                final_decision     = record.get("final_decision",     ""),
                authenticity_score = record.get("authenticity_score", 0),
                compared_at        = record.get("compared_at",        ""),
                submitter_ip       = record.get("submitter_ip",       "unknown"),
            )
        except Exception as exc:
            logger.error("audit_hash recomputation failed: %s", exc)
            return {
                "tampered":    None,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "stored_hash": stored_audit_hash,
                "reason":      f"Verification error: {exc}",
            }

        tampered = recomputed != stored_audit_hash

        if tampered:
            logger.warning(
                "TAMPER DETECTED | stored=%s | recomputed=%s",
                stored_audit_hash[:16], recomputed[:16],
            )

        return {
            "tampered":    tampered,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "stored_hash": stored_audit_hash,
            "reason": (
                "Record integrity verified — data matches its original hash."
                if not tampered else
                "TAMPER DETECTED — this record was modified after it was saved."
            ),
        }
