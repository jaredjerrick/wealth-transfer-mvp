"""Blue J direct REST API integration.

Per the spec:
- Enabled only if BLUEJ_API_KEY is set in the environment.
- POSTs (IRC section, fact-pattern summary, jurisdiction) to Blue J research API.
- Returns authority summary, predicted outcome, confidence.
- Cached by (section, fact_hash) to control API spend.
- If key absent: hide the button. No warnings, no UI affordances.

Blue J is NOT an Anthropic MCP connector — it is a credentialed SaaS REST API.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("validator.bluej")

BLUEJ_API_BASE = os.getenv("BLUEJ_API_BASE", "https://api.bluej.com/v1")
BLUEJ_TIMEOUT_S = float(os.getenv("BLUEJ_TIMEOUT_S", "10"))

_CACHE: dict[str, dict] = {}


def bluej_available() -> bool:
    """Feature flag — true iff BLUEJ_API_KEY is present in the environment."""
    return bool(os.getenv("BLUEJ_API_KEY", "").strip())


def _cache_key(section: str, fact_summary: str, jurisdiction: str) -> str:
    blob = f"{section}|{fact_summary}|{jurisdiction}".encode()
    return hashlib.sha256(blob).hexdigest()


def verify_with_bluej(
    section: str,
    fact_summary: str,
    jurisdiction: str,
) -> Optional[dict]:
    """Request a research-grade authority verification from Blue J.

    Returns a dict like:
      { "authority_summary": "...", "predicted_outcome": "...", "confidence": 0.0-1.0 }
    or None if the API is unavailable or returns an error.
    """
    api_key = os.getenv("BLUEJ_API_KEY")
    if not api_key:
        return None

    key = _cache_key(section, fact_summary, jurisdiction)
    if key in _CACHE:
        return _CACHE[key]

    try:
        with httpx.Client(timeout=BLUEJ_TIMEOUT_S) as client:
            resp = client.post(
                f"{BLUEJ_API_BASE}/research/verify",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "section": section,
                    "fact_pattern": fact_summary,
                    "jurisdiction": jurisdiction,
                },
            )
            if resp.status_code != 200:
                logger.debug("Blue J returned non-200: %s", resp.status_code)
                return None
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Blue J call failed: %r", exc)
        return None

    _CACHE[key] = data
    return data
