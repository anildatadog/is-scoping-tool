"""Structured diagnosis synthesis — v2 scoping tool.

Produces a structured architect's brief from the questionnaire inputs:
  shape:               Foundation | Accelerator | Gap-filler | Standards-setter | Defer
  motion:              IS-delivered | Customer-delivered | Partner-delivered
  binding_constraints: ordered list, all that apply (priority preserved as order)
  triggers:            consolidated audit trail (which inputs fired which field)
  customer_ownership:  composed from (shape, motion) plus conditional bullets

All rule-based. No LLM. The questionnaire (methodologies.QUESTIONS) is
unchanged. The v1 session-estimate math (methodologies.recommend) is retained
and consumed separately for the commercial footer.

Schema history:
  Slice 1   : initial shape/posture/dominant_constraint
  Slice 3.1 : Defer shape + no-heavy-HOK policy for high-volume Gap-filler
  Slice 3.3 : productScope as multi-select list; productCount dropped
  Slice 3.7 : posture→motion (3 values), dominant_constraint→binding_constraints (list),
              Standards-setter precedence over Accelerator for centrally-governed
              broad-scope mature customers
"""
from __future__ import annotations

from typing import TypedDict


class _Field(TypedDict):
    value: str
    triggers: list[tuple[str, str]]


class Trigger(TypedDict):
    signal: str
    value: str
    contributed_to: list[str]


class Diagnosis(TypedDict):
    shape: _Field
    motion: _Field
    binding_constraints: list[_Field]
    triggers: list[Trigger]
    customer_ownership: list[str]


# ──────────────────────────────────────────────────────────────────
# productScope helpers (multi-select list)
# ──────────────────────────────────────────────────────────────────

def _scope_list(a: dict) -> list[str]:
    """productScope is a multi-select list (slice 3.3). Returns [] when
    absent or unanswered (= observability-only)."""
    return a.get("productScope") or []


def _has_security_scope(a: dict) -> bool:
    return "security" in _scope_list(a)


def _has_dx_scope(a: dict) -> bool:
    return "dx" in _scope_list(a)


def _has_ai_scope(a: dict) -> bool:
    return "ai" in _scope_list(a)


def _has_workflow_scope(a: dict) -> bool:
    return "workflow" in _scope_list(a)


def _is_platform_scope(a: dict) -> bool:
    """3+ add-ons selected = platform-scale engagement, regardless of which ones."""
    return len(_scope_list(a)) >= 3


# ──────────────────────────────────────────────────────────────────
# Shape: Defer | Gap-filler | Foundation | Standards-setter | Accelerator
# ──────────────────────────────────────────────────────────────────
# Order matters — first match wins. Standards-setter precedes Accelerator
# (slice 3.7 fix): a centrally-governed broad-scope mature customer should
# get the "publish a replicable blueprint" diagnosis, not the generic
# accelerate-decisions one.

