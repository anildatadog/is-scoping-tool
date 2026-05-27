"""IS Scoping Tool — Streamlit UI.

Three screens: search, questionnaire, result. State held in st.session_state.
"""
from __future__ import annotations

import streamlit as st

from diagnosis import diagnose, package_label
from methodologies import build_flags, build_next_steps, recommend, visible_questions
from scoping_doc import build as build_scoping_doc

try:
    import snowflake_lookup as sf
    SNOWFLAKE_AVAILABLE = True
except Exception:
    SNOWFLAKE_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────
# Page config + state init
# ──────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IS Scoping Tool",
    page_icon="🧭",
    layout="centered",
)

# ──────────────────────────────────────────────────────────────────
# Auth: Datadog Google Workspace only
# ──────────────────────────────────────────────────────────────────
# Streamlit's native auth (1.42+) reads OAuth config from .streamlit/secrets.toml;
# the entrypoint writes that file from env vars at container start.
# `hd=datadoghq.com` in client_kwargs filters at Google's auth screen, and we
# also verify the email domain server-side as defense in depth.

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


if "screen" not in st.session_state:
    st.session_state.screen = "search"
    st.session_state.sf_data = None
    st.session_state.answers = {}
    st.session_state.step = 0
    st.session_state.search_results = []
    st.session_state.search_error = None
    st.session_state.prefilled_keys = set()


def reset_to_search() -> None:
    st.session_state.screen = "search"
    st.session_state.sf_data = None
    st.session_state.answers = {}
    st.session_state.step = 0
    st.session_state.search_results = []
    st.session_state.search_error = None
    st.session_state.prefilled_keys = set()


def remaining_questions(answers: dict) -> list[dict]:
    """Visible questions (per branching) that the user still needs to answer."""
    return [q for q in visible_questions(answers) if not answers.get(q["id"])]


def goto_next_after_search(sf_data: dict | None) -> None:
    """After SF lookup (or skip), pick the right next screen:
    - SF prefilled some answers → review screen so the AE can confirm/edit them
    - Nothing prefilled (skip path) → straight into the questionnaire
    """
    st.session_state.sf_data = sf_data
    if sf_data and sf_data.get("prefill"):
        st.session_state.answers = dict(sf_data["prefill"])
        st.session_state.prefilled_keys = set(sf_data["prefill"].keys())
        st.session_state.screen = "review"
    else:
        st.session_state.answers = {}
        st.session_state.prefilled_keys = set()
        st.session_state.screen = "questionnaire"
    st.session_state.step = 0


def advance_from_review() -> None:
    """Continue from the review screen: if any questions remain (or branching
    just opened new ones), go to the questionnaire. Otherwise jump to result."""
    st.session_state.step = 0
    if remaining_questions(st.session_state.answers):
        st.session_state.screen = "questionnaire"
    else:
        st.session_state.screen = "result"


# ──────────────────────────────────────────────────────────────────
# Search screen
# ──────────────────────────────────────────────────────────────────

