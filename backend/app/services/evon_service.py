"""Gnani Evon structured extraction and conversational correction service."""

import asyncio
import json
import platform
import re
import threading
from typing import Any, Optional

import httpx

from app.config import get_settings
from app.services.prisma_service import ConfigurationError


_LOCAL_MODEL = None
_LOCAL_TOKENIZER = None
_LOCAL_MODEL_ID: str | None = None
_LOCAL_INFERENCE_LOCK = threading.Lock()


def _generate_with_transformers(messages: list[dict[str, str]], model_id: str) -> str:
    """Run Evon locally on supported Linux/CUDA hardware; load weights only on demand."""
    global _LOCAL_MODEL, _LOCAL_TOKENIZER, _LOCAL_MODEL_ID
    if platform.system() != "Linux":
        raise ConfigurationError("The Evon v3.3 Transformers runtime is supported on Linux with a compatible NVIDIA GPU; use the API backend or a dedicated inference host on this machine.")
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise ConfigurationError("Local Evon needs the optional backend/requirements-evon-local.txt dependencies.") from exc
    if not torch.cuda.is_available():
        raise ConfigurationError("Local Evon needs an NVIDIA CUDA GPU. CPU-only inference is not supported for this 30B BF16 model.")

    total_gpu_bytes = sum(torch.cuda.get_device_properties(index).total_memory for index in range(torch.cuda.device_count()))
    if total_gpu_bytes < 70 * 1024**3:
        raise ConfigurationError("Local Evon v3.3 BF16 needs about 70 GB of combined GPU memory. Configure a supported 80 GB class GPU host or an inference server.")

    try:
        with _LOCAL_INFERENCE_LOCK:
            if _LOCAL_MODEL is None or _LOCAL_MODEL_ID != model_id:
                _LOCAL_TOKENIZER = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
                _LOCAL_MODEL = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    torch_dtype=torch.bfloat16,
                    trust_remote_code=True,
                    device_map="auto",
                )
                _LOCAL_MODEL.eval()
                _LOCAL_MODEL_ID = model_id

            tokenized = _LOCAL_TOKENIZER.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
                enable_thinking=False,
            ).to(_LOCAL_MODEL.device)
            with torch.inference_mode():
                output = _LOCAL_MODEL.generate(
                    **tokenized,
                    max_new_tokens=768,
                    do_sample=False,
                    eos_token_id=_LOCAL_TOKENIZER.eos_token_id,
                )
            new_tokens = output[0][tokenized["input_ids"].shape[-1]:]
            return _LOCAL_TOKENIZER.decode(new_tokens, skip_special_tokens=True).strip()
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ExtractionError("Local Gnani Evon failed to load or generate a response. Existing session data was not changed.") from exc


def _parse_json_object(content: Any) -> dict[str, Any]:
    if isinstance(content, str):
        text = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        try:
            content = json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start < 0 or end <= start:
                raise ExtractionError("Gnani Evon returned an invalid JSON response.")
            try:
                content = json.loads(text[start:end + 1])
            except json.JSONDecodeError as exc:
                raise ExtractionError("Gnani Evon returned an invalid JSON response.") from exc
    if not isinstance(content, dict):
        raise ExtractionError("Gnani Evon returned an invalid JSON response.")
    return content


class ExtractionError(Exception):
    """The extraction provider could not return a usable answer."""


class EvonService:
    SYSTEM_PROMPT = """You extract worker-reported wage records for MazdoorMitra.
Return one JSON object with these keys: intent, days_worked, daily_wage,
hours_worked, wage_basis, hourly_rate, overtime_hours, overtime_multiplier,
work_date, amount_received, payment_type, employer_name,
description, missing_fields, ambiguities. intent must be log_work,
log_payment, query, or unknown. payment_type must be cash, upi, bank,
advance, other, or null. Use YYYY-MM-DD dates. Use numeric values for amounts.
Never invent a number, employer, date, or payment method. Use null and list
missing required fields when the worker did not say the value. Set wage_basis
to daily or hourly according to the stated rate; never convert an hourly rate
into a daily rate. Use overtime_hours and overtime_multiplier only when the
worker explicitly states them. For payments,
store the received date in work_date. Do not mark an optional employer or
description as required. Set requires_confirmation to true."""

    REPLY_PROMPT = """Interpret the worker's latest answer or correction for the
existing wage record. Return a JSON object containing only fields that the
worker explicitly supplied or corrected, using keys from: intent,
days_worked, daily_wage, hours_worked, wage_basis, hourly_rate,
overtime_hours, overtime_multiplier, work_date, amount_received,
payment_type, employer_name, description. Do not repeat untouched fields.
Use null for fields that were not changed, and never infer missing values.
For a one-field follow-up, use the first missing field from the current record
when the answer clearly supplies it. Dates must be YYYY-MM-DD."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.GNANI_EVON_API_KEY
        self.api_url = settings.GNANI_EVON_API_URL
        self.backend = settings.GNANI_EVON_BACKEND.strip().lower()
        self.model_id = settings.GNANI_EVON_MODEL_ID.strip() or "gnani/gnani-evon-v3.3-30B-A3B"

    def _check_config(self) -> None:
        if self.backend == "transformers":
            return
        if self.backend != "api":
            raise ConfigurationError("GNANI_EVON_BACKEND must be 'api' or 'transformers'.")
        if not self.api_key or not self.api_key.strip():
            raise ConfigurationError("Gnani Evon is not configured. Add GNANI_EVON_API_KEY to backend/.env.")
        if not self.api_url or not self.api_url.strip():
            raise ConfigurationError("Gnani Evon API URL is not configured.")

    async def _complete(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        if self.backend == "transformers":
            self._check_config()
            content = await asyncio.to_thread(_generate_with_transformers, messages, self.model_id)
            return _parse_json_object(content)
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
            return _parse_json_object(content)
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
