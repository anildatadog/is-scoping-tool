"""IS Scoping Tool — Streamlit UI.

Three screens: search, questionnaire, result. State held in st.session_state.
"""
from __future__ import annotations

import streamlit as st

from diagnosis import (
    compute_defer_verdict,
    compute_delivery_phases,
    diagnose,
    package_label,
    phases_total_range,
)
from methodologies import build_flags, build_next_steps, recommend, visible_questions
from prose import generate as generate_prose
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
    """Visible questions (per branching) that the user still needs to answer.

    Used for the review/advance-from-review logic (asking 'is there work left?')
    and for the 'remaining N' counter on the review screen — i.e. anywhere we
    need a count of UNANSWERED questions.
    """
    return [q for q in visible_questions(answers) if not answers.get(q["id"])]


def questionnaire_questions(answers: dict) -> list[dict]:
    """Visible questions that belong on the QUESTIONNAIRE screen — every
    visible question that was NOT prefilled from Salesforce.

    Crucially, this filter does NOT exclude already-answered questions.
    The questionnaire screen needs a stable list so that picking an answer
    doesn't shift the step index under the user (which previously caused
    Back/Next/last-option-pick to all behave wrongly).

    Prefilled questions live in the review screen, not here.
    """
    prefilled = st.session_state.get("prefilled_keys", set())
    return [q for q in visible_questions(answers) if q["id"] not in prefilled]


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
                        dd_products = sf.fetch_dd_products(account["ACCOUNT_ID"])
                        full = {"account": account, "opp": opp, "dd_products": dd_products}
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
        col_mrr, col_prod = st.columns(2)
        mrr = sf_data.get("accountFamilyMRR")
        col_mrr.metric("Account MRR", f"${mrr:,.0f}" if mrr else "—")
        dd_products = sf_data.get("ddProducts") or []
        col_prod.markdown(
            f"**Contracted products**  \n{'  \n'.join(f'- {p}' for p in dd_products) if dd_products else '_None on record_'}"
        )
    st.caption("These values came from Salesforce. Edit any that look wrong, then continue.")

    # Only show questions whose answer is already set AND are visible per branching.
    # Multi-select questions count as "answered" by key-presence even if the
    # value is an empty list (= valid intentional "obs-only" answer).
    def _is_answered(qq: dict) -> bool:
        if qq.get("kind") == "multiselect":
            return qq["id"] in answers
        return bool(answers.get(qq["id"]))

    answered_visible = [q for q in visible_questions(answers) if _is_answered(q)]

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
        prefix = "⚡ " if q["id"] in st.session_state.prefilled_keys else ""

        if q.get("kind") == "multiselect":
            current_list = answers.get(q["id"], [])
            default_labels = [
                opts[option_values.index(v)]["l"]
                for v in current_list if v in option_values
            ]
            picked_labels = st.multiselect(
                f"{prefix}{q['q']}",
                option_labels,
                default=default_labels,
                key=f"review_multi_{q['id']}",
            )
            answers[q["id"]] = [
                option_values[option_labels.index(lbl)] for lbl in picked_labels
            ]
        else:
            current = answers.get(q["id"])
            default_idx = option_values.index(current) if current in option_values else 0
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
    # Use questionnaire_questions (filtered by prefilled_keys), NOT
    # remaining_questions (filtered by is-answered). The latter shifts the
    # indexable list every time the AE picks an answer, which is the cause
    # of the Back/Next/last-option-auto-advance bugs.
    rem = questionnaire_questions(st.session_state.answers)
    total = len(rem)
    step = st.session_state.step

    # No questions left → result. Happens if every visible question was
    # prefilled — branching may have removed all non-prefilled questions.
    if total == 0:
        st.session_state.screen = "result"
        st.rerun()

    # Clamp step into the valid range — branching can shorten `rem` mid-flow.
    if step >= total:
        st.session_state.step = total - 1
        step = total - 1

    sf_data = st.session_state.sf_data
    if sf_data:
        pre_count = len(st.session_state.prefilled_keys)
        mrr = sf_data.get("accountFamilyMRR")
        mrr_str = f" · MRR ${mrr:,.0f}" if mrr else ""
        dd_products = sf_data.get("ddProducts") or []
        prod_str = f" · {', '.join(dd_products)}" if dd_products else ""
        st.info(f"⚡ **{sf_data.get('accountName') or '?'}**"
                + (f" — {sf_data.get('oppName')}" if sf_data.get('oppName') else "")
                + mrr_str + prod_str
                + f"   ·   {pre_count} fields from Snowflake (review to edit)")
        if st.button("← Edit Salesforce answers", use_container_width=False):
            st.session_state.screen = "review"
            st.rerun()

    # Progress = completed questions / total. Hits 100% as soon as the last
    # question is answered, before the AE clicks "See recommendation".
    # Count answered: radio questions land truthy values; multi-select
    # questions can land an empty list (= "no add-ons" which is a valid
    # intentional answer). Treat key-presence as "answered" for those.
    def _answered(qq: dict) -> bool:
        if qq.get("kind") == "multiselect":
            return qq["id"] in st.session_state.answers
        return bool(st.session_state.answers.get(qq["id"]))

    answered_count = sum(1 for qq in rem if _answered(qq))
    st.progress(answered_count / total, text=f"{answered_count} of {total} answered")

    q = rem[step]
    st.subheader(q["q"])

    if q.get("hint"):
        st.caption(q["hint"])
    if q.get("sfField"):
        is_prefilled = q["id"] in st.session_state.prefilled_keys and st.session_state.answers.get(q["id"])
        badge_label = "Pre-filled" if is_prefilled else "Available in SF"
        st.caption(f"⚡ {badge_label}: {q['sfField']}")

    opts = q["opts"]
    option_values = [o["v"] for o in opts]
    option_labels = [o["l"] for o in opts]

    if q.get("kind") == "multiselect":
        current_list = st.session_state.answers.get(q["id"], [])
        default_labels = [opts[option_values.index(v)]["l"]
                          for v in current_list if v in option_values]
        picked_labels = st.multiselect(
            q["q"],
            option_labels,
            default=default_labels,
            key=f"multi_{q['id']}_{step}",
            label_visibility="collapsed",
        )
        picked_v_list = [option_values[option_labels.index(lbl)] for lbl in picked_labels]
        st.session_state.answers[q["id"]] = picked_v_list

        for v in picked_v_list:
            opt = next(o for o in opts if o["v"] == v)
            if opt.get("s"):
                st.caption(f"**{opt['l']}** — {opt['s']}")
    else:
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
        # is_last is true if this step is the last non-prefilled question
        # currently visible. Re-evaluated against the same questionnaire
        # filter so branching openings/closings are picked up.
        is_last = step == len(questionnaire_questions(st.session_state.answers)) - 1
        next_label = "See recommendation →" if is_last else "Next →"
        if st.button(next_label, type="primary", disabled=(not _answered(q)), use_container_width=True):
            st.session_state.step += 1
            if st.session_state.step >= len(questionnaire_questions(st.session_state.answers)):
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

    account = (sf_data or {}).get("accountName")
    sub_tail = f" — {account}" if account else ""

    shape = diag["shape"]["value"]
    is_defer = shape == "Defer"

    # Headline prose: Defer uses a templated verdict; everything else routes
    # through the LLM prose layer.
    if is_defer:
        v = compute_defer_verdict(answers)
        st.markdown(
            f"<div style='font-size:15px;line-height:1.55;'>"
            f"<p><strong>Verdict.</strong> {v['verdict']}</p>"
            f"<p><strong>What changes the picture.</strong> {v['what_changes']}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("")
    else:
        # Prose layer — single Anthropic call, cached per answer set so toggling
        # back to the result screen doesn't burn the API quota.
        prose_cache = st.session_state.setdefault("prose_cache", {})
        answers_key = repr(sorted(answers.items()))
        if answers_key not in prose_cache:
            with st.spinner("Writing diagnosis…"):
                prose_cache[answers_key] = generate_prose(diag, answers)
        prose = prose_cache[answers_key]

        if prose:
            st.markdown(
                f"<div style='font-size:15px;line-height:1.55;'>"
                f"<p><strong>Diagnosis.</strong> {prose['diagnosis_paragraph']}</p>"
                f"<p><strong>Consequence.</strong> {prose['consequence_paragraph']}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("")

    # Structured card. For Defer, show only the verdict label; motion /
    # binding-constraints fields aren't meaningful for a "this isn't IS"
    # output and would just confuse the reader.
    if is_defer:
        card_rows = '<div style="opacity:.6;">Verdict</div><div style="font-weight:500;">Defer — not an IS engagement (yet)</div>'
    else:
        motion = diag["motion"]["value"]
        constraints_str = " · ".join(c["value"] for c in diag["binding_constraints"])
        card_rows = (
            f'<div style="opacity:.6;">Shape</div><div style="font-weight:500;">{shape}</div>'
            f'<div style="opacity:.6;">Motion</div><div style="font-weight:500;">{motion}</div>'
            f'<div style="opacity:.6;">Binding constraints</div><div style="font-weight:500;">{constraints_str}</div>'
        )
    st.markdown(
        f"""
        <div style="background:#1c1c1c;padding:20px 22px;border-radius:8px;color:#fff;">
            <div style="font-size:10px;letter-spacing:.05em;text-transform:uppercase;opacity:.6;">
                Diagnosis{sub_tail}
            </div>
            <div style="display:grid;grid-template-columns:auto 1fr;gap:8px 18px;margin-top:10px;font-size:14px;">
                {card_rows}
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

    st.subheader("Next steps" if is_defer else "Customer ownership")
    for bullet in diag["customer_ownership"]:
        st.markdown(f"- {bullet}")

    if not is_defer:
        flags = build_flags(answers, rec["key"], rec.get("sMax"))
        if flags:
            st.subheader("Risk flags")
            for f in flags:
                _FLAG_RENDER.get(f["t"], st.info)(f["m"])

        st.subheader("Before you close the IS deal — confirm these")
        for i, n in enumerate(build_next_steps(answers, rec["key"]), start=1):
            st.markdown(f"**{i}.** {n}")

        no_sess = rec["sMin"] is None
        st.subheader("Commercial")
        if no_sess:
            st.warning("Resolve sponsor blocker before estimating sessions.")
        elif rec["sMax"] > 120:
            # Above 120 the v1 sizing math compounds into numbers with no
            # calibrated basis. Replace the raw range with a shape-aware
            # delivery plan: per-phase scope + per-phase session range. AE
            # can use the phase total for SOW templating without anchoring
            # on a single inflated number.
            phases = compute_delivery_phases(answers, shape)
            total_min, total_max = phases_total_range(phases)
            st.metric("Package", "Multi-phase")
            st.markdown(f"**High-level delivery plan** — {len(phases)} phases, estimated **{total_min}-{total_max} sessions total** (heuristic)")
            for i, p in enumerate(phases, start=1):
                st.markdown(
                    f"**{i}. {p['name']}** · {p['sessions_min']}–{p['sessions_max']} sessions  \n"
                    f"<span style='opacity:.7;'>{p['brief']}</span>",
                    unsafe_allow_html=True,
                )
            st.caption(
                "Phases and session ranges are heuristic — calibration data pending. "
                "Total is the sum of per-phase ranges; treat as scoping starting point, not commitment."
            )
        else:
            _rate = 1700
            dollar_min = rec["sMin"] * _rate
            dollar_max = rec["sMax"] * _rate
            c1, c2 = st.columns(2)
            c1.metric("Package", package_label(rec["sMax"]))
            c2.metric("Indicative value", f"${dollar_min:,} – ${dollar_max:,}")
            st.caption(f"{rec['sMin']}–{rec['sMax']} sessions at ${_rate:,}/session · heuristic, calibration pending")

    st.subheader("Copy scoping summary")
    st.caption("Click the copy icon (top right of the code block) to paste into Slack, Jira, or email.")
    # Pass prose into the copy-paste builder so the Slack-ready output
    # carries the same consulting-voice paragraphs as the in-browser view.
    prose_for_doc = None if is_defer else (prose if "prose" in locals() else None)
    st.code(build_scoping_doc(sf_data, answers, rec, diag, prose_for_doc), language=None, wrap_lines=True)

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
