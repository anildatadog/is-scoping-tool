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

_PRODUCT_SCOPE_TO_GOVERNED_PRODUCTS = {
    "infra_apm_logs": ["infra", "apm", "logs"],
    "dx": ["rum", "synthetics_api"],
    "security": ["security"],
    "ai": ["llm_observability"],
    "workflow": ["workflow", "ci_cd", "bits_ai"],
    "finops": ["cloud_cost_management"],
}

_METHODOLOGY_TO_ENGAGEMENT_TYPE = {
    "hok": "hok",
    "governedPlatform": "governed_platform",
    "goldenPattern": "governed_platform",
    "onboarding": "pair_programming",
    "capabilityBuild": "advisory",
    "consultative": "advisory",
}


def _normalise_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _governed_products_from_answers(answers: dict) -> list[str]:
    products: list[str] = []
    for scope in _normalise_list(answers.get("productScope")):
        products.extend(_PRODUCT_SCOPE_TO_GOVERNED_PRODUCTS.get(scope, [scope]))
    if not products:
        products.extend(["infra", "apm", "logs"])

    seen: set[str] = set()
    result: list[str] = []
    for product in products:
        if product not in seen:
            seen.add(product)
            result.append(product)
    return result


def _default_engagement_id(org_id: str, sf_data: dict) -> str:
    opportunity_id = sf_data.get("opportunityId") or sf_data.get("oppId") or ""
    return opportunity_id or f"{org_id}-engagement"


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


def build_governed_handoff(
    org_id: str,
    answers: dict,
    sf_data: dict | None = None,
    scoping_summary: str = "",
    engagement_id: str = "",
) -> dict:
    estimate = run_estimate(answers)
    sf_data = sf_data or {}
    methodology = estimate["methodology"]
    p1_mid = estimate.get("p1_days_mid")
    opportunity_id = sf_data.get("opportunityId") or sf_data.get("oppId") or ""
    engagement_id = engagement_id.strip()
    if opportunity_id and engagement_id and engagement_id != opportunity_id:
        return {
            "error": (
                "engagement_id must match the Salesforce Opportunity ID for "
                "Salesforce-backed handoffs."
            ),
            "expected_engagement_id": opportunity_id,
        }
    engagement_id = opportunity_id or engagement_id or _default_engagement_id(org_id, sf_data)

    arguments = {
        "org_id": org_id,
        "engagement_id": engagement_id,
        "products_in_scope": _governed_products_from_answers(answers),
        "engagement_type": _METHODOLOGY_TO_ENGAGEMENT_TYPE.get(methodology, "advisory"),
        "session_count": p1_mid,
        "source_opportunity_id": opportunity_id,
        "scoping_summary": scoping_summary,
        "scoping_payload": {
            "sf_data": sf_data,
            "answers": answers,
            "estimate": estimate,
        },
    }
    return {
        "target_mcp": "dd-governed-onboarding-mcp",
        "tool": "initialize_engagement",
        "arguments": arguments,
        "next_tool": "batch_submit_intake",
        "notes": [
            "This initializes the governed engagement only.",
            "Submit service-level inventory separately with batch_submit_intake dry_run=true first.",
        ],
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
