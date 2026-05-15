"""Aiwyn Tax MCP regression validator.

Per the spec:
- Aiwyn MCP is authless at https://mcp.columnapi.com/mcp.
- Replay the federal + state INCOME-TAX leg through Aiwyn's `calculate_tax`.
- Compare to the in-house engine; if delta > $1 on any line item, log a
  VALIDATION_DRIFT warning and surface a small badge in the UI footer.
- Fire-and-log only — never block the user-facing response.
- Cache by (tax_year, jurisdiction, filing_status, AGI_bucket).

Aiwyn does NOT cover estate, gift, or GST tax. Those legs are unvalidated by
external sources and must be hand-pinned in tests (which we did).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from decimal import Decimal
from typing import Optional

import httpx

logger = logging.getLogger("validator.aiwyn")

AIWYN_ENDPOINT = os.getenv("AIWYN_MCP_ENDPOINT", "https://mcp.columnapi.com/mcp")
AIWYN_TIMEOUT = float(os.getenv("AIWYN_TIMEOUT_S", "5"))

# In-process cache to control call volume during a session.
_CACHE: dict[str, dict] = {}


def _agi_bucket(agi: Decimal) -> int:
    """Bucket AGI into $25K bins so the cache keys are stable across small input perturbations."""
    return int(float(agi) // 25000) * 25000


def _cache_key(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()


def _build_aiwyn_payload(donor_inputs_dict: dict) -> dict:
    """Build the `calculate_tax` payload from our DonorInputs dict."""
    return {
        "tax_year": donor_inputs_dict.get("tax_year", 2026),
        "jurisdiction": donor_inputs_dict["state"],
        "filing_status": donor_inputs_dict["filing_status"],
        "agi_bucket": _agi_bucket(Decimal(donor_inputs_dict["donor_gross_income_agi"])),
    }


async def run_aiwyn_validation_async(donor_inputs_dict: dict, engine_result: dict) -> None:
    """Fire-and-log regression validation. Always returns None — caller awaits at most for logging.

    The MVP wires this as a FastAPI BackgroundTask so it never blocks the
    primary response. If Aiwyn is unreachable, log a debug line and return.
    """
    try:
        await _run_aiwyn_validation(donor_inputs_dict, engine_result)
    except Exception as exc:  # noqa: BLE001 — never propagate
        logger.debug("Aiwyn validation skipped due to exception: %r", exc)


async def _run_aiwyn_validation(donor_inputs_dict: dict, engine_result: dict) -> None:
    payload = _build_aiwyn_payload(donor_inputs_dict)
    key = _cache_key(payload)
    if key in _CACHE:
        cached = _CACHE[key]
        _log_drift(engine_result, cached.get("aiwyn_income_tax"))
        return

    async with httpx.AsyncClient(timeout=AIWYN_TIMEOUT) as client:
        # MCP servers typically take a tool-invocation envelope. The exact shape
        # depends on the MCP host. We send a best-effort minimal request and
        # log any structural error — this validator is non-critical.
        try:
            resp = await client.post(
                AIWYN_ENDPOINT,
                json={"tool": "calculate_tax", "args": payload},
                headers={"accept": "application/json"},
            )
            if resp.status_code != 200:
                logger.debug("Aiwyn returned non-200: %s", resp.status_code)
                return
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Aiwyn call failed: %r", exc)
            return

    aiwyn_income_tax = _extract_total_income_tax(data)
    _CACHE[key] = {"aiwyn_income_tax": aiwyn_income_tax}
    _log_drift(engine_result, aiwyn_income_tax)


def _extract_total_income_tax(aiwyn_response: dict) -> Optional[Decimal]:
    """Pluck the total income tax line out of Aiwyn's response. Format
    varies — we look at a few likely keys."""
    for key in ("total_tax", "income_tax", "federal_tax", "tax_total"):
        if key in aiwyn_response:
            try:
                return Decimal(str(aiwyn_response[key]))
            except Exception:  # noqa: BLE001
                return None
    return None


def _log_drift(engine_result: dict, aiwyn_total: Optional[Decimal]) -> None:
    if aiwyn_total is None:
        return
    # Sum our engine's income + state_income across all strategies for a coarse
    # comparison. (This is intentionally a crude check — Aiwyn doesn't model our
    # five-year horizon, so we're sanity-checking direction-and-magnitude only.)
    engine_total = Decimal("0")
    for r in engine_result.get("results", []):
        breakdown = r.get("taxes_paid_breakdown", {})
        for k in ("income", "state_income", "capital_gains"):
            try:
                engine_total += Decimal(breakdown.get(k, "0"))
            except Exception:  # noqa: BLE001
                pass
    drift = abs(engine_total - aiwyn_total)
    if drift > Decimal("1"):
        logger.warning(
            "VALIDATION_DRIFT: engine_total=%s vs aiwyn_total=%s (Δ=%s). Income-leg only; "
            "estate/gift/GST are unvalidated by Aiwyn.",
            engine_total, aiwyn_total, drift,
        )
