"""Manager pipeline synthesis — port of the is-manager-pipeline skill logic."""
from __future__ import annotations

import re
from collections import defaultdict


def classify_intent(question: str) -> str:
    """Classify a manager's free-text question into one of four query types."""
    q = question.lower()
    # filter before aggregate/capacity so "over 50 by motion" → filter, not aggregate
    if any(kw in q for kw in ("over", "above", "more than", "at least", "threshold", "which deals", "50+")):
        return "filter"
    # aggregate before capacity so "total days by motion" → aggregate, not capacity
    if any(kw in q for kw in ("by motion", "by shape", "breakdown", "group", "pipeline by", "split by")):
        return "aggregate"
    if any(kw in q for kw in ("total", "sum", "how many days", "capacity", "committed")):
        return "capacity"
    # Default: drill (customer name or estimator lookup)
    return "drill"


def _safe_int(v: str) -> int:
    try:
        return int(v.strip())
    except (ValueError, AttributeError):
        return 0


def synthesise_pipeline(
    rows: list[dict],
    query_type: str,
    customer: str | None = None,
    estimator: str | None = None,
    quarter: str | None = None,
    threshold_days: int | None = None,
) -> dict:
    """Synthesise a portfolio response for the given query type and filters."""
    # Apply quarter filter first if provided
    if quarter:
        rows = [r for r in rows if r.get("quarter", "").strip().lower() == quarter.strip().lower()]

    if query_type == "drill":
        matches = []
        for r in rows:
            if customer and customer.lower() in r.get("customer_name", "").lower():
                matches.append(r)
            elif estimator and estimator.lower() in r.get("estimator", "").lower():
                matches.append(r)
        return {"query_type": "drill", "matches": matches, "count": len(matches), "caveat": ""}

    if query_type == "filter":
        floor = threshold_days or 0
        matches = [r for r in rows if _safe_int(r.get("p1_days_mid", "0")) > floor]
        return {
            "query_type": "filter",
            "matches": matches,
            "count": len(matches),
            "threshold_days": floor,
            "caveat": "",
        }

    if query_type == "aggregate":
        by_motion: dict[str, list] = defaultdict(list)
        for r in rows:
            by_motion[r.get("motion", "unknown")].append(r)
        groups = []
        for motion, motion_rows in sorted(by_motion.items()):
            mids = [_safe_int(r.get("p1_days_mid", "0")) for r in motion_rows]
            pm_count = sum(1 for r in motion_rows if r.get("pm_required", "").lower() == "yes")
            groups.append({
                "key": motion,
                "count": len(motion_rows),
                "avg_mid": round(sum(mids) / len(mids)) if mids else 0,
                "pm_required": pm_count,
            })
        return {"query_type": "aggregate", "groups": groups, "total_rows": len(rows), "caveat": ""}

    if query_type == "capacity":
        total = sum(_safe_int(r.get("p1_days_mid", "0")) for r in rows)
        return {
            "query_type": "capacity",
            "total_days_mid": total,
            "row_count": len(rows),
            "quarter_filter": quarter,
            "caveat": "This is the sum of midpoint estimates, not committed days — actual PS contracts may differ.",
        }

    return {"query_type": query_type, "matches": [], "caveat": "Unknown query type."}
