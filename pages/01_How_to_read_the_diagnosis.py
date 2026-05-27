"""Static reference page — explains the v2 diagnosis vocabulary.

Auto-discovered by Streamlit via the pages/ folder. The OAuth + domain-check
gate is duplicated from the entry script because each page runs as its own
module on entry.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="How to read the diagnosis · IS Scoping Tool",
    page_icon="🧭",
    layout="wide",
)

# ──────────────────────────────────────────────────────────────────
# Auth gate — Datadog Google Workspace only
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
# Hero
# ──────────────────────────────────────────────────────────────────

st.title("🧭 How to read the diagnosis")
st.markdown(
    """
The tool produces a **structured diagnosis** from 11 inputs, not a SKU recommendation.
Three labels and an audit trail tell you what kind of engagement this is, who owns what, and what's binding.
"""
)


# ──────────────────────────────────────────────────────────────────
# Shape × Posture matrix
# ──────────────────────────────────────────────────────────────────

st.markdown("##### The two main axes")

st.markdown(
    """
<style>
.matrix-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.matrix-table th, .matrix-table td { padding: 10px 12px; border: 1px solid #2a2a2a; text-align: left; vertical-align: top; }
.matrix-table th { background: #1c1c1c; color: #fff; font-weight: 500; }
.matrix-table td { background: #111; color: #ddd; }
.matrix-table .row-header { background: #1c1c1c; color: #fff; font-weight: 500; width: 18%; }
.matrix-table .cell-emph { color: #ffaa55; }
</style>
<table class="matrix-table">
  <thead>
    <tr>
      <th></th>
      <th>🎯 IS-led<br/><span style="opacity:.6;font-weight:400;">IS owns architecture</span></th>
      <th>🧭 IS-advisory<br/><span style="opacity:.6;font-weight:400;">IS reviews, customer executes</span></th>
      <th>🔨 IS-executes<br/><span style="opacity:.6;font-weight:400;">Hands-on alongside customer</span></th>
      <th>📋 IS-as-pattern-source<br/><span style="opacity:.6;font-weight:400;">IS builds pilot, customer scales</span></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="row-header">🏗️ <strong>Foundation</strong><br/><span style="opacity:.6;font-weight:400;">Building from zero</span></td>
      <td>Greenfield + limited capability. IS sets every architectural pattern.</td>
      <td>Greenfield + strong customer. IS designs, platform team builds.</td>
      <td>Greenfield migration into new DD. Hands-on cutover.</td>
      <td>Greenfield + enterprise scale + central authority. Build the pilot, customer replicates.</td>
    </tr>
    <tr>
      <td class="row-header">🚀 <strong>Accelerator</strong><br/><span style="opacity:.6;font-weight:400;">Mature, wants design help</span></td>
      <td>Mature with capability gap on a specific topic. Rare.</td>
      <td class="cell-emph">The common Accelerator. Customer has the muscle; IS provides architectural judgement at decision time.</td>
      <td>Heavy migration on top of a mature deployment.</td>
      <td>Mature customer wants a reference pattern to scale internally.</td>
    </tr>
    <tr>
      <td class="row-header">🔧 <strong>Gap-filler</strong><br/><span style="opacity:.6;font-weight:400;">Fix broken or migrate</span></td>
      <td>Governance broke down and customer can't lead the remediation.</td>
      <td>Customer leads remediation; IS prescribes the target state.</td>
      <td class="cell-emph">The common Gap-filler. Large migration or governance debt; IS does the hands-on work.</td>
      <td>Build a clean reference; customer migrates teams onto it.</td>
    </tr>
    <tr>
      <td class="row-header">📐 <strong>Standards-setter</strong><br/><span style="opacity:.6;font-weight:400;">Replicable blueprint</span></td>
      <td>IS authors the standard; customer adopts it after.</td>
      <td>IS validates the customer's draft standard.</td>
      <td>Rare — execution by IS is unusual for a Standards-setter engagement.</td>
      <td>Natural fit. Build the first instance, customer replicates.</td>
    </tr>
  </tbody>
</table>
""",
    unsafe_allow_html=True,
)

st.caption(
    "Cells in **orange** are the most common shape × posture combinations. "
    "Other cells are valid but should make you pause and confirm with the AE."
)

st.divider()


# ──────────────────────────────────────────────────────────────────
# Shape detail cards
# ──────────────────────────────────────────────────────────────────

st.header("Shape")
st.caption("What kind of engagement is this, in one word?")

c1, c2 = st.columns(2)
with c1:
    st.markdown(
        """
##### 🏗️ Foundation
*Building the operating model from zero with the right structure baked in from the start.*

**Fires when** `ddStatus = new`, or `ddQuality = rebuild` with no incumbent.

**Design implication.** Every architectural decision is yours to set. The customer hasn't accumulated drift; the work is establishing standards rather than fixing broken ones.
"""
    )
    st.markdown(
        """
##### 🔧 Gap-filler
*Fixing something broken or unblocking a large migration.*

**Fires when** `ddQuality = messy`, or large incumbent-tool migration (`replacingTool = yes` and `migVol in l/xl`).

**Design implication.** Scope is determined by the existing mess or the incumbent tool's footprint. Parity sign-off and decommission ownership are gating concerns.
"""
    )
with c2:
    st.markdown(
        """
##### 🚀 Accelerator
*Mature customer, has platform muscle, wants design decisions accelerated.*

**Fires when** `ddStatus = live`, `ddQuality = good`, `capability = strong`.

**Design implication.** IS does not own execution. Work shows up as architectural review, proposals, validation. Customer pace runs faster than session cadence.
"""
    )
    st.markdown(
        """
##### 📐 Standards-setter
*Replicable blueprint. Customer wants you to define a pattern others will adopt.*

**Fires when** mature + central authority + broad scope, and capability is not strong (otherwise Accelerator wins).

**Design implication.** Output is a pattern + a pilot, not a deployment for everyone. Replication is the customer's responsibility.
"""
    )

st.divider()


# ──────────────────────────────────────────────────────────────────
# Defer — the fifth output (verdict, not engagement)
# ──────────────────────────────────────────────────────────────────

st.header("Plus: the verdict — Defer")

st.error(
    "🛑 **Defer — this is not yet an IS engagement.** Surfaces when the sponsor signal is structurally weak "
    "and no forcing function (regulatory deadline, compliance audit) exists to compel exec attention. "
    "Director-or-above sponsorship is the structural gate for IS budget."
)

dc1, dc2, dc3 = st.columns(3)
with dc1:
    st.markdown(
        """
**No champion**
`sponsor = none` →
no budget owner, no internal advocate
"""
    )
with dc2:
    st.markdown(
        """
**Engineer-only sponsorship**
`sponsor = engineer`
without forcing function →
will stall at budget approval
"""
    )
with dc3:
    st.markdown(
        """
**Vanity tooling**
`sponsor = manager` +
single team + 1-2 products +
no pressure →
sponsor disengages mid-delivery
"""
    )

st.info(
    "Override: `urgency = hard` OR `compliance = yes` overrides the engineer/manager Defer rules. "
    "A regulatory deadline or compliance audit forces directors to allocate budget, "
    "and an engineer-level champion can credibly escalate."
)

st.divider()


# ──────────────────────────────────────────────────────────────────
# Posture
# ──────────────────────────────────────────────────────────────────

st.header("Posture")
st.caption("What does IS actually do, and what does the customer own?")

p1, p2 = st.columns(2)
with p1:
    st.markdown(
        """
##### 🎯 IS-led
IS owns architecture decisions and drives the engagement. Customer is a learner or passive partner. Fires on limited capability, or greenfield + non-strong capability.
"""
    )
    st.markdown(
        """
##### 🔨 IS-executes
IS does the hands-on work alongside the customer. Migration heavy lift, or hard deadline that the customer can't shoulder alone.
"""
    )
with p2:
    st.markdown(
        """
##### 🧭 IS-advisory
IS provides architectural review; the customer executes. Mature customer that wants senior judgement at decision time. Work shows up as proposals, written assessments, design reviews, walkthroughs.
"""
    )
    st.warning(
        "**Honest second-order risk to name: invisibility.** IS does work that isn't sessions-visible. "
        "Sessions consumed becomes a poor proxy for impact unless deliberately reframed. "
        "The advisory posture must be governed at exec level on the customer side, "
        "or the engagement's value goes unread at renewal."
    )
    st.markdown(
        """
##### 📋 IS-as-pattern-source
IS builds the first instance of a pattern; the customer replicates across remaining teams. Enterprise scale with central authority and capacity to scale a pattern themselves.
"""
    )

st.divider()


# ──────────────────────────────────────────────────────────────────
# Dominant constraint
# ──────────────────────────────────────────────────────────────────

st.header("Dominant constraint")
st.caption("Priority order — only one wins. The most binding constraint dominates.")

st.markdown(
    """
| # | Constraint | Wins when |
|---|---|---|
| 1 | **capability gap** | `capability = limited` — dominates everything. Knowledge transfer is the engagement. |
| 2 | **deadline** | `urgency = hard` — negotiate scope down, never compress sessions. |
| 3 | **governance debt** | `ddQuality = messy` — audit + remediation precede new work. |
| 4 | **multi-team** | `teamCount = large` — explicit multi-BU case; beats regulation when fragmentation is the active driver. |
| 5 | **regulation** | `compliance = yes` — dominant only when nothing higher fires; otherwise contextual. |
| 6 | **multi-team (soft)** | `teamCount = enterprise` and `authority ≠ central` — less acute fragmentation. |
| 7 | **scale** | `productCount = suite` with enterprise/large teams — usually shows up with something more binding. |
"""
)

st.divider()


# ──────────────────────────────────────────────────────────────────
# Triggers + ownership + commercial
# ──────────────────────────────────────────────────────────────────

st.header("Triggers — the audit trail")
st.caption("Every diagnosis shows you which inputs fired it. Override the answer if the trigger looks wrong.")

st.code(
    """ddStatus       = live       → shape:Accelerator, posture:IS-advisory
ddQuality      = good       → shape:Accelerator, posture:IS-advisory
capability     = strong     → shape:Accelerator, posture:IS-advisory
teamCount      = large      → constraint:multi-team""",
    language="text",
)

st.markdown("The structure is **deterministic**: same answers in, same diagnosis out.")

st.divider()

st.header("Customer ownership")

st.markdown(
    """
The bullets list what the customer must own for the engagement to land. Composed from the `(shape, posture)` pair plus conditional bullets driven by specific inputs (compliance stakeholders, decommission owners, security ops, authority delegation).

> **Use the bullets as the pre-close conversation with the AE.**
> *"These are things the customer has to commit to; otherwise the engagement will stall."*
> If they can't commit, that's information about the deal, not just the engagement.
"""
)

st.divider()

st.header("Commercial · heuristic, calibration pending")

st.warning(
    "Session estimates are the v1 sizing math, retained because we have **no calibration data yet**. "
    "Treat the number as a range, not a commitment."
)

st.markdown(
    """
The package label (Starter / Standard / Enterprise / Multi-phase) is a function of the upper bound, useful for SOW templating but not for sales pricing.

The estimate becomes calibrated once 5 to 10 completed engagements give us actual session counts to compare against. Until then, honest framing in proposals: *"based on heuristic sizing; we will refine post-discovery."*
"""
)

st.divider()

st.caption(
    "Implementation status: structured diagnosis (rule-based) and prose layer "
    "(Claude Opus 4.7) are live. Defer verdict uses a deterministic template. "
    "RAG corpus over woof!-managed customer summaries is deferred."
)
