"""Formats the copy-paste scoping summary for the v2 structured diagnosis output.

Replaces the v1 methodology-driven summary. The session-estimate math from
methodologies.recommend() is retained and rendered as the commercial footer.
"""
from __future__ import annotations

from datetime import date

from diagnosis import Diagnosis, package_label
from methodologies import build_flags, build_next_steps


_TEAM_LABEL = {
    "single":     "1 team",
    "multi":      "2–5 teams",
    "enterprise": "6–15 teams",
    "large":      "15+ teams/BUs",
}

_PRODUCT_LABEL = {
    "1-2":   "1–2 products",
    "3-4":   "3–4 products",
    "5-7":   "5–7 products",
    "suite": "full product suite",
}


def build(sf_data: dict | None, answers: dict, rec: dict, diag: Diagnosis) -> str:
    today = date.today().strftime("%d %b %Y")
    no_sess = rec["sMin"] is None

    ctx: list[str] = []
    if answers.get("teamCount"):
        ctx.append(_TEAM_LABEL[answers["teamCount"]])
    if answers.get("productCount"):
        ctx.append(_PRODUCT_LABEL[answers["productCount"]] + " in scope")
    if answers.get("ddStatus") == "live":
        ctx.append("existing DD customer")
    if answers.get("replacingTool") == "yes":
        ctx.append("replacing incumbent tool")
    if answers.get("compliance") == "yes":
        ctx.append("regulated industry")

    flags = [f for f in build_flags(answers, rec["key"], rec.get("sMax")) if f["t"] != "ok"]
    ns = build_next_steps(answers, rec["key"])
    rule = "━" * 40

    account_name = (sf_data or {}).get("accountName") or "[Account Name]"
    opp_name = (sf_data or {}).get("oppName") or "[not specified]"

    shape = diag["shape"]["value"]
    posture = diag["posture"]["value"]
    constraint = diag["dominant_constraint"]["value"]

    trigger_lines = "\n".join(
        f"  {t['signal']:<15} = {t['value']:<10} → {', '.join(t['contributed_to'])}"
        for t in diag["triggers"]
    ) or "  (no triggers fired — fallback diagnosis)"

    ownership_lines = "\n".join(f"  • {b}" for b in diag["customer_ownership"]) \
        or "  (no specific ownership bullets — review manually)"

    if no_sess:
        commercial_block = (
            "\nCOMMERCIAL · heuristic\n"
            "  Status: resolve sponsor blocker before estimating sessions\n"
        )
    else:
        commercial_block = (
            f"\nCOMMERCIAL · heuristic, calibration data pending\n"
            f"  Package:           {package_label(rec['sMax'])}\n"
            f"  Session estimate:  {rec['sMin']}–{rec['sMax']}\n"
            f"  Caveat:            estimates remain heuristic until calibration data accrues\n"
        )

    risk_block = ""
    if flags:
        risk_lines = "\n".join(f"⚠  {f['m']}" for f in flags)
        risk_block = f"\nRISK FLAGS\n{risk_lines}\n"

    pre_close_lines = "\n".join(f"{i+1}. {n}" for i, n in enumerate(ns))
    context_line = " · ".join(ctx) if ctx else "See answers below"

    return (
        f"IS SCOPING SUMMARY\n"
        f"{rule}\n"
        f"Customer:     {account_name}\n"
        f"Opportunity:  {opp_name}\n"
        f"Date:         {today}\n"
        f"\n"
        f"DIAGNOSIS\n"
        f"  Shape:                {shape}\n"
        f"  Posture:              {posture}\n"
        f"  Dominant constraint:  {constraint}\n"
        f"\n"
        f"  Triggers\n"
        f"{trigger_lines}\n"
        f"\n"
        f"CONTEXT\n"
        f"  {context_line}\n"
        f"\n"
        f"CUSTOMER OWNERSHIP\n"
        f"{ownership_lines}\n"
        f"{risk_block}"
        f"{commercial_block}"
        f"\nPRE-CLOSE REQUIREMENTS\n"
        f"{pre_close_lines}\n"
        f"{rule}"
    )
