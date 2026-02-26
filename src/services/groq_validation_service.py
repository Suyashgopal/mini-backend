"""
groq_validation_service.py — Fixed & hardened.

Bugs fixed:
  1. [CRITICAL] Hardcoded API key removed → reads from GROQ_API_KEY env var
  2. Greedy regex r'{.*}' replaced with json.JSONDecoder().raw_decode() — correct nested JSON parsing
  3. No timeout on requests.post() → added 30s timeout
  4. Prompt injection via triple-quotes in label text → sanitized before embedding
  5. Unused 'os' import removed
  6. No error raised when API key missing → explicit startup check
"""

import json
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template — label text is injected via a USER message, not embedded
# inside triple-quotes in the system prompt, preventing prompt injection.
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are a pharmaceutical compliance validator.
Analyze the medicine label text the user provides and extract structured fields.
Return STRICT JSON ONLY — no markdown, no explanation, no code fences.

Required JSON schema:
{
  "drug_name": "string",
  "strength": "string",
  "batch_number": "string",
  "manufacturing_date": "string",
  "expiry_date": "string",
  "manufacturer": "string",
  "license_number": "string or null",
  "serialization_present": true or false,
  "missing_fields": ["list of missing field names"],
  "format_valid": true or false,
  "risk_level": "LOW or MEDIUM or HIGH",
  "confidence_score": 0-100,
  "analysis_summary": "short plain-text explanation"
}"""

_USER_TEMPLATE = """Validate this pharmaceutical label text:

{label_text}"""

class GroqValidationService:

    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL    = "llama-3.1-8b-instant"
    TIMEOUT  = 30   # seconds — never hang indefinitely

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY environment variable is not set. "
                "Add it to your .env file before starting the server."
            )
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_text(self, extracted_text: str) -> dict:
        """
        Validate pharmaceutical label text via Groq API.

        Args:
            extracted_text: Raw OCR-extracted label text.

        Returns:
            Parsed validation result dict matching the schema above.

        Raises:
            ValueError: If extracted_text is empty.
            RuntimeError: If the Groq API call fails or returns unparseable JSON.
        """
        if not extracted_text or not extracted_text.strip():
            raise ValueError("extracted_text must not be empty")

        # Sanitize input — strip triple-quotes to prevent prompt structure corruption
        safe_text = extracted_text.replace('"""', "'''")

        payload = {
            "model": self.MODEL,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": _USER_TEMPLATE.format(label_text=safe_text)},
            ],
        }

        try:
            response = requests.post(
                self.GROQ_URL,
                headers=self._headers,
                json=payload,
                timeout=self.TIMEOUT,
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Groq API timed out after {self.TIMEOUT}s")
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(f"Could not connect to Groq API: {exc}") from exc

        if response.status_code != 200:
            raise RuntimeError(
                f"Groq API error {response.status_code}: {response.text[:300]}"
            )

        raw_content = response.json()["choices"][0]["message"]["content"].strip()
        return self._parse_json(raw_content)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(content: str) -> dict:
        """
        Robustly extract the first valid JSON object from the model response.

        Uses json.JSONDecoder.raw_decode() which correctly handles:
          - Leading/trailing whitespace
          - Text after the closing brace
          - Does NOT fall for the greedy-regex trap of grabbing the wrong object
        """
        # Strip markdown code fences if present (```json ... ```)
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.MULTILINE)
        content = re.sub(r"\s*```$", "", content, flags=re.MULTILINE)
        content = content.strip()

        decoder = json.JSONDecoder()
        # Walk forward until we find the opening brace
        for idx, char in enumerate(content):
            if char == "{":
                try:
                    obj, _ = decoder.raw_decode(content, idx)
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    continue   # try the next '{' if this one fails

        logger.error("Unparseable Groq response: %s", content[:500])
        raise RuntimeError(
            "Groq returned a response that could not be parsed as JSON. "
            "Raw content logged at ERROR level."
        )
