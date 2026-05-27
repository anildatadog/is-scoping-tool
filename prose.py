"""LLM prose layer — wraps the structured diagnosis (slice 1) with two
consulting-voice paragraphs (diagnosis + consequence).

Single Anthropic API call with prompt caching on the system prompt + few-shot
prefix. Returns None on any failure so the caller can render the structured
diagnosis without the prose layer (graceful fallback).
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import TypedDict

import anthropic

log = logging.getLogger(__name__)


class ProseOutput(TypedDict):
    diagnosis_paragraph: str
    consequence_paragraph: str


SYSTEM_PROMPT = """You are the prose layer of an internal Datadog Implementation Services (IS) scoping tool.

You receive:
1. A structured diagnosis of an IS engagement (shape, posture, dominant constraint, customer ownership bullets)
2. The 11 raw answers the diagnosis was derived from

You produce a JSON object with exactly two fields:
- diagnosis_paragraph: a single architect's-brief paragraph (4 to 8 sentences) describing the engagement shape, posture, and the core architectural challenge in IS-Europe's consulting voice
- consequence_paragraph: a single paragraph (4 to 8 sentences) describing what happens without IS, framed as the alternative cost (why this customer needs IS specifically rather than TAM, partner, or in-house resourcing)

Return ONLY the JSON object. No code fences, no preamble, no explanatory text.

VOICE RULES (mandatory)
- Write like a senior consulting engineer briefing a senior peer. Direct, opinionated, structured. No filler, no warm openings, no "I" or "we" hedging.
- Reference IS-Europe operating-model PATTERNS by their archetype name (Foundation, Accelerator, Gap-filler, Standards-setter). Never by past customer names.
- Customers may not be named in your output. Only use the inputs you were given.
- Hands-on consulting depth applied at decision time is the function being offered. Do not describe IS as a delivery function or implementation labour.
- No em dashes. Use commas, full stops, or colons.

CONSTRAINT RULES (mandatory)
- Do NOT propose a Center of Excellence. No CoE playbook exists at Datadog.
- Do NOT describe Technical Account Managers (TAMs) as hands-on. TAMs are advisory only.
- Do NOT cite specific session counts, dates, dollar values, or named individuals. Those live in the structured fields the AE already sees.
- Do NOT invent customer-specific facts. If a fact is not in the structured diagnosis or the raw inputs, it does not exist.
- If posture is IS-advisory: the consequence_paragraph MUST name the invisibility risk explicitly. AEs and customers can mistake quietness for absence-of-value. IS must surface its judgement clearly and on time. Sessions consumed is a poor proxy for impact unless deliberately reframed.

