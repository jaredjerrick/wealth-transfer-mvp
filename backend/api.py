"""FastAPI surface for the wealth-transfer engine.

Exposes:
  POST /compare        — run all six strategies, return a CompareResult JSON
  GET  /healthz        — liveness
  GET  /rules/version  — surface the active rules version (consumed by UI footer)
  POST /pdf            — generate a PDF Strategy Brief (returns application/pdf)

The endpoint deliberately does *not* call the in-house engine via HTTP — the
engine is imported directly. Validators (Aiwyn / Blue J) fire as background
tasks and never block the primary response.
"""

from __future__ import annotations

import io
import logging
import os
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from engine.engine import compare_strategies, CompareResult
from engine.inputs import DonorInputs
from engine.tax_context import load_rules
from validators.aiwyn import run_aiwyn_validation_async
from validators.blue_j import bluej_available
from pdf_export import build_strategy_brief_pdf


logger = logging.getLogger("wealth_transfer_api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Wealth Transfer Strategy Comparison Engine",
    description="Deterministic, citation-traced comparison of 6 wealth-transfer strategies across NY/IL/TX.",
    version="0.1.0",
)

# CORS — env-driven so the deployed Vercel origin (or any other) can be added
# without code changes. Pass a comma-separated list in CORS_ALLOW_ORIGINS, or
# "*" to allow all (the default for the MVP).
_cors_raw = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
_origins = ["*"] if _cors_raw.strip() == "*" else [o.strip() for o in _cors_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/rules/version")
def rules_version() -> dict:
    rules = load_rules()
    return {
        "tax_year": rules["tax_year"],
        "last_updated": rules["last_updated"],
        "source": rules["source"],
        "bluej_enabled": bluej_available(),
        "aiwyn_validator_enabled": True,
    }


@app.post("/compare")
def compare(payload: dict, background_tasks: BackgroundTasks) -> dict:
    """Run the six-strategy comparison.

    Body is a JSON object matching `DonorInputs`. Validation errors return a
    400 with the specific field and the controlling authority citation
    embedded in the error message (e.g., Roth IRA blocked → §219(b)).
    """
    try:
        inputs = DonorInputs(**payload)
    except ValidationError as e:
        # Surface ValidationError details, including any §-citation strings we
        # baked into the model validators.
        raise HTTPException(status_code=400, detail=e.errors())

    rules = load_rules()
    result: CompareResult = compare_strategies(inputs, rules=rules)

    # Fire-and-log Aiwyn regression validation in the background.
    if os.getenv("DISABLE_AIWYN") != "1":
        background_tasks.add_task(run_aiwyn_validation_async, inputs.model_dump(mode="json"), result.to_dict())

    return result.to_dict()


@app.post("/pdf")
def pdf_export(payload: dict) -> Response:
    """Generate the Strategy Brief PDF. Body is the same shape as /compare."""
    try:
        inputs = DonorInputs(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors())

    rules = load_rules()
    result = compare_strategies(inputs, rules=rules)
    pdf_bytes = build_strategy_brief_pdf(inputs, result, rules)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=strategy_brief.pdf"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False)
