"""Gnani Evon structured extraction and conversational correction service."""

import json
from typing import Any, Optional

import httpx

from app.config import get_settings
from app.services.prisma_service import ConfigurationError


class ExtractionError(Exception):
    """The extraction provider could not return a usable answer."""


class EvonService:
    SYSTEM_PROMPT = """You extract worker-reported wage records for MazdoorMitra.
Return one JSON object with these keys: intent, days_worked, daily_wage,
hours_worked, work_date, amount_received, payment_type, employer_name,
description, missing_fields, ambiguities. intent must be log_work,
log_payment, query, or unknown. payment_type must be cash, upi, bank,
advance, other, or null. Use YYYY-MM-DD dates. Use numeric values for amounts.
Never invent a number, employer, date, or payment method. Use null and list
missing required fields when the worker did not say the value. For payments,
store the received date in work_date. Do not mark an optional employer or
description as required. Set requires_confirmation to true."""

    REPLY_PROMPT = """Interpret the worker's latest answer or correction for the
existing wage record. Return a JSON object containing only fields that the
worker explicitly supplied or corrected, using keys from: intent,
days_worked, daily_wage, hours_worked, work_date, amount_received,
payment_type, employer_name, description. Do not repeat untouched fields.
Use null for fields that were not changed, and never infer missing values.
For a one-field follow-up, use the first missing field from the current record
when the answer clearly supplies it. Dates must be YYYY-MM-DD."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.GNANI_EVON_API_KEY
        self.api_url = settings.GNANI_EVON_API_URL

    def _check_config(self) -> None:
        if not self.api_key or not self.api_key.strip():
            raise ConfigurationError("Gnani Evon is not configured. Add GNANI_EVON_API_KEY to backend/.env.")
        if not self.api_url or not self.api_url.strip():
            raise ConfigurationError("Gnani Evon API URL is not configured.")

    async def _complete(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        self._check_config()
        headers = {
            "X-API-Key-ID": self.api_key.strip(),
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "evon-30b",
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
            if response.status_code != 200:
                raise ExtractionError(f"Gnani Evon returned HTTP {response.status_code}.")
            result = response.json()
            content: Any = None
            if isinstance(result, dict):
                choices = result.get("choices")
                if isinstance(choices, list) and choices:
                    content = choices[0].get("message", {}).get("content")
                elif isinstance(result.get("extracted_data"), dict):
                    content = result["extracted_data"]
                elif result.get("intent") is not None:
                    content = result
            if isinstance(content, str):
                content = json.loads(content)
            if not isinstance(content, dict):
                raise ExtractionError("Gnani Evon returned an invalid JSON response.")
            return content
        except ConfigurationError:
            raise
        except ExtractionError:
            raise
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise ExtractionError("Gnani Evon could not be reached. Please try again.") from exc
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise ExtractionError("Gnani Evon returned an unreadable response.") from exc

    async def extract(
        self,
        transcript: str,
        language: str = "hi",
        context: Optional[dict] = None,
    ) -> dict[str, Any]:
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        if context:
            messages.append({"role": "system", "content": f"Existing context: {json.dumps(context, ensure_ascii=False)}"})
        messages.append({"role": "user", "content": f"Language: {language}. Transcript: {transcript}"})
        return await self._complete(messages)

    async def extract_reply(
        self,
        reply: str,
        current_data: dict,
        language: str = "hi",
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": self.REPLY_PROMPT},
            {"role": "system", "content": f"Current record: {json.dumps(current_data, ensure_ascii=False)}"},
            {"role": "user", "content": f"Language: {language}. Reply: {reply}"},
        ]
        return await self._complete(messages)


def get_evon_service() -> EvonService:
    return EvonService()