def compute_shape(a: dict) -> _Field:
    dd_status     = a.get("ddStatus")
    dd_quality    = a.get("ddQuality")
    replacing     = a.get("replacingTool")
    mig_vol       = a.get("migVol")
    capability    = a.get("capability")
    authority     = a.get("authority")
    team_count    = a.get("teamCount")
    scope_addons  = _scope_list(a)
    sponsor       = a.get("sponsor")
    urgency       = a.get("urgency")
    compliance    = a.get("compliance")

    # Defer fires before any other shape. Director+ sponsorship is the
    # structural gate for IS budget; without it (or a forcing function like
    # a hard regulatory deadline) the engagement is premature.
    forcing_function = urgency == "hard" or compliance == "yes"

    if sponsor == "none":
        return {"value": "Defer", "triggers": [("sponsor", "none")]}

    if sponsor == "engineer" and not forcing_function:
        return {
            "value": "Defer",
            "triggers": [
                ("sponsor", "engineer"),
                ("__note__", "no urgency or compliance forcing function"),
            ],
        }

    # Wider Defer: manager-level sponsor with single team + no add-ons selected
    # + no forcing function = the vanity-tooling pattern.
    if (
        sponsor == "manager"
        and team_count == "single"
        and not scope_addons
        and not forcing_function
    ):
        return {
            "value": "Defer",
            "triggers": [
                ("sponsor", "manager"),
                ("teamCount", "single"),
                ("productScope", "obs-only"),
                ("__note__", "small scope, no urgency or compliance forcing function"),
            ],
        }

    # Gap-filler — broken governance or large incumbent migration. Shaped by
    # the corrective scope, not by greenfield freedom.
    if dd_quality == "messy" or (replacing == "yes" and mig_vol in {"l", "xl"}):
        triggers: list[tuple[str, str]] = []
        if dd_quality == "messy":
            triggers.append(("ddQuality", "messy"))
        if replacing == "yes" and mig_vol in {"l", "xl"}:
            triggers.append(("replacingTool", "yes"))
            triggers.append(("migVol", mig_vol or ""))
        return {"value": "Gap-filler", "triggers": triggers}

    if dd_status == "new" or (dd_quality == "rebuild" and replacing == "no"):
        triggers = [("ddStatus", dd_status or "")]
        if dd_quality == "rebuild":
            triggers.append(("ddQuality", "rebuild"))
        return {"value": "Foundation", "triggers": triggers}

    # Standards-setter precedes Accelerator (slice 3.7 fix). Centrally-governed
    # mature customer with broad scope (2+ add-ons) and enterprise/large team
    # count → they want a replicable blueprint to publish, not just architectural
    # acceleration. Otherwise a strong-capability mature customer falls through
    # to Accelerator.
    if (
        dd_status == "live"
        and dd_quality == "good"
        and authority == "central"
        and team_count in {"enterprise", "large"}
        and len(scope_addons) >= 2
    ):
        return {
            "value": "Standards-setter",
            "triggers": [
                ("ddStatus", "live"),
                ("ddQuality", "good"),
                ("authority", "central"),
                ("teamCount", team_count or ""),
                ("productScope", f"{len(scope_addons)}-addons"),
            ],
        }

    if dd_status == "live" and dd_quality == "good" and capability == "strong":
        return {
            "value": "Accelerator",
            "triggers": [
                ("ddStatus", "live"),
                ("ddQuality", "good"),
                ("capability", "strong"),
            ],
        }

    # Fallback — treat as Foundation but signal low confidence in triggers.
    return {
        "value": "Foundation",
        "triggers": [
            ("ddStatus", dd_status or "unknown"),
            ("__fallback__", "shape not cleanly derivable from inputs"),
        ],
    }


# ──────────────────────────────────────────────────────────────────
# Motion: IS-delivered | Customer-delivered | Partner-delivered
# ──────────────────────────────────────────────────────────────────
# "Motion" replaces the old 4-posture taxonomy (slice 3.7). The 3 motions
# answer "who actually does the hands-on work" explicitly:
#   IS-delivered       — IS does the work alongside the customer (high-touch)
#   Customer-delivered — customer team does the work; IS architects/reviews
#   Partner-delivered  — delivery partner does the work; IS architects/oversees
#
# The old "IS-led" label was overloaded — it meant high-touch-everything for
# Foundation+limited-capability AND architecture-only-customer-or-partner-
# executes for high-volume Gap-filler. New motions make the distinction
# explicit.

