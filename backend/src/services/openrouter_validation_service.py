"""
openrouter_validation_service.py — OpenRouter API with step-3.5-flash model

This service replaces Groq validation with OpenRouter API using step-3.5-flash:free model
with reasoning capabilities for pharmaceutical label validation.

Features:
  1. Uses OpenRouter API with step-3.5-flash:free model
  2. Reasoning enabled for better analysis
  3. Preserves reasoning_details in conversation context
  4. Same JSON schema as Groq service for compatibility
  5. Robust error handling and timeout management
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
_SYSTEM_PROMPT = """You are a pharmaceutical compliance validator with advanced reasoning capabilities.
Analyze the medicine label text the user provides and extract structured fields.
Think step by step about each field and use your reasoning to validate the information.

CRITICAL: For drug_name field, look for:
- Generic drug names (e.g., paracetamol, ibuprofen, amoxicillin)
- Brand names (e.g., Tylenol, Advil, Augmentin)
- Active pharmaceutical ingredients (APIs)
- Drug names followed by dosage forms (tablets, capsules, syrup, injection)
- Chemical compound names
- Any word that represents the main therapeutic substance

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

_USER_TEMPLATE = """Validate this pharmaceutical label text and extract medicine information:

{label_text}

Use your reasoning to carefully identify each field. Pay special attention to:

DRUG NAME: Look for the main medicine name which could be:
- The most prominent text on the label
- Generic names (paracetamol, ibuprofen, metformin, etc.)
- Brand names (Tylenol, Advil, Glucophage, etc.)
- Active ingredients or chemical compounds
- Names followed by dosage forms (tablets, capsules, syrup)

STRENGTH: Dosage amounts with units (mg, ml, %, mcg, IU, etc.)
DATE FORMATS: Various formats like DD/MM/YYYY, MM/DD/YYYY, DD-MM-YY
BATCH/LOT: Numbers preceded by "Batch", "Lot", "B.No", "L.No"
MANUFACTURER: Company names, often after "Mfg by" or "Manufactured by"

Extract the most likely drug name even if you're not 100% certain."""

