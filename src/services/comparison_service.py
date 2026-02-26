import difflib
import json


class ComparisonService:

    @staticmethod
    def normalize_text(text):
        return " ".join(text.strip().split())

    @staticmethod
    def compare_texts(verified_text, production_text):
        verified = ComparisonService.normalize_text(verified_text)
        production = ComparisonService.normalize_text(production_text)

        similarity = difflib.SequenceMatcher(
            None, verified, production
        ).ratio()

        diff = list(difflib.ndiff(
            verified.split(),
            production.split()
        ))

        deviations = [d for d in diff if d.startswith("- ") or d.startswith("+ ")]

        return {
            "match_percentage": round(similarity * 100, 2),
            "deviations": deviations,
            "status": "PASS" if similarity > 0.95 else "FAIL"
        }