def render_search() -> None:
    st.title("🧭 IS Scoping Tool")
    st.caption("Size a Datadog Implementation Services engagement in 11 questions.")

    if not SNOWFLAKE_AVAILABLE:
        st.warning("Snowflake module not loaded — lookup disabled. You can still answer the questions manually.")

    st.subheader("Find the opportunity")
    st.caption("Enter the Salesforce opportunity ID (`006...`) or part of the account name.")

    query = st.text_input("Search", key="search_query", placeholder="British Airways, or 006...", label_visibility="collapsed")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        scope_clicked = st.button("Scope this opportunity", type="primary", use_container_width=True, disabled=not query.strip())
    with col_b:
        skip_clicked = st.button("Skip — answer manually", use_container_width=True)

    if skip_clicked:
        goto_next_after_search(None)
        st.rerun()

    if scope_clicked and query.strip():
        if not SNOWFLAKE_AVAILABLE:
            st.error("Snowflake connector not available. Use 'Skip' or fix the install.")
            return
        with st.spinner("Looking up in Salesforce…"):
            try:
                if sf.is_opp_id(query):
                    row = sf.lookup_opp_by_id(query)
                    if not row:
                        st.session_state.search_error = f"No opportunity found for ID `{query}`."
                        st.session_state.search_results = []
                    else:
                        # Already joined to account; build a fake "full" object.
                        account = {k: row[k] for k in ("ACCOUNT_ID", "ACCOUNT_NAME", "INDUSTRY",
                                                       "SALES_SEGMENT", "EMPLOYEE_COUNT",
                                                       "ACCOUNT_FAMILY_MRR", "CUSTOMER_TIER")}
                        opp = {k: row[k] for k in ("OPPORTUNITY_ID", "OPPORTUNITY_NAME", "PRODUCTS_IN_SCOPE",
                                                   "CURRENT_ENVIRONMENT_TOOLS", "PRIMARY_COMPETITOR",
                                                   "PRIMARY_COMPETITOR_INCUMBENT_STATUS", "CHAMPION",
                                                   "ECONOMIC_BUYER", "CLOSE_DATE", "TYPE", "STAGE")}
                        dd_count = sf.fetch_dd_product_count(account["ACCOUNT_ID"])
                        full = {"account": account, "opp": opp, "dd_product_count": dd_count}
                        goto_next_after_search(sf.to_sf_data(full))
                        st.rerun()
                else:
                    rows = sf.search_accounts(query)
                    if not rows:
                        st.session_state.search_error = f"No accounts matched `{query}`."
                        st.session_state.search_results = []
                    elif len(rows) == 1:
                        full = sf.fetch_full(rows[0])
                        goto_next_after_search(sf.to_sf_data(full))
                        st.rerun()
                    else:
                        st.session_state.search_results = rows
                        st.session_state.search_error = None
            except Exception as e:
                st.session_state.search_error = f"Lookup failed: {e}"
                st.session_state.search_results = []

    if st.session_state.search_error:
        st.error(st.session_state.search_error)

    if st.session_state.search_results:
        st.subheader("Multiple matches — pick one")
        labels = []
        for r in st.session_state.search_results:
            mrr = r.get("ACCOUNT_FAMILY_MRR")
            mrr_str = f"${mrr:,.0f} MRR" if mrr else "no MRR data"
            seg = r.get("SALES_SEGMENT") or "?"
            emp = r.get("EMPLOYEE_COUNT") or "?"
            labels.append(f"{r['ACCOUNT_NAME']} — {seg}, {emp} emp, {mrr_str}")

        choice = st.radio("Matching accounts", labels, key="account_choice", label_visibility="collapsed")
        if st.button("Use this account", type="primary"):
            idx = labels.index(choice)
            picked = st.session_state.search_results[idx]
            with st.spinner("Loading opportunity + contracted products…"):
                full = sf.fetch_full(picked)
                goto_next_after_search(sf.to_sf_data(full))
                st.rerun()


# ──────────────────────────────────────────────────────────────────
# Review screen — confirm/edit answers we already have (from SF prefill or
# from a prior pass through the questionnaire)
# ──────────────────────────────────────────────────────────────────

