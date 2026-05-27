"""Static reference page — explains the v2 diagnosis vocabulary.

Auto-discovered by Streamlit via the pages/ folder. The OAuth + domain-check
gate is duplicated from streamlit_app.py because each page runs as its own
module on entry; we keep it inline rather than extract to a helper so a future
reader can see the gate without chasing imports.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="How to read the diagnosis · IS Scoping Tool",
    page_icon="🧭",
    layout="centered",
)

# ──────────────────────────────────────────────────────────────────
# Auth gate — Datadog Google Workspace only (mirrors streamlit_app.py)
# ──────────────────────────────────────────────────────────────────
if not getattr(st, "user", None) or not st.user.is_logged_in:
    st.title("🧭 IS Scoping Tool")
    st.write("Sign in with your Datadog Google account to continue.")
    st.button("Sign in with Google", type="primary", on_click=st.login, args=("google",))
    st.stop()

_email = (st.user.email or "").lower()
if not _email.endswith("@datadoghq.com"):
    st.error("Access restricted to Datadog employees.")
    st.button("Sign out", on_click=st.logout)
    st.stop()


# ──────────────────────────────────────────────────────────────────
# Content
# ──────────────────────────────────────────────────────────────────

st.title("How to read the diagnosis")

st.markdown(
    """
The scoping tool produces a **structured diagnosis** from 11 inputs, not a SKU recommendation. Three labels and a triggers list. This page explains what the labels mean and how to use them.
"""
)

st.divider()

st.header("Shape · what the engagement is")

st.markdown(
    """
Four values. Pick the one that fits the customer's starting position, not what they say they want.

**Foundation.** Building the operating model from zero with the right structure baked in from the start. Greenfield deployment, or an explicit rebuild. Fires when `ddStatus = new`, or when `ddQuality = rebuild` and no incumbent tool is being replaced.

*What this implies for design.* Every architectural decision is yours to set. The customer hasn't accumulated drift yet, so the work is establishing standards rather than fixing broken ones.

**Accelerator.** Mature customer, has platform muscle, wants design decisions accelerated. The tool is installed, the patterns exist, the people are competent. Fires when `ddStatus = live`, `ddQuality = good`, and `capability = strong`.

*What this implies for design.* IS does not own execution. The work shows up as architectural review, proposals, and validation of the customer's own design work. Customer pace runs faster than session cadence.

**Gap-filler.** Fixing something broken, or unblocking a large migration. Fires when `ddQuality = messy` (governance broke down), or when a large incumbent-tool migration is in scope (`replacingTool = yes` and `migVol in l/xl`).

*What this implies for design.* Scope is determined by the existing mess or the incumbent tool's footprint, not by what the customer would ideally build from scratch. Parity sign-off and decommission ownership are gating concerns.

**Standards-setter.** Replicable blueprint. Customer wants you to define a pattern others will adopt. Fires when `ddStatus = live`, `ddQuality = good`, `authority = central`, broad scale, and capability is not strong (otherwise Accelerator takes precedence).

*What this implies for design.* Output is a pattern document plus a pilot, not a deployment for everyone. Replication is the customer's responsibility.
"""
)

st.divider()

st.header("Posture · what IS and customer each own")

st.markdown(
    """
Four values. Pick the one that matches the work IS will actually do.

**IS-led.** IS owns architecture decisions and drives the engagement. Customer is a learner or a passive partner. Fires when capability is limited, or when greenfield meets not-strong capability.

**IS-advisory.** IS provides architectural review; the customer executes. The customer is mature enough to operate the deployment but wants senior judgement at decision time. The work shows up as proposals, written assessments, design reviews, and walkthroughs.

*The honest second-order risk to name: invisibility.* IS does work that is not sessions-visible. Sessions consumed becomes a poor proxy for impact unless deliberately reframed. The advisory posture has to be governed at exec level on the customer side, or the engagement's value goes unread at renewal.

**IS-executes.** IS does the hands-on work alongside the customer. Migration heavy lift, or deadline pressure that the customer cannot shoulder alone. Fires on large migrations, or on hard deadlines with non-strong capability.

**IS-as-pattern-source.** IS builds the first instance of a pattern; the customer replicates across remaining teams. Fires at enterprise scale with central authority and capability sufficient to scale a pattern themselves.
"""
)

st.divider()

st.header("Dominant constraint · what is binding")

st.markdown(
    """
Priority order matters. The most binding constraint wins; only one fires.

1. **capability gap.** Limited capability dominates everything. Engagement design centres on knowledge transfer.
2. **deadline.** Hard external deadline. Always negotiate scope down rather than compress sessions.
3. **governance debt.** `ddQuality = messy`. Audit and remediation come before new deployment work.
4. **multi-team.** `teamCount = large` (explicit multi-BU case). Beats regulation when it fires, because fragmentation is the active driver and regulation is contextual.
5. **regulation.** `compliance = yes`. Dominant only when nothing higher fires; otherwise it stays in the background.
6. **multi-team (soft).** `teamCount = enterprise` and `authority != central`. Like multi-team above but less acute.
7. **scale.** Full suite plus enterprise/large teams. Last because it usually shows up *with* something more binding.
"""
)

st.divider()

st.header("Triggers · the audit trail")

st.markdown(
    """
Every diagnosis shows the inputs that fired it. This is for transparency, not decoration. If a trigger looks wrong, override the answer via the questionnaire before relying on the diagnosis. The structure is deterministic: same answers in, same diagnosis out.
"""
)

st.divider()

st.header("Customer ownership")

st.markdown(
    """
The bullets list what the customer must own for the engagement to land. Composed from the (shape, posture) pair plus conditional bullets driven by specific inputs (compliance stakeholders, decommission owners, security ops, authority delegation).

Use the bullets as the pre-close conversation with the AE. *These are things the customer has to commit to; otherwise the engagement will stall.* If they cannot commit, that is information about the deal, not just the engagement.
"""
)

st.divider()

st.header("Commercial · heuristic, calibration pending")

st.markdown(
    """
The session estimate is the v1 sizing math, retained because we have no calibration data yet. Treat the number as a range, not a commitment. The package label (Starter / Standard / Enterprise / Multi-phase) is a function of the upper bound, useful for SOW templating but not for sales pricing.

The estimate becomes calibrated once 5 to 10 completed engagements give us actual session counts to compare against. Until then, honest framing in proposals: *"based on heuristic sizing; we will refine post-discovery."*
"""
)

st.divider()

st.caption(
    "This page describes the locked v2 diagnosis schema. Implementation status: "
    "structured layer (rule-based) and prose layer (Claude Opus 4.7) are live; "
    "RAG corpus over woof!-managed customer summaries is deferred."
)
