"""Phase 1 fast-pass scoping — motion selection and rough-estimate engine.

Phase 1 is a fast entry point: AE picks a service motion, answers 3-5
questions, gets a wide-range day estimate. No diagnostic engine, no SFDC
lookup. The AE's stated motion is taken at face value; Phase 2 validates it.
"""
from __future__ import annotations


MOTIONS: dict[str, dict] = {
    "consultative": {
        "label": "Consultative / Advisory",
        "ask":   '"Help us understand what to do"',
        "desc":  "Customer needs IS guidance, architecture, standards, or recommendations. IS advises; customer executes.",
        "icon":  "💬",
    },
    "onboarding": {
        "label": "Guided Delivery",
        "ask":   '"We have a project — work with us to deliver it"',
        "desc":  "Specific project, defined scope, clear end state. IS guides and reviews while the customer team executes.",
        "icon":  "👥",
    },
    "hok": {
        "label": "HOK / Hands-on-Keyboard",
        "ask":   '"Build the Datadog assets for us"',
        "desc":  "Customer wants IS to build assets. Asset counts and complexity drive sizing.",
        "icon":  "⌨️",
    },
    "migration": {
        "label": "Migration Services",
        "ask":   '"Move us from another tool into Datadog"',
        "desc":  "Moving from Splunk, Dynatrace, SolarWinds, New Relic, or similar. Source inventory drives scope.",
        "icon":  "🔄",
    },
    "resident_architect": {
        "label": "Resident Architect",
        "ask":   '"Stay embedded with us across multiple months — we need an IS architect on tap"',
        "desc":  "No fixed scope, open-ended across multiple workstreams. IS is your go-to architect for the quarter. Sized by days/week × months.",
        "icon":  "🏗️",
    },
    "discovery": {
        "label": "Discovery / Consultative First",
        "ask":   '"We do not know yet"',
        "desc":  "Requirements, counts, or ownership are unclear. 5-10 days of scoping before a broader proposal.",
        "icon":  "🔍",
    },
}


P1_QUESTIONS: list[dict] = [
    {
        "id": "p1_teamCount",
        "q": "How many teams or workstreams are in scope?",
        "opts": [
            {"v": "single",     "l": "1 team"},
            {"v": "multi",      "l": "2–5 teams"},
            {"v": "enterprise", "l": "6–15 teams"},
            {"v": "large",      "l": "15+ teams or multiple business units"},
        ],
        "show": lambda m, a: True,
    },
    {
        "id": "p1_products",
        "q": "Which product categories are in scope?",
        "hint": "Select all that apply.",
        "kind": "multiselect",
        "opts": [
            {"v": "obs",      "l": "Standard observability (Infra, APM, Logs)"},
            {"v": "dx",       "l": "Digital Experience (RUM, Synthetics)"},
            {"v": "security", "l": "Cloud Security (CSPM, ASM, SIEM)"},
            {"v": "ai",       "l": "AI / LLM Observability"},
            {"v": "finops",   "l": "FinOps / Cloud Cost Management"},
        ],
        "show": lambda m, a: True,
    },
    {
        "id": "p1_readiness",
        "q": "How ready is their environment?",
        "opts": [
            {"v": "ready",   "l": "Ready — telemetry flowing, owners named"},
            {"v": "partial", "l": "Partial — some instrumentation exists"},
            {"v": "missing", "l": "Starting from zero"},
        ],
        "show": lambda m, a: m != "discovery",
    },
    {
        "id": "p1_migVol",
        "q": "Roughly how many dashboards / alert rules exist in the tool being replaced?",
        "opts": [
            {"v": "s",   "l": "Under 50"},
            {"v": "m",   "l": "50–200"},
            {"v": "l",   "l": "200–500"},
            {"v": "xl",  "l": "500+"},
            {"v": "unk", "l": "Unknown yet"},
        ],
        "show": lambda m, a: m == "migration",
    },
    {
        "id": "p1_deadline",
        "q": "Is there a hard external deadline?",
        "opts": [
            {"v": "hard",   "l": "Yes — within 3 months"},
            {"v": "target", "l": "Target date (flexible)"},
            {"v": "flex",   "l": "No hard deadline"},
        ],
        "show": lambda m, a: m != "discovery",
    },
]


def p1_visible_questions(motion: str, answers: dict) -> list[dict]:
    return [q for q in P1_QUESTIONS if q["show"](motion, answers)]


def fast_estimate(motion: str, answers: dict) -> dict:
    """Rough day-range estimate from Phase 1 inputs.

    Returns keys: days_min, days_max (int or None), pm_required (bool).
    Resident Architect also returns a 'label' key in place of numeric range.
    """
    if motion == "discovery":
        return {"days_min": 5, "days_max": 10, "pm_required": False}

    if motion == "resident_architect":
        return {
            "days_min": None,
            "days_max": None,
            "pm_required": True,
            "label": "Sized by days/week × months — needs deeper scoping",
        }

    team = answers.get("p1_teamCount", "multi")
    products = answers.get("p1_products") or []
    readiness = answers.get("p1_readiness", "partial")
    mig_vol = answers.get("p1_migVol", "unk")

    tf = {"single": 1, "multi": 2, "enterprise": 3, "large": 5}.get(team, 2)
    pb = len([p for p in products if p != "obs"]) * 5
    rb = {"ready": 0, "partial": 5, "missing": 12}.get(readiness, 5)
    mv = {"s": 0, "m": 10, "l": 25, "xl": 45, "unk": 15}.get(mig_vol, 0)

    _base: dict[str, tuple[int, int]] = {
        "consultative": (8,  20),
        "onboarding":   (10, 30),
        "hok":          (12, 35),
        "migration":    (20, 55),
    }
    base_min, base_max = _base.get(motion, (10, 30))

    d_min = base_min + (tf - 1) * 5 + pb
    d_max = base_max + (tf - 1) * 12 + pb + rb + mv

    pm_required = d_max > 50 or motion == "migration"

    return {"days_min": d_min, "days_max": d_max, "pm_required": pm_required}


def merge_p1_seed(sf_answers: dict, p1_seed: dict) -> dict:
    """Merge Phase 1 seed answers into SF-prefilled answers.

    SF prefill wins for overlapping factual keys (SF data is authoritative).
    _p1_stated_motion is always kept — it has no SF equivalent.
    """
    merged = dict(p1_seed)
    merged.update(sf_answers)
    if "_p1_stated_motion" in p1_seed:
        merged["_p1_stated_motion"] = p1_seed["_p1_stated_motion"]
    return merged