def render_review() -> None:
    sf_data = st.session_state.sf_data
    answers = st.session_state.answers

    st.title("Review what we already know")
    if sf_data:
        sub = f"**{sf_data.get('accountName') or '?'}**"
        if sf_data.get("oppName"):
            sub += f" · {sf_data['oppName']}"
        st.markdown(sub)
    st.caption("These values came from Salesforce. Edit any that look wrong, then continue.")

    # Only show questions whose answer is already set AND are visible per branching.
    # The radio for each lets the AE override before the rest of the questionnaire runs.
    visible_set = {q["id"] for q in visible_questions(answers)}
    answered_visible = [
        q for q in visible_questions(answers)
        if q["id"] in visible_set and answers.get(q["id"])
    ]

    if not answered_visible:
        # Defensive: shouldn't happen because we only land here when prefill is non-empty.
        st.info("Nothing to review yet — straight to the questions.")
        if st.button("Continue", type="primary"):
            advance_from_review()
            st.rerun()
        return

    for q in answered_visible:
        opts = q["opts"]
        option_values = [o["v"] for o in opts]
        option_labels = [o["l"] for o in opts]
        current = answers.get(q["id"])
        default_idx = option_values.index(current) if current in option_values else 0

        prefix = "⚡ " if q["id"] in st.session_state.prefilled_keys else ""
        picked_label = st.radio(
            f"{prefix}{q['q']}",
            option_labels,
            index=default_idx,
            key=f"review_radio_{q['id']}",
        )
        if picked_label is not None:
            picked_v = option_values[option_labels.index(picked_label)]
            if answers.get(q["id"]) != picked_v:
                answers[q["id"]] = picked_v

    st.markdown("---")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("← Search again", use_container_width=True):
            reset_to_search()
            st.rerun()
    with col_b:
        remaining_n = len(remaining_questions(answers))
        cta = f"Answer the remaining {remaining_n} →" if remaining_n else "See recommendation →"
        if st.button(cta, type="primary", use_container_width=True):
            advance_from_review()
            st.rerun()


# ──────────────────────────────────────────────────────────────────
# Questionnaire screen
# ──────────────────────────────────────────────────────────────────

def render_questionnaire() -> None:
    # Only walk through questions that don't already have an answer (prefilled
    # ones live in the review screen). Re-evaluated each rerun so branching
    # changes (e.g. ddStatus=live makes ddQuality visible) are picked up.
    rem = remaining_questions(st.session_state.answers)
    total = len(rem)
    step = st.session_state.step

    # No questions left → result. Happens if every visible question was
    # prefilled, or if the AE just answered the last one.
    if total == 0 or step >= total:
        st.session_state.screen = "result"
        st.rerun()

    sf_data = st.session_state.sf_data
    if sf_data:
        pre_count = len(st.session_state.prefilled_keys)
        st.info(f"⚡ **{sf_data.get('accountName') or '?'}**"
                + (f" — {sf_data.get('oppName')}" if sf_data.get('oppName') else "")
                + f"   ·   {pre_count} fields from Snowflake (review to edit)")
        if st.button("← Edit Salesforce answers", use_container_width=False):
            st.session_state.screen = "review"
            st.rerun()

    st.progress((step) / total, text=f"Question {step + 1} of {total}")

    q = rem[step]
    st.subheader(q["q"])

    if q.get("sfField"):
        is_prefilled = q["id"] in st.session_state.prefilled_keys and st.session_state.answers.get(q["id"])
        badge_label = "Pre-filled" if is_prefilled else "Available in SF"
        st.caption(f"⚡ {badge_label}: {q['sfField']}")

    opts = q["opts"]
    option_values = [o["v"] for o in opts]
    option_labels = [o["l"] for o in opts]

    current = st.session_state.answers.get(q["id"])
    default_idx = option_values.index(current) if current in option_values else None

    picked_label = st.radio(
        q["q"],
        option_labels,
        index=default_idx,
        key=f"radio_{q['id']}_{step}",
        label_visibility="collapsed",
    )
    if picked_label is not None:
        picked_v = option_values[option_labels.index(picked_label)]
        st.session_state.answers[q["id"]] = picked_v

        # Show the sublabel for the chosen option.
        sub = next((o.get("s") for o in opts if o["v"] == picked_v), "")
        is_danger = next((o.get("danger") for o in opts if o["v"] == picked_v), False)
        if sub:
            if is_danger:
                st.warning(sub)
            else:
                st.caption(sub)

    nav_back, nav_spacer, nav_next = st.columns([1, 2, 1])
    with nav_back:
        if st.button("← Back", disabled=(step == 0), use_container_width=True):
            st.session_state.step -= 1
            st.rerun()
    with nav_next:
        # Determine "last question" against the freshly-computed remaining set
        # so branching opening new questions doesn't get misdetected as done.
        is_last = step == len(remaining_questions(st.session_state.answers)) - 1
        next_label = "See recommendation →" if is_last else "Next →"
        if st.button(next_label, type="primary", disabled=(not st.session_state.answers.get(q["id"])), use_container_width=True):
            st.session_state.step += 1
            if st.session_state.step >= len(remaining_questions(st.session_state.answers)):
                st.session_state.screen = "result"
            st.rerun()


