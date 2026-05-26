"""IS scoping methodologies, questionnaire, and recommendation engine.

Direct port of is-scoping-tool.jsx. Keep field names and arithmetic identical
to the JSX so the two stay verifiably equivalent.
"""
from __future__ import annotations


QUESTIONS: list[dict] = [
    {
        "id": "ddStatus",
        "q": "Does this customer currently use Datadog?",
        "sfField": "Billing › Contracted DD Products",
        "opts": [
            {"v": "live", "l": "Yes — already using Datadog",
             "s": "Existing customer with active DD orgs"},
            {"v": "new", "l": "No — this is new for them",
             "s": "Net new Datadog deployment"},
        ],
        "show": lambda a: True,
    },
    {
        "id": "ddQuality",
        "q": "How would you describe their current Datadog setup?",
        "opts": [
            {"v": "good", "l": "Working well — expanding to more teams or products",
             "s": "Solid foundation, governance in place"},
            {"v": "messy", "l": "Grown organically — governance has broken down",
             "s": "Noisy alerts, no tagging standards, ballooning costs"},
            {"v": "rebuild", "l": "Being replaced or rebuilt from scratch",
             "s": "Full restart or migration to new architecture"},
        ],
        "show": lambda a: a.get("ddStatus") == "live",
    },
    {
        "id": "replacingTool",
        "q": "Is the customer replacing an existing monitoring tool?",
        "sfField": "Opportunity › Primary Competitor (Incumbent)",
        "opts": [
            {"v": "yes", "l": "Yes — replacing an existing tool",
             "s": "Splunk, Dynatrace, New Relic, Nagios, Prometheus/Grafana..."},
            {"v": "no", "l": "No — starting fresh, nothing to migrate",
             "s": "No dashboards or alerts to recreate"},
        ],
        "show": lambda a: a.get("ddStatus") == "new" or a.get("ddQuality") == "rebuild",
    },
    {
        "id": "migVol",
        "q": "Do you have a sense of how many dashboards or alert rules exist in the current tool?",
        "opts": [
            {"v": "s",   "l": "Under 50",       "s": "Light migration effort"},
            {"v": "m",   "l": "50–200",         "s": "Meaningful migration sprint needed"},
            {"v": "l",   "l": "200–500",        "s": "Large programme — needs its own track"},
            {"v": "xl",  "l": "500+",           "s": "Multi-phase migration; separate SOW likely needed"},
            {"v": "unk", "l": "Don't know yet", "s": "Tool audit session needed before final scoping"},
        ],
        "show": lambda a: a.get("replacingTool") == "yes",
    },
    {
        "id": "teamCount",
        "q": "How many separate engineering teams or business units will deploy Datadog through this project?",
        "sfField": "Account › Sales Segment + Employee Count (proxy)",
        "opts": [
            {"v": "single",     "l": "Just 1 team",
             "s": "Single squad or engineering team"},
            {"v": "multi",      "l": "2–5 teams",
             "s": "Multiple teams within one business unit"},
            {"v": "enterprise", "l": "6–15 teams",
             "s": "Enterprise-wide within one division"},
            {"v": "large",      "l": "15+ teams or multiple business units",
             "s": "Full enterprise or multi-divisional rollout"},
        ],
        "show": lambda a: True,
    },
    {
        "id": "productCount",
        "q": "How many Datadog products are in scope for this deal?",
        "sfField": "Opportunity › Products in Scope",
        "opts": [
            {"v": "1-2",   "l": "1–2 products",    "s": "e.g. Infrastructure + APM only"},
            {"v": "3-4",   "l": "3–4 products",    "s": "e.g. Infra, APM, Logs, Synthetics"},
            {"v": "5-7",   "l": "5–7 products",    "s": "Broad platform adoption"},
            {"v": "suite", "l": "Full suite (8+)", "s": "Everything Datadog offers"},
        ],
        "show": lambda a: True,
    },
    {
        "id": "sponsor",
        "q": "Who is actively sponsoring this project at the customer?",
        "sfField": "Opportunity › Champion + Economic Buyer",
        "opts": [
            {"v": "exec", "l": "C-level or VP executive (CTO, CIO, VP Engineering)",
             "s": "Has mandate and budget authority — can enforce adoption"},
            {"v": "manager", "l": "A Director or Senior Manager",
             "s": "Has influence but needs exec sign-off for large spend"},
            {"v": "engineer", "l": "The engineering team — pushing it upward",
             "s": "No executive mandate secured yet; adoption may stall"},
            {"v": "none", "l": "No clear internal champion yet",
             "s": "⚠ Risk: IS delivery without a sponsor frequently stalls",
             "danger": True},
        ],
        "show": lambda a: True,
    },
    {
        "id": "authority",
        "q": "Who decides how Datadog gets deployed — central team or each team independently?",
        "opts": [
            {"v": "central", "l": "A central Platform or DevOps team sets and enforces the standard",
             "s": "All teams must follow; they can block non-compliant deployments"},
            {"v": "guidelines", "l": "A platform team sets guidelines but teams can opt out",
             "s": "Expected but not mandated — teams can deviate"},
            {"v": "auto", "l": "Each team decides fully independently",
             "s": "No central ownership of how tools get deployed"},
        ],
        "show": lambda a: a.get("teamCount") != "single",
    },
    {
        "id": "capability",
        "q": "How would you rate the customer team's Datadog and observability experience?",
        "opts": [
            {"v": "strong", "l": "Strong — built observability platforms before at scale",
             "s": "Guidance on DD specifics only; fundamentals are solid"},
            {"v": "some", "l": "Some — a few people know Datadog, rest are learning",
             "s": "Will need best practice guidance alongside delivery"},
            {"v": "limited", "l": "Limited — new to enterprise observability or Datadog",
             "s": "Significant knowledge transfer needed; sessions run slower"},
        ],
        "show": lambda a: True,
    },
    {
        "id": "urgency",
        "q": "Is there a hard external deadline driving this project?",
        "sfField": "Opportunity › Close Date + Why Now",
        "opts": [
            {"v": "hard", "l": "Yes — hard deadline within 3 months",
             "s": "Regulatory audit, contract end, legacy tool switchoff, product launch"},
            {"v": "target", "l": "Target date in 3–6 months (flexible)",
             "s": "Internal goal — not externally enforced"},
            {"v": "flex", "l": "No hard deadline — flexible timeline",
             "s": "Customer controls the pace"},
        ],
        "show": lambda a: True,
    },
    {
        "id": "compliance",
        "q": "Is this customer in a heavily regulated industry?",
        "sfField": "Account › Industry",
        "opts": [
            {"v": "yes", "l": "Yes — Financial Services, Healthcare, Government, Defence, or similar",
             "s": "Security and compliance teams will be stakeholders from session 1"},
            {"v": "no", "l": "No — standard security practices apply",
             "s": "No special regulatory constraints"},
        ],
        "show": lambda a: True,
    },
]