def compute_motion(a: dict) -> _Field:
    dd_status   = a.get("ddStatus")
    dd_quality  = a.get("ddQuality")
    replacing   = a.get("replacingTool")
    mig_vol     = a.get("migVol")
    capability  = a.get("capability")
    urgency     = a.get("urgency")
    authority   = a.get("authority")
    team_count  = a.get("teamCount")

    # Capability gap dominates — IS must do the hands-on work.
    if capability == "limited":
        return {"value": "IS-delivered", "triggers": [("capability", "limited")]}

    # Heavy migration (xl) → Partner-delivered. Slice 3.1 policy: IS is not
    # scaled for hands-on migration labour at this volume. IS architects the
    # target state; partner or customer team does the cutover. This precedes
    # the urgency rule because the no-heavy-HOK policy beats deadline-driven
    # IS-pairing.
    if replacing == "yes" and mig_vol == "xl":
        return {
            "value": "Partner-delivered",
            "triggers": [
                ("replacingTool", "yes"),
                ("migVol", "xl"),
                ("__note__", "high-volume migration → IS architects, partner executes"),
            ],
        }

    # Moderate migration (l) with non-strong capability — IS pairs hands-on.
    if replacing == "yes" and mig_vol == "l" and capability != "strong":
        return {
            "value": "IS-delivered",
            "triggers": [
                ("replacingTool", "yes"),
                ("migVol", "l"),
                ("capability", capability or "unknown"),
            ],
        }

    # Hard deadline with non-strong capability — IS pairs to meet the date.
    if urgency == "hard" and capability != "strong":
        return {
            "value": "IS-delivered",
            "triggers": [("urgency", "hard"), ("capability", capability or "unknown")],
        }

    # Mature healthy deployment + strong capability → customer team does
    # the work, IS architects and reviews.
    if capability == "strong" and dd_status == "live" and dd_quality == "good":
        return {
            "value": "Customer-delivered",
            "triggers": [
                ("capability", "strong"),
                ("ddStatus", "live"),
                ("ddQuality", "good"),
            ],
        }

    # Enterprise-scale with central authority and capability to scale a pattern
    # → customer-delivered (they replicate; IS designs).
    if (
        team_count in {"enterprise", "large"}
        and authority == "central"
        and capability in {"some", "strong"}
    ):
        return {
            "value": "Customer-delivered",
            "triggers": [
                ("teamCount", team_count or ""),
                ("authority", "central"),
                ("capability", capability or ""),
            ],
        }

    # Fallback — assume mature customer-led motion. (If we got here without
    # a strong signal, the deal probably needs more discovery anyway.)
    return {
        "value": "Customer-delivered",
        "triggers": [("__fallback__", "motion not cleanly derivable; assuming customer-delivered")],
    }


# ──────────────────────────────────────────────────────────────────
# Binding constraints — ordered list, all that fire (slice 3.7)
# ──────────────────────────────────────────────────────────────────
# Returns every constraint that's binding, ordered by priority. Priority is
# encoded in the order in which constraints are evaluated. Deduplication is
# by value name (e.g. multi-team can fire twice via different rules; we keep
# the higher-priority trigger).

def compute_binding_constraints(a: dict) -> list[_Field]:
    capability    = a.get("capability")
    urgency       = a.get("urgency")
    dd_quality    = a.get("ddQuality")
    compliance    = a.get("compliance")
    team_count    = a.get("teamCount")
    authority     = a.get("authority")
    scope_addons  = _scope_list(a)

    constraints: list[_Field] = []
    seen: set[str] = set()

    def add(value: str, triggers: list[tuple[str, str]]) -> None:
        if value in seen:
            return
        seen.add(value)
        constraints.append({"value": value, "triggers": triggers})

    # 1. Capability gap
    if capability == "limited":
        add("capability gap", [("capability", "limited")])

    # 2. Deadline
    if urgency == "hard":
        add("deadline", [("urgency", "hard")])

    # 3. Governance debt
    if dd_quality == "messy":
        add("governance debt", [("ddQuality", "messy")])

    # 4. multi-team (strong signal — explicit multi-BU)
    if team_count == "large":
        add("multi-team", [("teamCount", "large")])

    # 5. Regulation
    if compliance == "yes":
        add("regulation", [("compliance", "yes")])

    # 6. multi-team (softer — enterprise without central authority)
    if team_count == "enterprise" and authority != "central":
        add("multi-team", [("teamCount", "enterprise"), ("authority", authority or "unknown")])

    # 7. Scale (broad scope at enterprise/large team count)
    if len(scope_addons) >= 3 and team_count in {"enterprise", "large"}:
        add(
            "scale",
            [
                ("productScope", f"{len(scope_addons)}-addons"),
                ("teamCount", team_count or ""),
            ],
        )

    if not constraints:
        add("none binding", [("__note__", "engagement is tractable on standard sizing")])

    return constraints