# ──────────────────────────────────────────────────────────────────
# Result screen
# ──────────────────────────────────────────────────────────────────

_FLAG_RENDER = {
    "blk": st.error,
    "wrn": st.warning,
    "inf": st.info,
    "ok":  st.success,
}


def render_result() -> None:
    answers = st.session_state.answers
    sf_data = st.session_state.sf_data
    rec = recommend(answers)
    diag = diagnose(answers)
    no_sess = rec["sMin"] is None

    account = (sf_data or {}).get("accountName")
    sub_tail = f" — {account}" if account else ""

    shape = diag["shape"]["value"]
    posture = diag["posture"]["value"]
    constraint = diag["dominant_constraint"]["value"]

    st.markdown(
        f"""
        <div style="background:#1c1c1c;padding:20px 22px;border-radius:8px;color:#fff;">
            <div style="font-size:10px;letter-spacing:.05em;text-transform:uppercase;opacity:.6;">
                Diagnosis{sub_tail}
            </div>
            <div style="display:grid;grid-template-columns:auto 1fr;gap:8px 18px;margin-top:10px;font-size:14px;">
                <div style="opacity:.6;">Shape</div><div style="font-weight:500;">{shape}</div>
                <div style="opacity:.6;">Posture</div><div style="font-weight:500;">{posture}</div>
                <div style="opacity:.6;">Dominant constraint</div><div style="font-weight:500;">{constraint}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if diag["triggers"]:
        with st.expander("Triggers — why this diagnosis fired", expanded=False):
            for t in diag["triggers"]:
                contribs = ", ".join(t["contributed_to"])
                st.markdown(f"- `{t['signal']} = {t['value']}` → {contribs}")

    st.subheader("Customer ownership")
    for bullet in diag["customer_ownership"]:
        st.markdown(f"- {bullet}")

    flags = build_flags(answers, rec["key"], rec.get("sMax"))
    if flags:
        st.subheader("Risk flags")
        for f in flags:
            _FLAG_RENDER.get(f["t"], st.info)(f["m"])

    st.subheader("Before you close the IS deal — confirm these")
    for i, n in enumerate(build_next_steps(answers, rec["key"]), start=1):
        st.markdown(f"**{i}.** {n}")

    st.subheader("Commercial")
    st.caption("Heuristic — calibration data pending. Treat as range, not commitment.")
    if no_sess:
        st.warning("Resolve sponsor blocker before estimating sessions.")
    else:
        c1, c2 = st.columns(2)
        c1.metric("Package", package_label(rec["sMax"]))
        c2.metric("Session estimate", f"{rec['sMin']}–{rec['sMax']}")

    st.subheader("Copy scoping summary")
    st.caption("Click the copy icon (top right of the code block) to paste into Slack, Jira, or email.")
    st.code(build_scoping_doc(sf_data, answers, rec, diag), language=None)

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("← Edit answers"):
            # Send the AE back to the review screen so they can edit anything
            # (prefilled OR previously-manual answers — they're all in `answers`
            # now and the review screen renders any answered+visible question).
            st.session_state.screen = "review"
            st.session_state.step = 0
            st.rerun()
    with col_b:
        if st.button("Start over", type="primary"):
            reset_to_search()
            st.rerun()


# ──────────────────────────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────────────────────────

screen = st.session_state.screen
if screen == "search":
    render_search()
elif screen == "review":
    render_review()
elif screen == "questionnaire":
    render_questionnaire()
elif screen == "result":
    render_result()
else:
    st.error(f"Unknown screen: {screen}")
    if st.button("Reset"):
        reset_to_search()
        st.rerun()
