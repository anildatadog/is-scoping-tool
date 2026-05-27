"""Static reference page — what each diagnosis means for the AE and what to do.

Output-first: 5 tabs, one per possible diagnosis. Compact content per tab —
"what to say / session shape / they commit / not this if". Vocabulary is in
a collapsed appendix at the bottom.

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
# Auth gate
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
st.caption("Pick the tab that matches your diagnosis. Each tab tells you how to position it to the customer, how the engagement shapes up, and what would have to be true for it to land differently.")


# ──────────────────────────────────────────────────────────────────
# 5 tabs — one per possible output
# ──────────────────────────────────────────────────────────────────

tab_foundation, tab_accel, tab_gap, tab_std, tab_defer = st.tabs([
    "🏗️ Foundation",
    "🚀 Accelerator",
    "🔧 Gap-filler",
    "📐 Standards-setter",
    "🛑 Defer",
])


def _tab_section(title: str, tagline: str, say: str, sessions: str,
                 commits: list[str], not_this_if: str) -> None:
    st.markdown(f"### {title}")
    st.markdown(f"*{tagline}*")
    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**📣 What to say**\n\n{say}")
        st.markdown(f"**⏱️ Session shape**\n\n{sessions}")
    with c2:
        commit_md = "\n".join(f"- {b}" for b in commits)
        st.markdown(f"**🤝 They commit**\n\n{commit_md}")
        st.markdown(f"**⚠️ Not this if**\n\n{not_this_if}")


with tab_foundation:
    _tab_section(
        title="🏗️ Foundation",
        tagline="Building Datadog from zero with the right operating model baked in from the start.",
        say='"Not just installing Datadog. Putting the operating model around it that lets it scale."',
        sessions="Discovery → architecture → pattern build → handover. **Architecture-heavy.**",
        commits=[
            "Named engineering capacity for the duration",
            "Platform team to inherit the deployed pattern",
            "CMDB / asset-owner role authoritative for service identity",
        ],
        not_this_if=(
            "Datadog is already running and they need a specific fix → **Gap-filler**. "
            "Mature at scale and want a blueprint to publish → **Standards-setter**."
        ),
    )

with tab_accel:
    _tab_section(
        title="🚀 Accelerator",
        tagline="Mature customer with the muscle to execute. They want IS judgement at decision time, not delivery labour.",
        say='"Datadog is installed and working. We accelerate your architectural decisions so you move faster than your change-management cadence would otherwise allow."',
        sessions="Proposals → written assessments → design reviews → walkthroughs. **Advisory-light, customer-paced.**",
        commits=[
            "Execution across every workstream (IS does not own the rollout)",
            "Workstream prioritisation (IS does not own the backlog)",
            "**Exec-level steering** so IS judgement stays visible — sessions consumed is a poor proxy for impact, surface architectural calls at exec cadence",
        ],
        not_this_if=(
            "Wants the pattern *published* across other teams as a blueprint → **Standards-setter**. "
            "Existing deployment has broken governance, not just architectural choices to make → **Gap-filler**."
        ),
    )

with tab_gap:
    _tab_section(
        title="🔧 Gap-filler",
        tagline="Something is broken or they're migrating. IS designs the target state and validates the cutover.",
        say='"We design the target state and validate the work. Hands-on migration is your team or a delivery partner — IS doesn\'t scale to that."',
        sessions=(
            "Audit → target-state design → cutover validation → decommission. **Phased per workstream.** "
            "_Note: high-volume migration (xl) shifts posture to **IS-led** — IS architects the target state, partner or customer team does the hands-on cutover. IS does not take heavy HOK at this volume._"
        ),
        commits=[
            "Named decommission owner + audit-trail sign-off",
            "Resource the hands-on remediation / migration (or engage a delivery partner)",
            "Standards adoption — operate the IS-defined target state",
        ],
        not_this_if=(
            "Governance hasn't broken and they're building from zero → **Foundation**. "
            "Existing deployment is healthy and they want architectural acceleration → **Accelerator**."
        ),
    )

with tab_std:
    _tab_section(
        title="📐 Standards-setter",
        tagline="Mature customer wants a replicable blueprint. IS designs the pattern; customer replicates.",
        say='"We build the reference and the pilot. Your platform team replicates it to the rest of the org. No per-team rollouts from IS."',
        sessions="Pattern design → pilot build → documentation → handover. **Tight, no per-team scaling.**",
        commits=[
            "Replication ownership across remaining teams",
            "Internal training and pattern-divergence governance",
            "**Central authority** to govern divergence — without a broker function the pattern won't land; push back before scoping if absent",
        ],
        not_this_if=(
            "Wants IS to *scale the rollout* per team rather than just design the pattern → **Accelerator** (advisory) or **Foundation** (with broker authority). "
            "Existing governance has broken and the standard is corrective remediation, not a forward blueprint → **Gap-filler**."
        ),
    )

with tab_defer:
    st.markdown("### 🛑 Defer")
    st.markdown("*This isn't an IS engagement yet. Datadog the product still delivers value; TAM supports ongoing advisory; a delivery partner handles execution-heavy needs.*")
    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            "**📣 What to say**\n\n"
            '"Datadog will work for you. IS specifically needs director-or-above sponsorship to land — without it the engagement stalls at budget approval or loses attention mid-delivery. Let\'s set you up with TAM coverage and revisit IS when the conditions are right."'
        )
        st.markdown(
            "**🎯 Why now**\n\n"
            "Sponsor signal is structurally weak (no champion, engineer-only, or vanity-tooling pattern) AND no forcing function (regulatory deadline, compliance audit, hard contract date) exists to compel exec attention."
        )
    with c2:
        st.markdown(
            "**🆘 Escalate**\n\n"
            "If you read this differently, contact Fred (IS management sponsor): "
            "`frederique.martinsainteagathe@datadoghq.com`."
        )
        st.markdown(
            "**🔁 When to revisit**\n\n"
            "Director+ champion is named, OR an external forcing function appears (regulatory deadline, compliance audit, hard contract date)."
        )


# ──────────────────────────────────────────────────────────────────
# Definitions appendix — collapsed by default
# ──────────────────────────────────────────────────────────────────

with st.expander("📖 Vocabulary — postures, constraints, triggers, ownership"):
    st.markdown(
        """