METHODS: dict[str, dict] = {
    "political": {
        "name": "Pre-technical engagement required",
        "color": "#888780",
        "desc": "Without an internal champion, IS delivery stalls. Identify a sponsor, build the business case, secure a mandate first.",
        "phases": {"discover": "—", "design": "—", "build": "—", "launch": "—"},
    },
    "handsOnKeys": {
        "name": "Hands-on keys",
        "color": "#185FA5",
        "desc": "Sit with the team and build it together. Decisions in real time, full knowledge transfer. Exits with working deployment, tagging strategy, core dashboards and monitors, handoff doc.",
        "phases": {"discover": "2", "design": "2–3", "build": "4–5", "launch": "1–2"},
    },
    "capability": {
        "name": "Capability building (co-delivery)",
        "color": "#A32D2D",
        "desc": "Every session is a teaching session. Every decision explained, not just made. Exit criteria: a team that can independently own and extend what was built.",
        "phases": {"discover": "2", "design": "3–4", "build": "6–10", "launch": "2–4"},
    },
    "remediation": {
        "name": "Operational standards remediation",
        "color": "#993556",
        "desc": "Health audit first. Quantify governance debt, prioritise, rebuild — tagging first, then monitors, then dashboards. Cost, noise, and compliance are the success metrics.",
        "phases": {"discover": "3–6", "design": "4–10", "build": "8–45", "launch": "2–8"},
    },
    "migration": {
        "name": "Migration blueprint",
        "color": "#BA7517",
        "desc": "Audit source tool, define parity criteria, build in parallel, cut over, decommission. Dashboard and alert volume dominates session count. Formal parity sign-off gates cutover.",
        "phases": {"discover": "3–6", "design": "5–15", "build": "10–55", "launch": "4–12"},
    },
    "goldenPattern": {
        "name": "Golden pattern (self-service enablement)",
        "color": "#0F6E56",
        "desc": "Build a deployment pattern so frictionless teams adopt voluntarily. Pilot with one team, validate, hand off as self-service blueprint. Each additional team adds a small number of sessions.",
        "phases": {"discover": "3–5", "design": "5–18", "build": "10–45", "launch": "5–20"},
    },
    "governedPlatform": {
        "name": "Governed platform build",
        "color": "#534AB7",
        "desc": "Full operating model: central key management, intake flows, CMDB integration, RBAC, shadow integration prevention. Architecture before instrumentation.",
        "phases": {"discover": "4–6", "design": "12–25", "build": "20–45", "launch": "10–20"},
    },
    "complianceFirst": {
        "name": "Compliance-first deployment",
        "color": "#5F5E5A",
        "desc": "RBAC, key management, audit logging, data residency fully designed before any instrumentation begins. Security and compliance gate every phase.",
        "phases": {"discover": "4–7", "design": "8–20", "build": "8–35", "launch": "4–12"},
    },
    "programme": {
        "name": "Multi-track programme delivery",
        "color": "#3B6D11",
        "desc": "Multiple methodology tracks in parallel or sequence. Governed platform build as foundation, BU onboarding, migration tracks, capability building. Phased SOWs with formal break points.",
        "phases": {"discover": "8–12", "design": "25–50", "build": "60–150", "launch": "20–50"},
    },
}


