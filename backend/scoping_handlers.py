"""Pure-Python handler functions for the /scoping/* HTTP endpoints.

No FastMCP, no Rapid imports — plain Python called by FastAPI routes in main.py
and by the Go MCP front (is_platform/woof_hub in the internal datadog/ monorepo).
"""
from __future__ import annotations

import diagnosis as _diag
import methodologies as _meth
import sheets as _sheets
import snowflake_lookup as _sf
from pipeline import classify_intent, synthesise_pipeline


def search_account(q: str) -> list[dict]:
    if _sf.is_opp_id(q):
        opp = _sf.lookup_opp_by_id(q)
        if opp is None:
            return []
        # fetch_full expects {"ACCOUNT_ID": ...}, not an opportunity row
        full = _sf.fetch_full({"ACCOUNT_ID": opp["ACCOUNT_ID"]})
        return [_sf.to_sf_data(full)]
    return _sf.search_accounts(q)


def get_account_details(opp_id: str) -> dict:
    opp = _sf.lookup_opp_by_id(opp_id)
    if opp is None:
        return {"error": f"Opportunity {opp_id} not found"}
    full = _sf.fetch_full({"ACCOUNT_ID": opp["ACCOUNT_ID"]})
    return _sf.to_sf_data(full)


def run_estimate(answers: dict) -> dict:
    diag = _diag.diagnose(answers)
    rec = _meth.recommend(answers)
    flags = _meth.build_flags(answers, rec["key"], rec.get("sMax"))
    next_steps = _meth.build_next_steps(answers, rec["key"])
    service_motion = _diag.to_service_motion(
        diag["shape"]["value"], diag["motion"]["value"]
    )
    p1_mid = None
    if rec.get("sMin") is not None and rec.get("sMax") is not None:
        p1_mid = round((rec["sMin"] + rec["sMax"]) / 2)
    return {
        "methodology": rec["key"],
        "p1_days_low": rec.get("sMin"),
        "p1_days_high": rec.get("sMax"),
        "p1_days_mid": p1_mid,
        # pm_required mirrors phase1.py: d_max > 50 or motion == "migration"
        "pm_required": (rec.get("sMax") or 0) > 50 or rec.get("key") == "migration",
        "shape": diag["shape"]["value"],
        "motion": diag["motion"]["value"],
        "service_motion": service_motion,
        # _Field shape is {"value": str, "triggers": ...} — use "value" key
        "binding_constraints": [c["value"] for c in diag.get("binding_constraints", [])],
        "flags": flags,
        "next_steps": next_steps,
    }


def log_estimate(row: dict) -> None:
    _sheets.append_estimate_row(row)


def get_pipeline(
    question: str,
    customer: str | None = None,
    estimator: str | None = None,
    quarter: str | None = None,
    threshold_days: int | None = None,
) -> dict:
    query_type = classify_intent(question)
    rows = _sheets.read_scoping_log()
    return synthesise_pipeline(
        rows, query_type,
        customer=customer,
        estimator=estimator,
        quarter=quarter,
        threshold_days=threshold_days,
    )
