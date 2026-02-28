"""
comparison_service.py — Fixed & improved.

Bugs fixed:
  1. None inputs crash SequenceMatcher → added guard, returns 0% match
  2. Empty-string inputs return 1.0 similarity (auto-PASS) → returns 0% for empty
  3. Similarity computed at character level on full string, then deviations at word level
     — these two metrics were inconsistent. Now BOTH use word-level tokens so the
     match_percentage accurately reflects word-level agreement (more meaningful for
     pharmaceutical compliance where "500mg" ≠ "500 mg" matters at word level).
  4. Threshold comment said 95% but code used > 0.95 (exclusive) — now >= 0.95 (inclusive)
     consistent with the comparison_routes check of >= 95.
"""

import difflib
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ComparisonService:

    PASS_THRESHOLD = 0.95   # 95 % word-level similarity required for PASS

    @staticmethod
    def normalize_text(text: str) -> str:
        """Collapse all whitespace and strip leading/trailing spaces."""
        if not text:
            return ""
        return " ".join(text.strip().split())

    @staticmethod
    def compare_texts(
        verified_text: Optional[str],
        production_text: Optional[str],
    ) -> Dict[str, Any]:
        """
        Compare two texts and return similarity metrics.

        Args:
            verified_text:   The approved reference text.
            production_text: The OCR-extracted text to validate.

        Returns:
            Dict with keys:
              match_percentage  – 0.0–100.0 (word-level)
              deviations        – list of {"type": "added"|"removed", "word": str}
              status            – "PASS" | "FAIL"
              word_count        – {"verified": int, "production": int}
        """
        # --- Guard: treat None / empty as zero match -----------------------
        verified_raw   = verified_text   or ""
        production_raw = production_text or ""

        if not verified_raw.strip() or not production_raw.strip():
            logger.warning(
                "compare_texts called with empty text — "
                "verified_empty=%s production_empty=%s",
                not verified_raw.strip(),
                not production_raw.strip(),
            )
            return {
                "match_percentage": 0.0,
                "deviations": [],
                "status": "FAIL",
                "word_count": {"verified": 0, "production": 0},
            }

        verified   = ComparisonService.normalize_text(verified_raw)
        production = ComparisonService.normalize_text(production_raw)

        verified_words   = verified.split()
        production_words = production.split()

        # --- Word-level similarity (consistent with deviation calculation) --
        similarity = difflib.SequenceMatcher(
            None, verified_words, production_words
        ).ratio()

        # --- Structured deviations (serialization-safe dicts) ---------------
        diff = difflib.ndiff(verified_words, production_words)
        deviations = []
        for token in diff:
            if token.startswith("- "):
                deviations.append({"type": "removed", "word": token[2:]})
            elif token.startswith("+ "):
                deviations.append({"type": "added",   "word": token[2:]})

        status = "PASS" if similarity >= ComparisonService.PASS_THRESHOLD else "FAIL"

        return {
            "match_percentage": round(similarity * 100, 2),
            "deviations":       deviations,
            "status":           status,
            "word_count": {
                "verified":   len(verified_words),
                "production": len(production_words),
            },
        }