class OpenRouterValidationService:

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    MODEL = "stepfun/step-3.5-flash:free"
    TIMEOUT = 45   # seconds — reasoning takes more time

    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError(
                "OPENROUTER_API_KEY environment variable is not set. "
                "Add it to your .env file before starting the server."
            )
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._conversation_messages = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_text(self, extracted_text: str) -> dict:
        """
        Validate pharmaceutical label text via OpenRouter API with reasoning.

        Args:
            extracted_text: Raw OCR-extracted label text.

        Returns:
            Parsed validation result dict matching the schema above.

        Raises:
            ValueError: If extracted_text is empty.
            RuntimeError: If the OpenRouter API call fails or returns unparseable JSON.
        """
        if not extracted_text or not extracted_text.strip():
            raise ValueError("extracted_text must not be empty")

        # Sanitize input — strip triple-quotes to prevent prompt structure corruption
        safe_text = extracted_text.replace('"""', "'''")

        # Build messages for reasoning context
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_TEMPLATE.format(label_text=safe_text)},
        ]

        payload = {
            "model": self.MODEL,
            "temperature": 0.1,  # Slightly higher for reasoning variety
            "messages": messages,
            "reasoning": {"enabled": True}  # Enable reasoning capabilities
        }

        try:
            response = requests.post(
                self.OPENROUTER_URL,
                headers=self._headers,
                json=payload,
                timeout=self.TIMEOUT,
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(f"OpenRouter API timed out after {self.TIMEOUT}s")
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(f"Could not connect to OpenRouter API: {exc}") from exc

        if response.status_code != 200:
            raise RuntimeError(
                f"OpenRouter API error {response.status_code}: {response.text[:300]}"
            )

        response_data = response.json()
        assistant_message = response_data["choices"][0]["message"]
        
        # Log the raw response for debugging
        logger.info("OpenRouter API response: %s", assistant_message.get("content", "")[:200])
        
        # Store reasoning details for potential follow-up questions
        self._conversation_messages = messages + [{
            "role": "assistant",
            "content": assistant_message.get("content"),
            "reasoning_details": assistant_message.get("reasoning_details")
        }]

        raw_content = assistant_message["content"].strip()
        result = self._parse_json(raw_content)
        
        # Post-process drug name if empty or generic
        if not result.get("drug_name") or result.get("drug_name").lower() in ["not detected", "unknown", "n/a", ""]:
            result["drug_name"] = self._extract_drug_name_fallback(extracted_text)
        
        # Add reasoning summary if available
        if assistant_message.get("reasoning_details"):
            reasoning_summary = self._extract_reasoning_summary(assistant_message["reasoning_details"])
            if reasoning_summary and not result.get("analysis_summary"):
                result["analysis_summary"] = reasoning_summary

        return result

    def validate_with_followup(self, extracted_text: str, followup_question: str) -> dict:
        """
        Validate text and ask a follow-up question using preserved reasoning context.
        
        Args:
            extracted_text: Raw OCR-extracted label text.
            followup_question: Additional question to ask about the validation.
            
        Returns:
            Updated validation result with follow-up analysis.
        """
        # First get initial validation
        initial_result = self.validate_text(extracted_text)
        
        # Add follow-up question to conversation
        followup_messages = self._conversation_messages + [
            {"role": "user", "content": followup_question}
        ]
        
        payload = {
            "model": self.MODEL,
            "temperature": 0.1,
            "messages": followup_messages,
            "reasoning": {"enabled": True}
        }
        
        try:
            response = requests.post(
                self.OPENROUTER_URL,
                headers=self._headers,
                json=payload,
                timeout=self.TIMEOUT,
            )
            
            if response.status_code == 200:
                response_data = response.json()
                followup_content = response_data["choices"][0]["message"]["content"]
                
                # Try to parse as JSON, otherwise append to analysis
                try:
                    followup_result = self._parse_json(followup_content)
                    # Merge results, preferring followup for updated fields
                    initial_result.update(followup_result)
                except RuntimeError:
                    # Not JSON, append to analysis summary
                    current_summary = initial_result.get("analysis_summary", "")
                    initial_result["analysis_summary"] = f"{current_summary} Follow-up: {followup_content}"
                    
        except Exception as exc:
            logger.warning(f"Follow-up question failed: {exc}")
            # Return initial result if follow-up fails
            
        return initial_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_drug_name_fallback(text: str) -> str:
        """
        Fallback method to extract drug name using pattern matching.
        
        Args:
            text: The OCR extracted text
            
        Returns:
            Best guess drug name or "Not detected"
        """
        if not text:
            return "Not detected"
        
        # Common pharmaceutical patterns
        patterns = [
            # Generic drug names with common suffixes
            r'\b([A-Za-z]+(?:cillin|mycin|prazole|olol|pine|zole|statin|sartan|pril|ide|ine|ate|ol))\b',
            # Brand names (capitalized words not common words)
            r'\b([A-Z][a-z]{3,}(?:\s+[A-Z][a-z]{2,})?)\s+(?:tablet|capsule|syrup|injection|mg|ml)',
            # Words followed by dosage forms
            r'\b([A-Za-z]{4,})\s+(?:tablet|capsule|syrup|injection|suspension|cream|ointment)',
            # Words followed by strength
            r'\b([A-Za-z]{4,})\s+\d+\s*(?:mg|ml|g|%)',
            # Capitalized words at the beginning (likely drug names)
            r'^([A-Z][A-Za-z]{3,})',
            # Any pharmaceutical-looking word
            r'\b([A-Za-z]{5,}(?:ol|in|ate|ide|ine|one|ase))\b'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Filter out common non-drug words
                excluded_words = {
                    'tablet', 'capsule', 'syrup', 'injection', 'suspension', 
                    'cream', 'ointment', 'solution', 'drops', 'powder',
                    'manufactured', 'company', 'limited', 'pharmaceutical',
                    'batch', 'expiry', 'date', 'strength', 'contains'
                }
                
                for match in matches:
                    if match.lower() not in excluded_words and len(match) >= 4:
                        return match.title()
        
        # Last resort: look for any capitalized word that's not common
        words = re.findall(r'\b[A-Z][a-z]{3,}\b', text)
        common_words = {'Batch', 'Date', 'Expiry', 'Manufactured', 'Company', 'Limited'}
        
        for word in words:
            if word not in common_words:
                return word
        
        return "Not detected"

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

        logger.error("Unparseable OpenRouter response: %s", content[:500])
        raise RuntimeError(
            "OpenRouter returned a response that could not be parsed as JSON. "
            "Raw content logged at ERROR level."
        )

    @staticmethod
    def _extract_reasoning_summary(reasoning_details) -> str:
        """
        Extract a concise summary from reasoning details for analysis_summary.
        
        Args:
            reasoning_details: The reasoning_details object from OpenRouter response.
            
        Returns:
            A concise summary string or empty string if extraction fails.
        """
        try:
            if isinstance(reasoning_details, dict):
                # Try to extract key reasoning points
                if "steps" in reasoning_details:
                    steps = reasoning_details["steps"]
                    if isinstance(steps, list) and steps:
                        # Get the last few reasoning steps
                        last_steps = steps[-2:] if len(steps) > 1 else steps
                        summary_parts = []
                        for step in last_steps:
                            if isinstance(step, dict) and "content" in step:
                                content = step["content"][:100]  # Limit length
                                summary_parts.append(content)
                        if summary_parts:
                            return "Reasoning: " + " | ".join(summary_parts)
                            
                # Fallback: try to get any text content
                if "content" in reasoning_details:
                    content = str(reasoning_details["content"])[:150]
                    return f"Analysis: {content}"
                    
        except Exception as exc:
            logger.debug(f"Could not extract reasoning summary: {exc}")
            
        return ""