TONE CALIBRATION
Two examples follow. Match the voice. Do not copy the content."""


_BA_INPUT = {
    "structured_diagnosis": {
        "shape": "Foundation",
        "posture": "IS-led",
        "dominant_constraint": "regulation",
        "customer_ownership": [
            "Commit named engineering capacity for the duration of the engagement.",
            "Stand up a platform team to inherit the deployed pattern.",
            "Appoint a CMDB / asset-owner role authoritative for service identity.",
            "Named security and legal stakeholder from session 1.",
            "Security ops and identity teams named as stakeholders from session 1.",
        ],
    },
    "answers": {
        "ddStatus": "new", "replacingTool": "no",
        "teamCount": "enterprise", "productCount": "5-7",
        "sponsor": "exec", "authority": "central",
        "capability": "strong", "urgency": "flex",
        "compliance": "yes", "securityScope": "yes",
    },
}

_BA_OUTPUT = {
    "diagnosis_paragraph": (
        "Foundation engagement, regulated enterprise context. The customer is building the "
        "operating model from zero with the right structure baked in from the start, rather "
        "than retrofitting governance over an existing sprawl. The signals are multiple cloud "
        "accounts forming fragmented organisational boundaries, diverse compute runtimes "
        "demanding distinct enablement patterns, and a platform engineering function that "
        "exists but has not yet been granted broker authority over keys, integrations, and "
        "patterns. The work is to make governance structural rather than procedural: project "
        "CMDB ownership downward through cloud account tags into RBAC so access is inherited "
        "not granted, and operate two lanes. A standard lane the platform owns and product "
        "teams execute. A complex lane that mandates platform engagement before any custom "
        "instrumentation, non-standard logging, or new integration commits. Autonomy at the "
        "edge, absolute control at the core."
    ),
    "consequence_paragraph": (
        "Without IS-led architecture at decision time, the failure mode is the one every "
        "regulated enterprise hits at this stage. The tool installs cleanly, deployments "
        "scale, governance does not. API keys leak across teams. Shadow integrations appear "
        "because nothing structurally prevents them. RBAC becomes a manual grant queue. "
        "Audit conversations get harder every quarter because nothing is mechanically "
        "traceable to a CMDB owner. Datadog as a product cannot do this work. A TAM cannot "
        "own architecture decisions or build. A partner can execute a pattern but cannot "
        "define one. The function that fits is implementation services with consulting "
        "depth, applied at decision time, before drift becomes debt."
    ),
}

_FCA_INPUT = {
    "structured_diagnosis": {
        "shape": "Accelerator",
        "posture": "IS-advisory",
        "dominant_constraint": "multi-team",
        "customer_ownership": [
            "Execution across every workstream. IS does not own the rollout, the platform team does.",
            "Workstream prioritisation. IS does not own the backlog.",
            "Cross-team coordination, including any third-party integration partners.",
            "Governance of the IS relationship. Exec-level steering so prioritisation is the customer's call.",
            "Named security and legal stakeholder from session 1.",
        ],
    },
    "answers": {
        "ddStatus": "live", "ddQuality": "good",
        "teamCount": "large", "productCount": "5-7",
        "sponsor": "exec", "authority": "central",
        "capability": "strong", "urgency": "flex",
        "compliance": "yes", "securityScope": "no",
    },
}

_FCA_OUTPUT = {
    "diagnosis_paragraph": (
        "Accelerator engagement. The customer already has the platform, the patterns, the "
        "people, and the org structure. They are not building from zero and they are not "
        "retrofitting governance over a sprawl. What they want from IS is accelerated "
        "decisions and validated architectural choices, so they can move faster than internal "
        "change-management cadence would otherwise allow. The fragility is not capability. "
        "It is making consistent choices fast enough across a broad surface of product groups "
        "and services before drift accumulates. Two lanes operate naturally: a standard lane "
        "the platform owns and product teams execute, and a complex lane that mandates IS "
        "engagement before any custom instrumentation, non-standard logging, or new "
        "integration commits."
    ),
    "consequence_paragraph": (
        "Without IS in the advisory role, the customer has the muscle to implement Datadog "
        "but no external pressure to make the right architectural decisions at decision time. "
        "The failure mode is slow rather than acute. Each product group makes locally correct "
        "choices, the platform fragments, tagging drift accumulates, the monitor estate "
        "becomes ungovernable, and the second-order asks get structurally blocked because the "
        "foundation was never aligned. A TAM cannot make those calls because TAMs are not "
        "hands-on. A partner can execute against a pattern but cannot define one. The honest "
        "second-order risk to name is the advisory posture's own failure mode: invisibility. "
        "If IS does not surface its judgement clearly and on time, the customer's execution "
        "moves on without architectural review, and the engagement's value is unreadable at "
        "renewal. Sessions consumed becomes a poor proxy for impact unless deliberately reframed."
    ),
}


def _few_shot_messages() -> list[dict]:
    """Two-shot exchange, with cache_control on the final assistant block so the
    whole few-shot prefix is cached across requests."""
    return [
        {"role": "user", "content": json.dumps(_BA_INPUT, indent=2)},
        {"role": "assistant", "content": json.dumps(_BA_OUTPUT, indent=2)},
        {"role": "user", "content": json.dumps(_FCA_INPUT, indent=2)},
        {"role": "assistant", "content": [{
            "type": "text",
            "text": json.dumps(_FCA_OUTPUT, indent=2),
            "cache_control": {"type": "ephemeral"},
        }]},
    ]


# Strip any literal mention of known portfolio archetype customer names that
# may have leaked from the few-shot examples into the model's output. The
# system prompt forbids this, but guardrail belt-and-braces.
_FORBIDDEN_NAMES = re.compile(
    r"\b(?:BA|British Airways|FCA|Financial Conduct Authority|Chalhoub|"
    r"Core42|Munich Re|Telstra|Haleon|Base44|Momentum)\b"
)


def _redact(text: str) -> str:
    return _FORBIDDEN_NAMES.sub("[redacted]", text)


def generate(diagnosis: dict, answers: dict) -> ProseOutput | None:
    """Generate the diagnosis + consequence paragraphs.

    Returns None on any failure (missing key, API error, parse error). Caller
    must handle None by rendering the structured diagnosis without prose.

    For shape=Defer, returns None — the caller should render the templated
    verdict from diagnosis.compute_defer_verdict() instead. Defer is a verdict
    and reads better from a deterministic template than an LLM paragraph.
    """
    if diagnosis["shape"]["value"] == "Defer":
        return None

    # Strip whitespace defensively — Secret Manager values can include a
    # trailing newline when provisioned via `op read | gcloud secrets create`,
    # which causes the SDK to construct an invalid x-api-key header (newlines
    # are illegal in HTTP header values) and leak the key into the error log.
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        log.warning("ANTHROPIC_API_KEY not set; skipping prose generation")
        return None

    request_input = {
        "structured_diagnosis": {
            "shape": diagnosis["shape"]["value"],
            "posture": diagnosis["posture"]["value"],
            "dominant_constraint": diagnosis["dominant_constraint"]["value"],
            "customer_ownership": diagnosis["customer_ownership"],
        },
        "answers": answers,
    }

    try:
        client = anthropic.Anthropic(api_key=api_key)
        messages = _few_shot_messages() + [
            {"role": "user", "content": json.dumps(request_input, indent=2)},
        ]
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
        )

        text = next((b.text for b in response.content if b.type == "text"), "")
        if not text.strip():
            log.warning("empty LLM response; falling back to structured-only")
            return None

        parsed = json.loads(text)
        return ProseOutput(
            diagnosis_paragraph=_redact(parsed["diagnosis_paragraph"]),
            consequence_paragraph=_redact(parsed["consequence_paragraph"]),
        )

    except (anthropic.APIError, json.JSONDecodeError, KeyError, ValueError):
        log.exception("prose generation failed; falling back to structured-only")
        return None