**Posture** describes what IS actually does — the customer-IS dynamic. Derived from capability + scope + urgency.

| Posture | What it means |
|---|---|
| 🎯 IS-led | IS owns architecture decisions and drives the engagement |
| 🧭 IS-advisory | IS reviews and proposes; customer executes |
| 🔨 IS-executes | IS does the hands-on work alongside the customer (moderate migrations only — high-volume goes IS-led + partner) |
| 📋 IS-as-pattern-source | IS builds the first instance; customer replicates |

**Dominant constraint** — priority order, only one wins:

| # | Constraint | Wins when |
|---|---|---|
| 1 | capability gap | `capability = limited` — dominates everything; knowledge transfer is the engagement |
| 2 | deadline | `urgency = hard` — scope negotiates down, sessions never compress |
| 3 | governance debt | `ddQuality = messy` — audit + remediation come first |
| 4 | multi-team | `teamCount = large` — fragmentation is the binding cost |
| 5 | regulation | `compliance = yes` — only if nothing higher fires |
| 6 | multi-team (soft) | `teamCount = enterprise` and `authority ≠ central` |
| 7 | scale | 3+ scope add-ons selected with `teamCount` enterprise/large |

**Triggers** — every diagnosis shows which inputs fired it. Override the answer if a trigger looks wrong; the rule engine is deterministic.

**Customer ownership** bullets — composed from `(shape, posture)` plus conditional bullets driven by specific inputs (compliance, replacingTool, infraTopology, productScope). Use them in the pre-close conversation with the customer.

**Commercial** — session estimates are the v1 sizing math. Above ~80 sessions the number is withheld and the engagement is flagged Multi-phase. Heuristic; calibration data pending.
"""
    )
