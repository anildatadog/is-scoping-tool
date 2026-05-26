"""IS Scoping Tool — Streamlit UI.

Three screens: search, questionnaire, result. State held in st.session_state.
"""
from __future__ import annotations

import streamlit as st

from methodologies import METHODS, build_flags, build_next_steps, recommend, visible_questions
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


def goto_questionnaire(sf_data: dict | None) -> None:
    st.session_state.sf_data = sf_data
    if sf_data and sf_data.get("prefill"):
        st.session_state.answers = dict(sf_data["prefill"])
        st.session_state.prefilled_keys = set(sf_data["prefill"].keys())
    else:
        st.session_state.answers = {}
        st.session_state.prefilled_keys = set()
    st.session_state.step = 0
    st.session_state.screen = "questionnaire"


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
        goto_questionnaire(None)
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
                        goto_questionnaire(sf.to_sf_data(full))
                        st.rerun()
                else:
                    rows = sf.search_accounts(query)
                    if not rows:
                        st.session_state.search_error = f"No accounts matched `{query}`."
                        st.session_state.search_results = []
                    elif len(rows) == 1:
                        full = sf.fetch_full(rows[0])
                        goto_questionnaire(sf.to_sf_data(full))
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
                goto_questionnaire(sf.to_sf_data(full))
                st.rerun()


# ──────────────────────────────────────────────────────────────────
# Questionnaire screen
# ──────────────────────────────────────────────────────────────────

def render_questionnaire() -> None:
    vis = visible_questions(st.session_state.answers)
    total = len(vis)
    step = st.session_state.step

    # If branching reduced the list and we're past the end, jump to result.
    if step >= total:
        st.session_state.screen = "result"
        st.rerun()

    sf_data = st.session_state.sf_data
    if sf_data:
        pre_count = len(st.session_state.prefilled_keys)
        st.info(f"⚡ **{sf_data.get('accountName') or '?'}**"
                + (f" — {sf_data.get('oppName')}" if sf_data.get('oppName') else "")
                + f"   ·   {pre_count} fields pre-filled from Snowflake")

    st.progress((step) / total, text=f"Question {step + 1} of {total}")

    q = vis[step]
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
        next_label = "See recommendation →" if step == total - 1 else "Next →"
        if st.button(next_label, type="primary", disabled=(not st.session_state.answers.get(q["id"])), use_container_width=True):
            st.session_state.step += 1
            if st.session_state.step >= len(visible_questions(st.session_state.answers)):
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
    meth = METHODS[rec["key"]]
    no_sess = rec["sMin"] is None

    sub = "Resolve sponsor blocker before estimating sessions" if no_sess \
        else f"Estimated sessions: {rec['sMin']}–{rec['sMax']}"
    account = (sf_data or {}).get("accountName")
    sub_tail = f" — {account}" if account else ""

    st.markdown(
        f"""
        <div style="background:{meth['color']};padding:18px 20px;border-radius:8px;color:#fff;">
            <div style="font-size:10px;letter-spacing:.05em;text-transform:uppercase;opacity:.75;">
                Recommended IS methodology
            </div>
            <div style="font-size:22px;font-weight:500;margin-top:4px;">{meth['name']}</div>
            <div style="font-size:13px;opacity:.85;margin-top:4px;">{sub}{sub_tail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("")
    st.write(meth["desc"])

    if not no_sess:
        st.subheader("Phase breakdown")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Discover", meth["phases"]["discover"])
        c2.metric("Design",   meth["phases"]["design"])
        c3.metric("Build",    meth["phases"]["build"])
        c4.metric("Launch",   meth["phases"]["launch"])

    flags = build_flags(answers, rec["key"])
    if flags:
        st.subheader("Risk flags")
        for f in flags:
            _FLAG_RENDER.get(f["t"], st.info)(f["m"])

    st.subheader("Before you close the IS deal — confirm these")
    for i, n in enumerate(build_next_steps(answers, rec["key"]), start=1):
        st.markdown(f"**{i}.** {n}")

    st.subheader("Copy scoping summary")
    st.caption("Click the copy icon (top right of the code block) to paste into Slack, Jira, or email.")
    st.code(build_scoping_doc(sf_data, answers, rec), language=None)

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("← Edit answers"):
            st.session_state.screen = "questionnaire"
            st.session_state.step = max(0, len(visible_questions(answers)) - 1)
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
elif screen == "questionnaire":
    render_questionnaire()
elif screen == "result":
    render_result()
else:
    st.error(f"Unknown screen: {screen}")
    if st.button("Reset"):
        reset_to_search()
        st.rerun()