def visible_questions(answers: dict) -> list[dict]:
    return [q for q in QUESTIONS if q["show"](answers)]


def recommend(a: dict) -> dict:
    if a.get("sponsor") == "none":
        return {"key": "political", "sMin": None, "sMax": None}

    migration = a.get("replacingTool") == "yes" or a.get("ddQuality") == "rebuild"
    remediation = a.get("ddQuality") == "messy"
    single     = a.get("teamCount") == "single"
    large      = a.get("teamCount") == "large"
    enterprise = a.get("teamCount") == "enterprise"
    multi      = a.get("teamCount") == "multi"

    pb = {"1-2": 0, "3-4": 8, "5-7": 18, "suite": 28}.get(a.get("productCount"), 0)
    cm = 1.38 if a.get("capability") == "limited" else 1.12 if a.get("capability") == "some" else 1.0
    mv = {"s": 0, "m": 12, "l": 28, "xl": 45, "unk": 10}.get(a.get("migVol"), 0)

    def adj(mn: int, mx: int, ex: int = 0) -> dict:
        return {"sMin": round((mn + pb + ex) * cm), "sMax": round((mx + pb + ex) * cm)}

    if remediation:
        b = (10, 20) if single else (30, 55) if multi else (55, 100) if enterprise else (80, 140)
        return {"key": "remediation", **adj(b[0], b[1])}

    if migration:
        if not large and not enterprise:
            b = (25, 55)
        elif enterprise:
            b = (60, 110)
        else:
            b = (90, 150)
        return {"key": "migration", **adj(b[0], b[1], mv)}

    if a.get("compliance") == "yes" and not single:
        b = (80, 150) if large else (45, 85) if enterprise else (25, 50)
        return {"key": "complianceFirst", **adj(b[0], b[1])}

    if single:
        if a.get("capability") == "limited":
            return {"key": "capability", **adj(15, 25)}
        return {"key": "handsOnKeys", **adj(10, 18)}

    if large:
        return {"key": "programme", **adj(130, 200, mv)}

    hi = a.get("authority") == "central"
    if enterprise:
        return {"key": "governedPlatform" if hi else "goldenPattern",
                **(adj(55, 110) if hi else adj(60, 100))}

    return {"key": "governedPlatform" if hi else "goldenPattern",
            **adj(25, 50)}


