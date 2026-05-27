"""Structured diagnosis synthesis — v2 scoping tool slice 1.

Replaces the v1 methodology selector with a structured architect's brief:
shape / posture / dominant_constraint / triggers / customer_ownership.

All rule-based. No LLM. The 11 v1 inputs (defined in methodologies.QUESTIONS)
are unchanged. The v1 session-estimate math (methodologies.recommend) is
retained and consumed separately for the commercial footer.
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
    posture: _Field
    dominant_constraint: _Field
    triggers: list[Trigger]
    customer_ownership: list[str]


# ──────────────────────────────────────────────────────────────────
# Shape: Foundation | Accelerator | Gap-filler | Standards-setter
# ──────────────────────────────────────────────────────────────────

def compute_shape(a: dict) -> _Field:
    dd_status     = a.get("ddStatus")
    dd_quality    = a.get("ddQuality")
    replacing     = a.get("replacingTool")
    mig_vol       = a.get("migVol")
    capability    = a.get("capability")
    authority     = a.get("authority")
    team_count    = a.get("teamCount")
    product_count = a.get("productCount")
    sponsor       = a.get("sponsor")
    urgency       = a.get("urgency")
    compliance    = a.get("compliance")

    # Defer fires before any other shape. The signal is "IS budget is unlikely
    # to land or the deal will stall." Director+ sponsorship is the structural
    # gate for IS budget; without it (or without a forcing function like a
    # hard regulatory deadline) the engagement is premature.
    #
    # Forcing functions that override the weak-sponsor signal:
    #   urgency=hard   — external deadline forces budget escalation
    #   compliance=yes — regulatory exposure forces director attention
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

    # Wider Defer: manager-level sponsor with a small, low-pressure scope is
    # the "vanity tooling" pattern — a Director Of Something signs up but the
    # deal isn't substantial enough to maintain attention through delivery.
    if (
        sponsor == "manager"
        and team_count == "single"
        and product_count in {"1-2"}
        and not forcing_function
    ):
        return {
            "value": "Defer",
            "triggers": [
                ("sponsor", "manager"),
                ("teamCount", "single"),
                ("productCount", "1-2"),
                ("__note__", "small scope, no urgency or compliance forcing function"),
            ],
        }

    # Gap-filler precedes Foundation: a large migration into a new DD deployment
    # is shaped by the migration parity work, not by greenfield architectural
    # freedom. Only large/xl migrations fire Gap-filler; smaller migrations fall
    # through to Foundation.
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

    if dd_status == "live" and dd_quality == "good" and capability == "strong":
        return {
            "value": "Accelerator",
            "triggers": [
                ("ddStatus", "live"),
                ("ddQuality", "good"),
                ("capability", "strong"),
            ],
        }

    if (
        dd_status == "live"
        and dd_quality == "good"
        and authority == "central"
        and team_count in {"enterprise", "large"}
        and product_count in {"5-7", "suite"}
    ):
        return {
            "value": "Standards-setter",
            "triggers": [
                ("ddStatus", "live"),
                ("ddQuality", "good"),
                ("authority", "central"),
                ("teamCount", team_count or ""),
                ("productCount", product_count or ""),
            ],
        }

    # Fallback — treat as Foundation but signal low confidence in triggers.
    return {
        "value": "Foundation",
        "triggers": [("ddStatus", dd_status or "unknown"), ("__fallback__", "shape not cleanly derivable from inputs")],
    }


# ──────────────────────────────────────────────────────────────────
# Posture: IS-led | IS-advisory | IS-executes | IS-as-pattern-source
# ──────────────────────────────────────────────────────────────────

def compute_posture(a: dict) -> _Field:
    dd_status   = a.get("ddStatus")
    dd_quality  = a.get("ddQuality")
    replacing   = a.get("replacingTool")
    mig_vol     = a.get("migVol")
    capability  = a.get("capability")
    urgency     = a.get("urgency")
    authority   = a.get("authority")
    team_count  = a.get("teamCount")

    # Capability gap dominates everything — IS has to drive.
    if capability == "limited":
        return {"value": "IS-led", "triggers": [("capability", "limited")]}

    # IS-executes fires on heavy migration regardless of capability: the parity
    # work and cutover demand sustained hands-on attention that few customers
    # absorb cleanly alongside their normal load. Strong-capability customers
    # *can* execute themselves, but the default and safer scoping is IS-executes.
    if replacing == "yes" and mig_vol in {"l", "xl"}:
        return {
            "value": "IS-executes",
            "triggers": [("replacingTool", "yes"), ("migVol", mig_vol or "")],
        }

    if urgency == "hard" and capability != "strong":
        return {
            "value": "IS-executes",
            "triggers": [("urgency", "hard"), ("capability", capability or "unknown")],
        }

    # IS-advisory: customer has both capability and a live, healthy deployment —
    # IS supplies senior judgement at decision time, customer executes.
    if capability == "strong" and dd_status == "live" and dd_quality == "good":
        return {
            "value": "IS-advisory",
            "triggers": [
                ("capability", "strong"),
                ("ddStatus", "live"),
                ("ddQuality", "good"),
            ],
        }

    # Greenfield + non-strong capability falls back to IS-led after specific
    # patterns (migration / deadline / advisory) have had a chance to fire.
    if dd_status == "new" and capability != "strong":
        return {
            "value": "IS-led",
            "triggers": [("ddStatus", "new"), ("capability", capability or "unknown")],
        }

    # IS-as-pattern-source: enterprise-scale customer with central authority and
    # the capability to scale a pattern themselves — IS builds the first
    # instance, customer replicates.
    if (
        team_count in {"enterprise", "large"}
        and authority == "central"
        and capability in {"some", "strong"}
        and urgency != "hard"
    ):
        return {
            "value": "IS-as-pattern-source",
            "triggers": [
                ("teamCount", team_count or ""),
                ("authority", "central"),
                ("capability", capability or ""),
            ],
        }

    return {"value": "IS-led", "triggers": [("__fallback__", "posture not cleanly derivable from inputs")]}


# ──────────────────────────────────────────────────────────────────
# Dominant constraint
# ──────────────────────────────────────────────────────────────────

def compute_dominant_constraint(a: dict) -> _Field:
    capability    = a.get("capability")
    urgency       = a.get("urgency")
    dd_quality    = a.get("ddQuality")
    compliance    = a.get("compliance")
    team_count    = a.get("teamCount")
    authority     = a.get("authority")
    product_count = a.get("productCount")

    if capability == "limited":
        return {"value": "capability gap", "triggers": [("capability", "limited")]}

    if urgency == "hard":
        return {"value": "deadline", "triggers": [("urgency", "hard")]}

    if dd_quality == "messy":
        return {"value": "governance debt", "triggers": [("ddQuality", "messy")]}

    # multi-team precedes regulation when teamCount=="large" — the explicit
    # multi-BU case where fragmentation across teams is the active binding
    # constraint and regulation is contextual (per the FCA archetype).
    if team_count == "large":
        return {"value": "multi-team", "triggers": [("teamCount", "large")]}

    if compliance == "yes":
        return {"value": "regulation", "triggers": [("compliance", "yes")]}

    if team_count == "enterprise" and authority != "central":
        return {
            "value": "multi-team",
            "triggers": [("teamCount", "enterprise"), ("authority", authority or "unknown")],
        }

    if product_count == "suite" and team_count in {"enterprise", "large"}:
        return {
            "value": "scale",
            "triggers": [("productCount", "suite"), ("teamCount", team_count or "")],
        }

    return {
        "value": "none binding",
        "triggers": [("__note__", "engagement is tractable on standard sizing")],
    }


# ──────────────────────────────────────────────────────────────────
# Customer ownership — derived from (shape, posture) + conditional bullets
# ──────────────────────────────────────────────────────────────────

# Base bullets per (shape, posture). Pairs intentionally listed explicitly so
# the table is grep-able and easy to amend when archetypes get refined.
_OWNERSHIP_BASE: dict[tuple[str, str], list[str]] = {
    ("Foundation", "IS-led"): [
        "Commit named engineering capacity for the duration of the engagement.",
        "Stand up a platform team to inherit the deployed pattern.",
        "Appoint a CMDB / asset-owner role authoritative for service identity.",
    ],
    ("Foundation", "IS-advisory"): [
        "Execute the rollout — IS supplies designs, the platform team builds.",
        "Decide on the platform-team broker authority over keys, integrations, patterns.",
        "Curate CMDB attributes as authoritative source-of-truth for telemetry scoping.",
    ],
    ("Foundation", "IS-executes"): [
        "Designate the receiving team to take ownership at handover.",
        "Resource the parallel migration / cutover window the customer side.",
        "Own decommission of any legacy paths after parity sign-off.",
    ],
    ("Foundation", "IS-as-pattern-source"): [
        "Replicate the IS-built pattern across remaining teams.",
        "Provide internal training and pattern-divergence governance.",
        "Appoint a platform-engineering function to broker subsequent rollouts.",
    ],
    ("Accelerator", "IS-advisory"): [
        "Execution across every workstream — IS does not own the rollout, the platform team does.",
        "Workstream prioritisation — IS does not own the backlog.",
        "Cross-team coordination, including any third-party integration partners.",
        "Governance of the IS relationship — exec-level steering so prioritisation is the customer's call.",
    ],
    ("Accelerator", "IS-led"): [
        "Execute IS-led architectural decisions across the deployment.",
        "Resource cross-team coordination as IS guidance lands.",
        "Operate the deployment after each IS-led phase.",
    ],
    ("Accelerator", "IS-as-pattern-source"): [
        "Scale the IS-built pattern across teams without per-team IS hand-holding.",
        "Internal training and pattern adherence reviews.",
        "Cross-team coordination of pattern adoption sequencing.",
    ],
    ("Gap-filler", "IS-executes"): [
        "Named decommission owner for the legacy path.",
        "Parity-test sign-off ahead of cutover.",
        "Change-management ownership for the cutover window.",
    ],
    ("Gap-filler", "IS-led"): [
        "Resource the remediation work alongside IS.",
        "Decommission ownership and audit-trail sign-off.",
        "Standards adoption — accept and operate the IS-defined target state.",
    ],
    ("Gap-filler", "IS-advisory"): [
        "Execute the remediation work — IS supplies the target state and review.",
        "Decommission ownership and audit-trail sign-off.",
        "Cross-team alignment on the new standards.",
    ],
    ("Standards-setter", "IS-led"): [
        "Execute the pattern rollout to subsequent teams once IS has set the standard.",
        "Govern divergence from the pattern centrally.",
        "Resource ongoing pattern maintenance.",
    ],
    ("Standards-setter", "IS-advisory"): [
        "Codify and publish the IS-validated pattern internally.",
        "Govern pattern divergence centrally; route exceptions back to IS.",
        "Resource the platform team that brokers pattern adoption.",
    ],
    ("Standards-setter", "IS-as-pattern-source"): [
        "Replicate the IS-built reference deployment across remaining teams.",
        "Maintain the pattern as teams adopt — IS will not do per-team rollouts.",
        "Govern divergence centrally.",
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
    """Templated verdict prose for shape=Defer. Branches by which trigger
    fired so the verdict says something specific about *this* engagement,
    not a generic 'not yet IS' boilerplate.
    """
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
        # The vanity-tooling pattern: director-tier sponsor + small scope +
        # no forcing function.
        verdict = (
            "This is not yet an IS engagement. A director-tier sponsor exists, "
            "but the combination of small scope (single team, narrow product "
            "footprint) and no external forcing function is the vanity-tooling "
            "pattern. The sponsor approves the deal but disengages once it lands "
            "at the next quarterly priority shift. The commercial completes; the "
            "work does not get operationalised."
        )
    else:
        # Defensive fallback — shouldn't be reachable given the compute_shape rules.
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


def compute_customer_ownership(a: dict, shape: str, posture: str) -> list[str]:
    # Defer is a verdict, not an engagement. Surface next-step alternatives
    # rather than the customer-must-own bullets that other shapes produce.
    if shape == "Defer":
        return list(_DEFER_NEXT_STEPS)

    bullets: list[str] = list(_OWNERSHIP_BASE.get((shape, posture), [
        "Execution ownership — IS does not run the deployment.",
        "Prioritisation and cross-team coordination.",
    ]))

    if a.get("compliance") == "yes":
        bullets.append("Named security and legal stakeholder from session 1.")
    if a.get("replacingTool") == "yes" and not any("decommission" in b.lower() for b in bullets):
        bullets.append("Named decommission owner for the incumbent tool.")
    if a.get("authority") == "auto" and a.get("teamCount") != "single":
        bullets.append("Central authority delegated, or rollout will fragment across teams.")
    if _security_in_scope(a):
        bullets.append("Security ops and identity teams named as stakeholders from session 1.")

    return bullets


def _security_in_scope(a: dict) -> bool:
    """Effective securityScope: the explicit answer if asked, otherwise infer
    'yes' when productCount is 5-7 or suite (the questionnaire skips the
    explicit question for those breadths because they almost always include
    security products)."""
    explicit = a.get("securityScope")
    if explicit:
        return explicit == "yes"
    return a.get("productCount") in {"5-7", "suite"}


# ──────────────────────────────────────────────────────────────────
# Triggers — consolidated audit trail
# ──────────────────────────────────────────────────────────────────

def _build_triggers(
    shape: _Field, posture: _Field, constraint: _Field,
) -> list[Trigger]:
    by_signal: dict[tuple[str, str], list[str]] = {}

    for field_value, contrib_prefix in (
        (shape, "shape"),
        (posture, "posture"),
        (constraint, "constraint"),
    ):
        for signal, value in field_value["triggers"]:
            if signal.startswith("__"):
                continue
            key = (signal, value)
            by_signal.setdefault(key, []).append(f"{contrib_prefix}:{field_value['value']}")

    return [
        {"signal": sig, "value": val, "contributed_to": contribs}
        for (sig, val), contribs in by_signal.items()
    ]


# ──────────────────────────────────────────────────────────────────
# Public entrypoint
# ──────────────────────────────────────────────────────────────────

def diagnose(answers: dict) -> Diagnosis:
    """Return the full structured diagnosis for a set of answers.

    Deterministic: same answers → same diagnosis. No external calls.
    """
    shape = compute_shape(answers)
    posture = compute_posture(answers)
    constraint = compute_dominant_constraint(answers)
    triggers = _build_triggers(shape, posture, constraint)
    ownership = compute_customer_ownership(answers, shape["value"], posture["value"])

    return {
        "shape": shape,
        "posture": posture,
        "dominant_constraint": constraint,
        "triggers": triggers,
        "customer_ownership": ownership,
    }


# ──────────────────────────────────────────────────────────────────
# Commercial footer helpers — derived from the v1 recommend() output
# ──────────────────────────────────────────────────────────────────

def package_label(s_max: int | None) -> str:
    """Map the v1 session-estimate upper bound to a package name.

    Heuristic boundaries; tune as calibration data accrues.
    """
    if s_max is None:
        return "Resolve sponsor blocker first"
    if s_max <= 30:
        return "Starter"
    if s_max <= 60:
        return "Standard"
    if s_max <= 100:
        return "Enterprise"
    return "Multi-phase"