# ──────────────────────────────────────────────────────────────────
# Customer ownership — (shape, motion) base + conditional bullets
# ──────────────────────────────────────────────────────────────────

_OWNERSHIP_BASE: dict[tuple[str, str], list[str]] = {
    # Foundation — building the operating model from zero.
    ("Foundation", "IS-delivered"): [
        "Commit named engineering capacity to pair with IS for the duration.",
        "Designate the receiving team that takes ownership at handover.",
        "Appoint a CMDB / asset-owner role authoritative for service identity.",
    ],
    ("Foundation", "Customer-delivered"): [
        "Stand up a platform team to build and operate the IS-designed pattern.",
        "Decide on the platform-team broker authority over keys, integrations, patterns.",
        "Curate CMDB attributes as authoritative source-of-truth for telemetry scoping.",
    ],
    ("Foundation", "Partner-delivered"): [
        "Name the delivery partner and the scope of their build engagement.",
        "Stand up a platform team to inherit the pattern at partner handover.",
        "Govern the IS↔partner↔customer triad — IS architects, partner builds, customer operates.",
    ],

    # Accelerator — mature customer, forward architectural decisions.
    ("Accelerator", "Customer-delivered"): [
        "Execution across every workstream — IS does not own the rollout, the platform team does.",
        "Workstream prioritisation — IS does not own the backlog.",
        "Cross-team coordination, including any third-party integration partners.",
        "Exec-level steering so IS judgement stays visible — sessions consumed is a poor proxy for impact, surface architectural calls at exec cadence.",
    ],
    ("Accelerator", "IS-delivered"): [
        "Pair with IS on the specific high-stakes work driving the IS-delivered motion.",
        "Resource cross-team coordination as IS guidance lands.",
        "Operate the deployment after each IS-paired phase.",
    ],
    ("Accelerator", "Partner-delivered"): [
        "Name the delivery partner and the workstream they own.",
        "Govern the IS↔partner↔customer triad — IS advises on architecture, partner executes, customer operates.",
        "Exec-level steering so partner work stays aligned to IS-validated architecture.",
    ],

    # Gap-filler — corrective: fix broken governance or migrate from incumbent.
    ("Gap-filler", "Partner-delivered"): [
        "Engage a Datadog delivery partner for the cutover — IS is not scaled for heavy hands-on migration at this volume.",
        "Named decommission owner and audit-trail sign-off for the legacy path.",
        "Parity sign-off ahead of cutover.",
        "Govern the IS↔partner↔customer triad — IS architects target state, partner executes, customer operates.",
    ],
    ("Gap-filler", "IS-delivered"): [
        "Named decommission owner and audit-trail sign-off for the legacy path.",
        "Parity-test sign-off ahead of cutover.",
        "Change-management ownership for the cutover window.",
        "Resource the customer side of the IS-paired cutover work.",
    ],
    ("Gap-filler", "Customer-delivered"): [
        "Execute the remediation / migration — IS supplies the target state and reviews.",
        "Named decommission owner and audit-trail sign-off.",
        "Cross-team alignment on the new standards.",
    ],

    # Standards-setter — replicable blueprint; customer/partner scales.
    ("Standards-setter", "Customer-delivered"): [
        "Replication ownership across remaining teams after IS hands off the pattern + pilot.",
        "Internal training and pattern-divergence governance.",
        "Central authority to govern divergence — without a broker function the pattern won't land; push back before scoping if absent.",
    ],
    ("Standards-setter", "Partner-delivered"): [
        "Name the delivery partner that will replicate the IS-built pattern across teams.",
        "Govern pattern divergence centrally; route exceptions back to IS via the partner.",
        "Maintain the pattern over time after the IS engagement closes.",
    ],
    ("Standards-setter", "IS-delivered"): [
        "Re-scope discussion: IS doesn't run per-team rollouts. If the customer wants IS to scale the pattern across teams, the shape should be Accelerator (advisory) or Foundation (with broker authority).",
        "If keeping IS-delivered: pair on the reference build only; hand off replication to customer or partner.",
    ],
}