def build_flags(a: dict, key: str) -> list[dict]:
    f: list[dict] = []
    if key == "political":
        f.append({"t": "blk", "m": "No internal champion identified. IS cannot be sold until a sponsor is confirmed."})
        f.append({"t": "wrn", "m": "AE action: identify who feels the monitoring pain most. Build the business case with them before selling IS sessions."})
        return f

    if a.get("sponsor") == "engineer":
        f.append({"t": "wrn", "m": "Engineering-led with no exec mandate. Adoption will stall at the first cross-team blocker. Push for exec involvement before IS kickoff."})
    if a.get("capability") == "limited":
        f.append({"t": "wrn", "m": "Capability gap: sessions run 35–40% longer by design. Confirm knowledge transfer is a stated goal, not just deployment."})
    if a.get("urgency") == "hard":
        f.append({"t": "wrn", "m": "Hard deadline: scope must be locked in session 1. Never compress sessions — reduce scope instead."})
    if a.get("compliance") == "yes":
        f.append({"t": "inf", "m": "Regulated industry: security and legal must be named stakeholders from session 1."})
    if a.get("authority") == "auto" and a.get("teamCount") != "single":
        f.append({"t": "wrn", "m": "No central authority: adoption cannot be mandated. Exec mandate essential for scale beyond the pilot team."})
    if a.get("migVol") == "unk":
        f.append({"t": "inf", "m": "Migration volume unknown: schedule a tool audit as session 1."})
    if a.get("migVol") == "xl":
        f.append({"t": "wrn", "m": "500+ dashboards/alerts: structure as multi-phase migration."})
    if a.get("teamCount") == "large":
        f.append({"t": "inf", "m": "Large enterprise: cap each SOW phase at 50–60 sessions."})

    if not f:
        f.append({"t": "ok", "m": "No major risk flags. Standard scoping process applies."})
    return f


def build_next_steps(a: dict, key: str) -> list[str]:
    ns: list[str] = []
    if key == "political":
        ns.append("Identify who feels the monitoring pain most — that is your potential champion.")
        ns.append("Quantify the cost of inaction: incidents, legacy tool cost, team hours wasted.")
        ns.append("Do not present IS pricing until executive sponsorship is confirmed.")
        return ns

    commit_who = "1 engineer" if a.get("teamCount") == "single" else "a dedicated Datadog Admin"
    ns.append(f"Confirm the customer can commit {commit_who} 10+ hrs/week throughout.")

    if a.get("replacingTool") == "yes":
        ns.append("Verify a named decommission owner exists — without it the migration track stalls.")
    if a.get("teamCount") != "single":
        ns.append("Confirm a named pilot team and published rollout sequence before IS kickoff.")
    if a.get("compliance") == "yes":
        ns.append("Introduce IS team to security and legal stakeholders before scoping is finalised.")
    if a.get("migVol") == "unk":
        ns.append("Schedule a tool audit session before final pricing — estimate will change significantly.")

    ns.append("Book the sales-to-IS handoff call before deal close. Never hand off cold post-signature.")
    return ns
