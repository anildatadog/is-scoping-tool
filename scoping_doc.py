"""Formats the copy-paste scoping summary. Direct port of buildScopingDoc from JSX."""
from __future__ import annotations

from datetime import date

from methodologies import METHODS, build_flags, build_next_steps


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


def build(sf_data: dict | None, answers: dict, rec: dict) -> str:
    m = METHODS[rec["key"]]
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

    flags = [f for f in build_flags(answers, rec["key"]) if f["t"] != "ok"]
    ns = build_next_steps(answers, rec["key"])
    rule = "━" * 40

    account_name = (sf_data or {}).get("accountName") or "[Account Name]"
    opp_name = (sf_data or {}).get("oppName") or "[not specified]"

    if no_sess:
        sessions_line = "Session estimate: resolve sponsor blocker first"
    else:
        sessions_line = f"Estimated sessions: {rec['sMin']}–{rec['sMax']}"

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
        f"RECOMMENDED METHODOLOGY\n"
        f"{m['name']}\n"
        f"{sessions_line}\n"
        f"\n"
        f"CONTEXT\n"
        f"{context_line}\n"
        f"\n"
        f"PHASE BREAKDOWN\n"
        f"  Discovery: {m['phases']['discover']}\n"
        f"  Design:    {m['phases']['design']}\n"
        f"  Build:     {m['phases']['build']}\n"
        f"  Launch:    {m['phases']['launch']}\n"
        f"{risk_block}"
        f"\nPRE-CLOSE REQUIREMENTS\n"
        f"{pre_close_lines}\n"
        f"{rule}"
    )