_DEFER_NEXT_STEPS: list[str] = [
    "For a second opinion before deferring, contact Frédérique Martin Sainte-Agathe (IS management sponsor): frederique.martinsainteagathe@datadoghq.com.",
    "Customer-led adoption with TAM support — Datadog as a product still delivers value without IS sessions.",
    "Partner-led delivery if the work is repetitive execution rather than architectural — engage a Datadog partner.",
    "Revisit IS when a director-or-above champion is named, OR an external forcing function appears (regulatory deadline, compliance audit, hard contract date).",
]


class DeferVerdict(TypedDict):
    verdict: str
    what_changes: str


def compute_defer_verdict(answers: dict) -> DeferVerdict:
    """Templated verdict prose for shape=Defer."""
    sponsor = answers.get("sponsor")

    if sponsor == "none":
        verdict = (
            "This is not yet an IS engagement. No champion has been identified at "
            "the customer, which means there is no budget owner, no internal advocate "
            "to keep the work moving, and no decision-maker who will defend the "
            "engagement's value at quarterly review. IS sessions without that anchor "
            "stall before they start."
        )
    elif sponsor == "engineer":
        verdict = (
            "This is not yet an IS engagement. Engineer-level sponsorship is a "
            "signal that the technical team sees value, but IS budget rarely lands "
            "without director-or-above approval. Without a regulatory deadline or "
            "compliance pressure forcing exec attention, the deal will stall at "
            "budget approval or be cut mid-cycle when priorities shift."
        )
    elif sponsor == "manager":
        verdict = (
            "This is not yet an IS engagement. A director-tier sponsor exists, "
            "but the combination of small scope (single team, narrow product "
            "footprint) and no external forcing function is the vanity-tooling "
            "pattern. The sponsor approves the deal but disengages once it lands "
            "at the next quarterly priority shift. The commercial completes; the "
            "work does not get operationalised."
        )
    else:
        verdict = (
            "This is not yet an IS engagement. The combination of signals suggests "
            "the engagement will not sustain attention through delivery. Re-scope "
            "or wait for the conditions below to change."
        )

    what_changes = (
        "What would change the picture: a named director-or-above champion willing "
        "to authorise IS spend, or an external forcing function — regulatory "
        "deadline, compliance audit, hard contract date — that compels exec "
        "attention. Either unlocks the budget conversation and the sustained "
        "stakeholder presence the engagement needs. In the meantime, the customer "
        "is well-served by Datadog as a product, with TAM support for ongoing "
        "advisory and a delivery partner for execution-heavy needs. The escalation "
        "line above is the path if you read this diagnosis differently."
    )

    return {"verdict": verdict, "what_changes": what_changes}


