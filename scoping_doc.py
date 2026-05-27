"""Formats the copy-paste scoping summary for the v2 structured diagnosis output.

Compressed layout: single-line header, LLM prose paragraphs first (so the
copy-paste reads the same quality as the in-browser version), then the
actionable bullets, then a one-line audit footer. Session estimate is hidden
when it exceeds the threshold where the number stops being defensible.
"""
from __future__ import annotations

from datetime import date

from diagnosis import (
    Diagnosis,
    compute_defer_verdict,
    compute_delivery_phases,
    phases_total_range,
)
from methodologies import build_flags, build_next_steps


# When the v1 session-estimate upper bound exceeds this, the raw range is
# hidden and the engagement is rendered as a phased delivery plan instead.
# Phases are heuristic too, but structured (per-phase scope + sessions)
# rather than a single inflated total.
_SESSION_DISPLAY_CAP = 120


def _commercial_block(rec: dict, answers: dict, shape: str) -> str:
    """Return the commercial block: either a one-line summary (under cap) or
    a multi-line phased delivery plan (over cap)."""
    if rec["sMin"] is None:
        return "Commercial: resolve sponsor blocker before estimating sessions."

    if rec["sMax"] > _SESSION_DISPLAY_CAP:
        phases = compute_delivery_phases(answers, shape)
        if not phases:
            return "Commercial: Multi-phase — engagement shape doesn't define phases."
        total_min, total_max = phases_total_range(phases)
        header = (
            f"Commercial: Multi-phase · {len(phases)} phases, "
            f"~{total_min}-{total_max} sessions total (heuristic, calibration pending)."
        )
        phase_lines = "\n".join(
            f"  {i}. {p['name']} ({p['sessions_min']}-{p['sessions_max']} sessions)\n     {p['brief']}"
            for i, p in enumerate(phases, start=1)
        )
        return f"{header}\n{phase_lines}"

    label = _package_label_short(rec["sMax"])
    return f"Commercial: {label} · {rec['sMin']}-{rec['sMax']} sessions (heuristic, calibration pending)."


def _package_label_short(s_max: int) -> str:
    if s_max <= 30:
        return "Starter"
    if s_max <= 60:
        return "Standard"
    return "Enterprise"  # > 60 but <= cap


def _triggers_one_line(diag: Diagnosis) -> str:
    parts = [f"{t['signal']}={t['value']}" for t in diag["triggers"]]
    return " · ".join(parts) if parts else "(none)"


def build(sf_data: dict | None, answers: dict, rec: dict, diag: Diagnosis,
          prose: dict | None = None) -> str:
    today = date.today().strftime("%d %b %Y")
    rule = "━" * 40

    account_name = (sf_data or {}).get("accountName") or "[Account Name]"
    opp_name = (sf_data or {}).get("oppName")
    header_tail = f" · {opp_name}" if opp_name else ""

    shape = diag["shape"]["value"]
    is_defer = shape == "Defer"

    triggers_line = _triggers_one_line(diag)
    ownership_lines = "\n".join(f"  • {b}" for b in diag["customer_ownership"])

    # ── Defer branch ──────────────────────────────────────────────────
    if is_defer:
        v = compute_defer_verdict(answers)
        return (
            f"IS SCOPING SUMMARY\n{rule}\n"
            f"Customer: {account_name}{header_tail} · {today}\n"
            f"\n"
            f"Verdict: Defer — not yet an IS engagement.\n"
            f"\n"
            f"{v['verdict']}\n"
            f"\n"
            f"{v['what_changes']}\n"
            f"\n"
            f"Next steps\n"
            f"{ownership_lines}\n"
            f"\n"
            f"Triggers (audit): {triggers_line}\n"
            f"{rule}"
        )

    # ── Engagement-shape branch ───────────────────────────────────────
    motion = diag["motion"]["value"]
    constraints_str = " · ".join(c["value"] for c in diag["binding_constraints"])

    if prose and prose.get("diagnosis_paragraph") and prose.get("consequence_paragraph"):
        prose_block = (
            f"\n{prose['diagnosis_paragraph']}\n"
            f"\n{prose['consequence_paragraph']}\n"
        )
    else:
        # Graceful fallback when LLM prose isn't available (API error, key
        # missing, etc.). Skip the prose block; the structured fields below
        # still carry the diagnosis.
        prose_block = ""

    flags = [f for f in build_flags(answers, rec["key"], rec.get("sMax")) if f["t"] != "ok"]
    ns = build_next_steps(answers, rec["key"])
    risk_block = ""
    if flags:
        risk_lines = "\n".join(f"⚠  {f['m']}" for f in flags)
        risk_block = f"\nRisk flags\n{risk_lines}\n"

    pre_close_lines = "\n".join(f"{i+1}. {n}" for i, n in enumerate(ns))

    return (
        f"IS SCOPING SUMMARY\n{rule}\n"
        f"Customer: {account_name}{header_tail} · {today}\n"
        f"\n"
        f"Diagnosis: {shape} · {motion} · {constraints_str}\n"
        f"{prose_block}"
        f"\n"
        f"Customer ownership\n"
        f"{ownership_lines}\n"
        f"{risk_block}"
        f"\n"
        f"{_commercial_block(rec, answers, shape)}\n"
        f"\n"
        f"Pre-close\n"
        f"{pre_close_lines}\n"
        f"\n"
        f"Triggers (audit): {triggers_line}\n"
        f"{rule}"
    )
