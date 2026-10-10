"""
AI client for CivicLens Mini.

Primary runtime: an OPEN-WEIGHT model (Qwen2.5-7B-Instruct) served through the
OpenRouter API. We talk to it over plain HTTPS so the project has no heavy local
dependency. The API key is read from the environment / .env ONLY -- it is never
hard-coded and never written to disk.

Design goals:
  * Return STRUCTURED, VALIDATED JSON for every complaint.
  * Never fabricate a location or evidence that the citizen did not report.
  * Degrade with a clear, honest error when the model is unreachable -- we never
    silently swap in a fake/canned analysis.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

# Open-weight model. Qwen2.5-7B-Instruct is Apache-2.0 and within the
# challenge's maximum model size of 8B parameters.
# Served here via OpenRouter so no local GPU/RAM is required.
DEFAULT_MODEL = os.environ.get("CIVICLENS_MODEL", "qwen/qwen-2.5-7b-instruct")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Categories the classifier is constrained to. Keeping a closed set makes the
# dashboard metrics meaningful and the output predictable.
CATEGORIES = [
    "Roads & Potholes",
    "Water Supply",
    "Sewerage & Drainage",
    "Electricity",
    "Waste Management",
    "Street Lighting",
    "Public Safety",
    "Parks & Environment",
    "Other",
]

PRIORITIES = ["Low", "Medium", "High", "Critical"]


class AIError(Exception):
    """Raised when the AI runtime is unreachable or misconfigured."""


SYSTEM_PROMPT = (
    "You are a civic complaint analyst for a city municipal office. "
    "You read a citizen complaint and return ONLY a single JSON object. "
    "Do not add commentary, markdown, or code fences.\n\n"
    "Rules you MUST follow:\n"
    "- NEVER invent a location. If the citizen did not state a location, set "
    "\"location\" to null.\n"
    "- NEVER invent evidence. Only list evidence the citizen explicitly "
    "mentioned (photos, videos, bills, reference numbers). If none, use an "
    "empty list.\n"
    "- NEVER claim the complaint is verified or official. Your priority is a "
    "SUGGESTION for a human officer to review.\n"
    "- \"reported_duration\" is how long the citizen says the problem has "
    "existed (e.g. \"3 days\", \"2 weeks\"), or null if not stated.\n"
    f"- \"category\" MUST be exactly one of: {CATEGORIES}.\n"
    f"- \"suggested_priority\" MUST be exactly one of: {PRIORITIES}.\n\n"
    "Return JSON with EXACTLY these keys:\n"
    "{\n"
    '  "category": string,\n'
    '  "summary": string (<= 30 words),\n'
    '  "reported_duration": string | null,\n'
    '  "location": string | null,\n'
    '  "evidence_mentioned": string[],\n'
    '  "suggested_priority": string,\n'
    '  "priority_reasons": string[]\n'
    "}"
)


def _api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise AIError(
            "No OPENROUTER_API_KEY found. Set it in a .env file "
            "(see .env.example) or as an environment variable, then restart "
            "the app. The AI analysis step needs this key; nothing else does."
        )
    return key


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of the model's reply, tolerating stray text."""
    text = text.strip()
    # Strip accidental code fences.
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fallback: grab the outermost {...} block.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        return json.loads(snippet)  # may raise -> caller handles
    raise json.JSONDecodeError("no JSON object found", text, 0)


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        v = value.strip()
        return [v] if v else []
    return [str(value)]


def _coerce_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"null", "none", "n/a", "not provided", "unknown"}:
        return None
    return s


def validate_analysis(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise and sanity-check the model's JSON into a safe, known shape."""
    category = str(raw.get("category", "")).strip()
    if category not in CATEGORIES:
        category = "Other"

    priority = str(raw.get("suggested_priority", "")).strip().title()
    if priority not in PRIORITIES:
        priority = "Medium"

    summary = str(raw.get("summary", "")).strip() or "No summary produced."

    return {
        "category": category,
        "summary": summary,
        "reported_duration": _coerce_optional_str(raw.get("reported_duration")),
        "location": _coerce_optional_str(raw.get("location")),
        "evidence_mentioned": _coerce_list(raw.get("evidence_mentioned")),
        "suggested_priority": priority,
        "priority_reasons": _coerce_list(raw.get("priority_reasons")),
    }


def analyze_complaint(text: str, *, model: str | None = None, timeout: int = 60) -> dict[str, Any]:
    """
    Send a complaint to the open-weight model and return validated analysis.

    Raises AIError on connection/config problems. Raises ValueError when the
    model replies but its output cannot be parsed as valid JSON even after
    repair -- callers surface this as a user-facing "could not analyse" message
    rather than guessing.
    """
    key = _api_key()
    model = model or DEFAULT_MODEL

    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Citizen complaint:\n\n{text}"},
        ],
        # Ask OpenRouter/the model to emit a JSON object when supported.
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            # Optional attribution headers OpenRouter recommends.
            "HTTP-Referer": "https://github.com/your-org/civiclens-mini",
            "X-Title": "CivicLens Mini",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise AIError(
            f"OpenRouter returned HTTP {exc.code}. Check your API key and that "
            f"the model '{model}' is available. Detail: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise AIError(
            "Could not reach OpenRouter. Check your internet connection. "
            f"Detail: {exc.reason}"
        ) from exc

    try:
        envelope = json.loads(body)
        content = envelope["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        raise AIError(f"Unexpected response shape from OpenRouter: {exc}") from exc

    try:
        raw = _extract_json(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "The model did not return valid JSON. Raw reply (truncated): "
            + content[:300]
        ) from exc

    return validate_analysis(raw)


def health_check() -> tuple[bool, str]:
    """Lightweight readiness probe used by the dashboard banner."""
    try:
        _api_key()
    except AIError as exc:
        return False, str(exc)
    return True, f"AI ready (model: {DEFAULT_MODEL} via OpenRouter)."