def compute_customer_ownership(a: dict, shape: str, motion: str) -> list[str]:
    # Defer is a verdict, not an engagement.
    if shape == "Defer":
        return list(_DEFER_NEXT_STEPS)

    bullets: list[str] = list(_OWNERSHIP_BASE.get((shape, motion), [
        "Execution ownership — IS does not run the deployment.",
        "Prioritisation and cross-team coordination.",
    ]))

    if a.get("compliance") == "yes":
        bullets.append("Named security and legal stakeholder from session 1.")
    if a.get("replacingTool") == "yes" and not any("decommission" in b.lower() for b in bullets):
        bullets.append("Named decommission owner for the incumbent tool.")
    if a.get("authority") == "auto" and a.get("teamCount") != "single":
        bullets.append("Central authority delegated, or rollout will fragment across teams.")

    if _has_security_scope(a):
        bullets.append("Security ops and identity teams named as stakeholders from session 1.")
    if _has_dx_scope(a):
        bullets.append("Frontend / web / mobile teams named as RUM and Synthetics stakeholders; JS instrumentation + browser-side telemetry ownership agreed.")
    if _has_ai_scope(a):
        bullets.append("Data science / ML platform team named as stakeholders; LLM Obs telemetry scope and instrumentation pattern agreed before kickoff.")
    if _has_workflow_scope(a):
        bullets.append("Platform / DevOps team named as stakeholders for CI-CD and Workflow Automation; GitHub or GitLab admin access secured for the integration.")
    if _is_platform_scope(a):
        bullets.append("Named category lead per add-on area — platform-scale expansion is too broad for a single owner; appoint a category accountable per workstream before kickoff.")

    topology = a.get("infraTopology")
    if topology == "multi-cloud":
        bullets.append("Named cloud-platform lead per cloud — IAM and integration accounts owned per provider.")
    elif topology == "sovereign":
        bullets.append("Data residency + DD site selection sign-off before any agent install.")
    elif topology == "gpu-aas":
        bullets.append("AI/HPC telemetry scope agreed — LLM Obs surface, GPU metrics, custom workload identification.")
    elif topology == "byoc":
        bullets.append("Customer owns install + version-upgrade cadence; agent rollout cadence aligned to their release cycle.")
    elif topology == "hybrid":
        bullets.append("Dual-deployment plumbing — cloud agent + on-prem agent or bridge — and the bridge owner named.")

    return bullets


# ──────────────────────────────────────────────────────────────────
# Triggers — consolidated audit trail
# ──────────────────────────────────────────────────────────────────

def _build_triggers(
    shape: _Field, motion: _Field, constraints: list[_Field],
) -> list[Trigger]:
    by_signal: dict[tuple[str, str], list[str]] = {}

    def add(field_value: _Field, prefix: str) -> None:
        for signal, value in field_value["triggers"]:
            if signal.startswith("__"):
                continue
            by_signal.setdefault((signal, value), []).append(f"{prefix}:{field_value['value']}")

    add(shape, "shape")
    add(motion, "motion")
    for c in constraints:
        add(c, "constraint")

    return [
        {"signal": sig, "value": val, "contributed_to": contribs}
        for (sig, val), contribs in by_signal.items()
    ]


# ──────────────────────────────────────────────────────────────────
# Public entrypoint
# ──────────────────────────────────────────────────────────────────

def diagnose(answers: dict) -> Diagnosis:
    """Return the full structured diagnosis. Deterministic — same answers
    in, same diagnosis out. No external calls."""
    shape = compute_shape(answers)
    motion = compute_motion(answers)
    constraints = compute_binding_constraints(answers)
    triggers = _build_triggers(shape, motion, constraints)
    ownership = compute_customer_ownership(answers, shape["value"], motion["value"])

    return {
        "shape": shape,
        "motion": motion,
        "binding_constraints": constraints,
        "triggers": triggers,
        "customer_ownership": ownership,
    }


# ──────────────────────────────────────────────────────────────────
# Commercial footer helpers — consumed by Scope_an_opportunity.py
# ──────────────────────────────────────────────────────────────────

def package_label(s_max: int | None) -> str:
    """Map the v1 session-estimate upper bound to a package name. Heuristic;
    tune as calibration data accrues."""
    if s_max is None:
        return "Resolve sponsor blocker first"
    if s_max <= 30:
        return "Starter"
    if s_max <= 60:
        return "Standard"
    if s_max <= 100:
        return "Enterprise"
    return "Multi-phase"
