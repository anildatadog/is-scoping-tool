"""IS Scoping — FastAPI backend.

Thin wrapper around existing Python business logic. No logic lives here.
All routes delegate immediately to domain modules.
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

import snowflake_lookup as sf
from auth import AuthFailure, verify_google_bearer
from diagnosis import diagnose, to_service_motion
from methodologies import recommend, build_flags, build_next_steps
from phase1 import MOTIONS, fast_estimate, explain_estimate
from prose import generate as generate_prose

app = FastAPI(title="IS Scoping Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # local dev only — in prod, backend is internal Cloud Run
    allow_credentials=False,      # no cookies between frontend and backend; IAM handles auth
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def verify_google_token(request: Request, call_next):
    """Verify Google ID token on every request except /health.

    Skipped entirely when GOOGLE_CLIENT_ID env var is absent (local dev).
    Rejects non-@datadoghq.com accounts with 403.
    """
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id or request.url.path == "/health" or request.method == "OPTIONS":
        return await call_next(request)

    try:
        verify_google_bearer(request.headers.get("Authorization", ""), client_id)
    except AuthFailure as exc:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    return await call_next(request)


# ── Request models ────────────────────────────────────────────────

class DiagnoseRequest(BaseModel):
    answers: dict


class ProseRequest(BaseModel):
    diagnosis: dict
    answers: dict


class EstimateRequest(BaseModel):
    motion: str
    answers: dict


class SelectAccountRequest(BaseModel):
    account: dict  # full account row from /search results (ACCOUNT_ID + all fields)


# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/search")
def search(q: str = Query(..., min_length=1)) -> list[dict]:
    """Search by account name or opp ID.

    If q looks like an opp ID (006...), fetches the full SF data object
    directly and returns it as a single-element list so the client can
    handle both shapes uniformly.
    """
    if sf.is_opp_id(q):
        opp = sf.lookup_opp_by_id(q)
        if opp is None:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        full = sf.fetch_full(opp)
        return [sf.to_sf_data(full)]
    return sf.search_accounts(q)


@app.get("/lookup")
def lookup(opp_id: str = Query(...)) -> dict:
    """Full SF data fetch for a known opp ID. Returns the sf_data dict
    (accountName, prefill answers, MRR, contracted products)."""
    opp = sf.lookup_opp_by_id(opp_id)
    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    full = sf.fetch_full(opp)
    return sf.to_sf_data(full)


@app.post("/accounts/select")
def accounts_select(req: SelectAccountRequest) -> dict:
    """Given an account row from /search, fetch the open opportunity and
    contracted DD products, then return the full sf_data dict with prefill.

    The client sends back the account dict it received from /search so we
    avoid a redundant Snowflake account query.
    """
    full = sf.fetch_full(req.account)
    return sf.to_sf_data(full)


@app.post("/diagnose")
def diagnose_endpoint(req: DiagnoseRequest) -> dict:
    """Run the full diagnostic engine on a completed answer set.

    Returns the structured diagnosis, v1 session recommendation, risk flags,
    next steps, and the AE-facing service motion label.
    """
    diag = diagnose(req.answers)
    rec = recommend(req.answers)
    flags = build_flags(req.answers, rec["key"], rec.get("sMax"))
    next_steps = build_next_steps(req.answers, rec["key"])
    service_motion = to_service_motion(
        diag["shape"]["value"], diag["motion"]["value"]
    )
    return {
        "diagnosis": diag,
        "recommendation": rec,
        "flags": flags,
        "next_steps": next_steps,
        "service_motion": service_motion,
    }


@app.post("/prose")
def prose_endpoint(req: ProseRequest) -> dict:
    """Generate consulting-voice diagnosis and consequence paragraphs.

    Returns null paragraphs on any failure (missing key, API error, parse
    error, or any unexpected exception). Callers must handle null gracefully.
    prose.generate() catches most Anthropic failures internally, but the
    broad except here guards against any uncaught runtime error.
    """
    try:
        result = generate_prose(req.diagnosis, req.answers)
    except Exception:
        result = None
    if result is None:
        return {"diagnosis_paragraph": None, "consequence_paragraph": None}
    return result


@app.get("/phase1/motions")
def phase1_motions() -> dict:
    """Return the 6 named service motions for the Phase 1 selector UI."""
    return MOTIONS


@app.post("/phase1/estimate")
def phase1_estimate(req: EstimateRequest) -> dict:
    """Rough day-range estimate from Phase 1 motion + minimal inputs.

    Returns days_min/days_max (int or null), pm_required (bool), and
    optionally a 'label' string when no numeric range applies (Resident
    Architect).
    """
    return fast_estimate(req.motion, req.answers)


@app.post("/phase1/explain")
def phase1_explain(req: EstimateRequest) -> dict:
    """Rule-based explanation of why the estimate landed where it did,
    plus motion-specific next steps. Instant — no LLM call.

    Returns: {why: str, next_steps: list[str]}
    """
    return explain_estimate(req.motion, req.answers)
