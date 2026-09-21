#!/usr/bin/env python3
"""Shared resilient Gemini GenerateContent runtime for ShortAutoPro.

All production modules should use this client instead of implementing their own
retry loops. The runtime keeps mobile latency bounded, rotates across supported
models on transient capacity failures, and raises typed errors so callers can
choose fail-open/fallback behavior without duplicating transport logic.
"""

from __future__ import annotations

import os
import time
from typing import Iterable

import requests

from runtime_config import env_float, env_int


class GeminiRuntimeError(RuntimeError):
    pass


class GeminiTemporaryUnavailable(GeminiRuntimeError):
    pass


class GeminiInvalidResponse(GeminiRuntimeError):
    pass


def _model_chain(primary: str | None = None) -> list[str]:
    primary = str(
        primary
        or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    ).strip()

    configured = os.getenv("GEMINI_MODEL_CHAIN", "").strip()
    if configured:
        raw = [x.strip() for x in configured.split(",") if x.strip()]
    else:
        raw = [
            primary,
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash",
        ]

    result: list[str] = []
    for model in raw:
        if model and model not in result:
            result.append(model)
    return result


def _extract_text(data: object) -> str:
    if not isinstance(data, dict):
        raise GeminiInvalidResponse("invalid_json_shape")

    candidates = data.get("candidates", [])
    if isinstance(candidates, list):
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content", {})
            parts = content.get("parts", []) if isinstance(content, dict) else []
            if not isinstance(parts, list):
                continue
            finish = str(candidate.get("finishReason", "") or "").strip().upper()
            if finish and finish != "STOP":
                raise GeminiInvalidResponse("finish_reason=" + finish)

            chunks = [
                str(part.get("text", "") or "")
                for part in parts
                if isinstance(part, dict)
                and not part.get("thought")
                and str(part.get("text", "") or "")
            ]
            if chunks:
                # Gemini may split structured JSON in the middle of a quoted
                # string. Joining with a newline mutates that JSON.
                return "".join(chunks).strip()

    feedback = data.get("promptFeedback", {})
    if isinstance(feedback, dict) and feedback.get("blockReason"):
        raise GeminiInvalidResponse(
            "prompt_block=" + str(feedback.get("blockReason"))
        )

    finish_reasons = []
    if isinstance(candidates, list):
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("finishReason"):
                finish_reasons.append(str(candidate.get("finishReason")))

    detail = (
        "finish_reason=" + ",".join(finish_reasons)
        if finish_reasons
        else "no_usable_candidates"
    )
    raise GeminiInvalidResponse(detail)


def generate_text(
    prompt: str,
    *,
    temperature: float = 0.4,
    max_output_tokens: int = 1800,
    response_mime_type: str | None = None,
    component: str = "Gemini",
    models: Iterable[str] | None = None,
    api_key: str | None = None,
) -> str:
    key = str(api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    if not key:
        raise GeminiTemporaryUnavailable("GEMINI_API_KEY ausente")

    timeout = env_float("SAP_GEMINI_TIMEOUT", 28.0, 8.0, 60.0)
    attempts = env_int("SAP_GEMINI_ATTEMPTS_PER_MODEL", 2, 1, 3)

    chain = list(models) if models is not None else _model_chain()
    chain = [str(x).strip() for x in chain if str(x).strip()]
    if not chain:
        raise GeminiRuntimeError("cadeia de modelos vazia")

    generation_config = {
        "temperature": float(temperature),
        "maxOutputTokens": int(max_output_tokens),
    }
    if response_mime_type:
        generation_config["responseMimeType"] = str(response_mime_type)

    payload = {
        "contents": [{"parts": [{"text": str(prompt)}]}],
        "generationConfig": generation_config,
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key,
    }

    transient = []
    invalid = []

    for model_index, model in enumerate(chain, start=1):
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + model
            + ":generateContent"
        )

        for attempt in range(1, attempts + 1):
            print(
                f"{component} model {model_index}/{len(chain)}={model} "
                f"tentativa {attempt}/{attempts}..."
            )

            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
            except requests.Timeout as exc:
                transient.append(f"{model}:timeout:{exc}")
                print(
                    f"SAP_GEMINI_FAILOVER component={component} "
                    f"model={model} reason=TIMEOUT"
                )
                if attempt < attempts:
                    time.sleep(min(1.5 * attempt, 4.0))
                    continue
                break
            except requests.RequestException as exc:
                transient.append(f"{model}:network:{exc}")
                print(
                    f"SAP_GEMINI_FAILOVER component={component} "
                    f"model={model} reason=NETWORK"
                )
                if attempt < attempts:
                    time.sleep(min(1.5 * attempt, 4.0))
                    continue
                break

            if response.ok:
                try:
                    data = response.json()
                except Exception as exc:
                    invalid.append(f"{model}:invalid_json:{exc}")
                    if attempt < attempts:
                        time.sleep(1.0)
                        continue
                    break

                try:
                    text = _extract_text(data)
                except GeminiInvalidResponse as exc:
                    reason = str(exc)
                    invalid.append(f"{model}:{reason}")

                    if "finish_reason=MAX_TOKENS" in reason and attempt < attempts:
                        current = int(payload["generationConfig"]["maxOutputTokens"])
                        payload["generationConfig"]["maxOutputTokens"] = min(
                            16000,
                            max(current + 512, current * 2),
                        )
                        print(
                            f"SAP_GEMINI_OUTPUT_BUDGET_GROW component={component} "
                            f"model={model} tokens="
                            f"{payload['generationConfig']['maxOutputTokens']}"
                        )
                        continue

                    # Safety/policy stops are deterministic for the same prompt;
                    # do not burn retries or model rotations trying to bypass
                    # them. Callers can fail-open/fallback explicitly.
                    if "finish_reason=SAFETY" in reason or "prompt_block=" in reason:
                        raise

                    if attempt < attempts:
                        time.sleep(1.0)
                        continue
                    break

                print(
                    f"SAP_GEMINI_MODEL_OK component={component} model={model}"
                )
                return text

            status = int(response.status_code or 0)
            body = str(getattr(response, "text", "") or "")[:500]

            if status in {429, 500, 502, 503, 504}:
                transient.append(f"{model}:HTTP_{status}:{body}")
                print(
                    f"SAP_GEMINI_FAILOVER component={component} "
                    f"model={model} reason=HTTP_{status}"
                )

                # Capacity/service errors should fail over quickly instead of
                # consuming the same model's entire retry budget.
                if status in {503, 504}:
                    break

                if attempt < attempts:
                    wait = 2
                    if status == 429:
                        try:
                            wait = int(
                                response.headers.get("Retry-After") or wait
                            )
                        except (TypeError, ValueError):
                            wait = 2
                        wait = max(1, min(wait, 12))
                    time.sleep(wait)
                    continue
                break

            raise GeminiRuntimeError(
                f"HTTP {status} em {model}: {body}"
            )

    detail = " | ".join((transient + invalid)[-8:]) or "sem detalhe"
    if transient:
        raise GeminiTemporaryUnavailable(
            "todos os modelos indisponíveis: " + detail
        )
    raise GeminiInvalidResponse(
        "nenhum modelo retornou texto utilizável: " + detail
    )


__all__ = [
    "GeminiRuntimeError",
    "GeminiTemporaryUnavailable",
    "GeminiInvalidResponse",
    "generate_text",
]
