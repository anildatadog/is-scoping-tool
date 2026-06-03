# Two-Phase Scoping Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Phase 1 fast-pass flow (motion select + 3-5 questions → rough day estimate) alongside the existing Phase 2 full-scope flow.

**Architecture:** Phase 1 is a new entry point — AE picks a service motion from 6 named options then answers 3-5 questions; a `fast_estimate()` function returns a wide day range and PM flag. Phase 2 is the existing flow unchanged, but now also emits a named service motion label derived from `diagnosis.to_service_motion()`. A "Refine this estimate →" CTA on the Phase 1 result screen carries forward Phase 1 answers into Phase 2.

**Tech Stack:** Python 3.11, Streamlit 1.42+, pytest. No new dependencies.

---

## File Map

| File | Change |
|------|--------|
| `phase1.py` | **Create** — Phase 1 question list, `MOTIONS` dict, `fast_estimate()`, `p1_visible_questions()`, `merge_p1_seed()` |
| `diagnosis.py` | **Modify** — add `to_service_motion(shape, motion) -> str` |
| `Scope_an_opportunity.py` | **Modify** — add `render_p1_motion_select()`, `render_p1_questionnaire()`, `render_p1_result()`, update router and session init, update `render_result()` to show service motion label |
| `tests/test_phase1.py` | **Create** — unit tests for `fast_estimate()`, `p1_visible_questions()`, and `merge_p1_seed()` |
| `tests/test_diagnosis.py` | **Modify** — add `to_service_motion()` tests |

---

## Task 1: Add `to_service_motion()` to `diagnosis.py`

**Files:**
- Modify: `diagnosis.py` (append after the `diagnose()` function)
- Modify: `tests/test_diagnosis.py` (append tests at bottom)

- [ ] **Step 1.1: Write failing tests** — add to bottom of `tests/test_diagnosis.py`:

```python
from diagnosis import to_service_motion


def test_foundation_is_delivered_maps_to_hok():
    assert to_service_motion("Foundation", "IS-delivered") == "HOK / Hands-on-Keyboard"


def test_foundation_customer_delivered_maps_to_onboarding():
    assert to_service_motion("Foundation", "Customer-delivered") == "Team Onboarding & Enablement"


def test_accelerator_customer_delivered_maps_to_consultative():
    assert to_service_motion("Accelerator", "Customer-delivered") == "Consultative / Advisory"


def test_accelerator_is_delivered_maps_to_hok():
    assert to_service_motion("Accelerator", "IS-delivered") == "HOK / Hands-on-Keyboard"


def test_gap_filler_is_delivered_maps_to_hok():
    assert to_service_motion("Gap-filler", "IS-delivered") == "HOK / Hands-on-Keyboard"


def test_gap_filler_partner_delivered_maps_to_migration():
    assert to_service_motion("Gap-filler", "Partner-delivered") == "Migration Services"


def test_standards_setter_customer_delivered_maps_to_consultative():
    assert to_service_motion("Standards-setter", "Customer-delivered") == "Consultative / Advisory"


def test_standards_setter_is_delivered_maps_to_resident_architect():
    assert to_service_motion("Standards-setter", "IS-delivered") == "Resident Architect"


def test_defer_maps_to_discovery():
    assert to_service_motion("Defer", "IS-delivered") == "Discovery / Consultative First"
    assert to_service_motion("Defer", "Customer-delivered") == "Discovery / Consultative First"
```

- [ ] **Step 1.2: Run to confirm failure:**
  ```bash
  python -m pytest tests/test_diagnosis.py -k "service_motion" -v
  ```
  Expected: `ImportError: cannot import name 'to_service_motion'`

- [ ] **Step 1.3: Implement** — append to `diagnosis.py` after the `diagnose()` function:

```python
_SERVICE_MOTION: dict[tuple[str, str], str] = {
    ("Foundation",       "IS-delivered"):       "HOK / Hands-on-Keyboard",
    ("Foundation",       "Customer-delivered"): "Team Onboarding & Enablement",
    ("Foundation",       "Partner-delivered"):  "HOK / Hands-on-Keyboard",
    ("Accelerator",      "IS-delivered"):       "HOK / Hands-on-Keyboard",
    ("Accelerator",      "Customer-delivered"): "Consultative / Advisory",
    ("Accelerator",      "Partner-delivered"):  "Consultative / Advisory",
    ("Gap-filler",       "IS-delivered"):       "HOK / Hands-on-Keyboard",
    ("Gap-filler",       "Customer-delivered"): "Consultative / Advisory",
    ("Gap-filler",       "Partner-delivered"):  "Migration Services",
    ("Standards-setter", "IS-delivered"):       "Resident Architect",
    ("Standards-setter", "Customer-delivered"): "Consultative / Advisory",
    ("Standards-setter", "Partner-delivered"):  "Consultative / Advisory",
}


def to_service_motion(shape: str, motion: str) -> str:
    """Map internal shape + motion to the AE-facing service motion label."""
    if shape == "Defer":
        return "Discovery / Consultative First"
    return _SERVICE_MOTION.get((shape, motion), "Consultative / Advisory")
```

- [ ] **Step 1.4: Run tests:**
  ```bash
  python -m pytest tests/test_diagnosis.py -v
  ```
  Expected: all tests pass.

- [ ] **Step 1.5: Commit:**
  ```bash
  git add diagnosis.py tests/test_diagnosis.py
  git commit -m "feat: add to_service_motion() AE-facing label mapping"
  ```

---

## Task 2: Create `phase1.py`

**Files:**
- Create: `phase1.py`
- Create: `tests/test_phase1.py`

- [ ] **Step 2.1: Write failing tests** — create `tests/test_phase1.py`:

```python
"""Tests for Phase 1 fast-estimate logic."""
from phase1 import fast_estimate, p1_visible_questions, MOTIONS


def test_motions_has_six_entries():
    assert len(MOTIONS) == 6


def test_motions_keys():
    assert set(MOTIONS.keys()) == {
        "consultative", "onboarding", "hok",
        "migration", "resident_architect", "discovery",
    }


def test_migration_vol_shown_only_for_migration():
    migration_qs = {q["id"] for q in p1_visible_questions("migration", {})}
    other_qs = {q["id"] for q in p1_visible_questions("hok", {})}
    assert "p1_migVol" in migration_qs
    assert "p1_migVol" not in other_qs


def test_all_motions_get_team_count_question():
    for motion in MOTIONS:
        ids = {q["id"] for q in p1_visible_questions(motion, {})}
        assert "p1_teamCount" in ids, f"{motion} missing p1_teamCount"


def test_discovery_returns_fixed_range():
    est = fast_estimate("discovery", {})
    assert est["days_min"] == 5
    assert est["days_max"] == 10
    assert est["pm_required"] is False


def test_resident_architect_has_no_numeric_range():
    est = fast_estimate("resident_architect", {})
    assert est["days_min"] is None
    assert est["days_max"] is None
    assert est["pm_required"] is True


def test_large_team_produces_higher_estimate_than_single():
    single = fast_estimate("hok", {"p1_teamCount": "single"})
    large = fast_estimate("hok", {"p1_teamCount": "large"})
    assert large["days_max"] > single["days_max"]


def test_missing_readiness_raises_estimate():
    ready = fast_estimate("hok", {"p1_readiness": "ready"})
    missing = fast_estimate("hok", {"p1_readiness": "missing"})
    assert missing["days_max"] > ready["days_max"]


def test_xl_migration_raises_estimate():
    small = fast_estimate("migration", {"p1_migVol": "s"})
    xl = fast_estimate("migration", {"p1_migVol": "xl"})
    assert xl["days_max"] > small["days_max"]


def test_pm_required_when_estimate_exceeds_50():
    est = fast_estimate("hok", {
        "p1_teamCount": "large",
        "p1_products": ["obs", "security", "dx"],
    })
    assert est["pm_required"] is True


def test_pm_required_for_migration_regardless_of_size():
    est = fast_estimate("migration", {"p1_teamCount": "single", "p1_migVol": "s"})
    assert est["pm_required"] is True


def test_estimate_keys_present():
    est = fast_estimate("consultative", {})
    assert {"days_min", "days_max", "pm_required"} <= est.keys()
```

- [ ] **Step 2.2: Run to confirm failure:**
  ```bash
  python -m pytest tests/test_phase1.py -v
  ```
  Expected: `ModuleNotFoundError: No module named 'phase1'`

- [ ] **Step 2.3: Create `phase1.py`:**

```python
"""Phase 1 fast-pass scoping — motion selection and rough-estimate engine.

Phase 1 is a fast entry point: AE picks a service motion, answers 3-5
questions, gets a wide-range day estimate. No diagnostic engine, no SFDC
lookup. The AE's stated motion is taken at face value; Phase 2 validates it.
"""
from __future__ import annotations


MOTIONS: dict[str, dict] = {
    "consultative": {
        "label": "Consultative / Advisory",
        "ask":   '"Help us understand what to do"',
        "desc":  "Customer needs IS guidance, architecture, standards, or recommendations. IS advises; customer executes.",
        "icon":  "💬",
    },
    "onboarding": {
        "label": "Team Onboarding & Enablement",
        "ask":   '"Teach our teams and help them start doing it"',
        "desc":  "Datadog works with customer teams directly to onboard and build starter assets together.",
        "icon":  "👥",
    },
    "hok": {
        "label": "HOK / Hands-on-Keyboard",
        "ask":   '"Build the Datadog assets for us"',
        "desc":  "Customer wants IS to build assets. Asset counts and complexity drive sizing.",
        "icon":  "⌨️",
    },
    "migration": {
        "label": "Migration Services",
        "ask":   '"Move us from another tool into Datadog"',
        "desc":  "Moving from Splunk, Dynatrace, SolarWinds, New Relic, or similar. Source inventory drives scope.",
        "icon":  "🔄",
    },
    "resident_architect": {
        "label": "Resident Architect",
        "ask":   '"Stay with us for multiple months and guide execution"',
        "desc":  "Customer needs embedded IS support across multiple months. Sized by days/week × months.",
        "icon":  "🏗️",
    },
    "discovery": {
        "label": "Discovery / Consultative First",
        "ask":   '"We do not know yet"',
        "desc":  "Requirements, counts, or ownership are unclear. 5-10 days of scoping before a broader proposal.",
        "icon":  "🔍",
    },
}


P1_QUESTIONS: list[dict] = [
    {
        "id": "p1_teamCount",
        "q": "How many teams or workstreams are in scope?",
        "opts": [
            {"v": "single",     "l": "1 team"},
            {"v": "multi",      "l": "2–5 teams"},
            {"v": "enterprise", "l": "6–15 teams"},
            {"v": "large",      "l": "15+ teams or multiple business units"},
        ],
        "show": lambda m, a: True,
    },
    {
        "id": "p1_products",
        "q": "Which product categories are in scope?",
        "hint": "Select all that apply.",
        "kind": "multiselect",
        "opts": [
            {"v": "obs",      "l": "Standard observability (Infra, APM, Logs)"},
            {"v": "dx",       "l": "Digital Experience (RUM, Synthetics)"},
            {"v": "security", "l": "Cloud Security (CSPM, ASM, SIEM)"},
            {"v": "ai",       "l": "AI / LLM Observability"},
            {"v": "finops",   "l": "FinOps / Cloud Cost Management"},
        ],
        "show": lambda m, a: True,
    },
    {
        "id": "p1_readiness",
        "q": "How ready is their environment?",
        "opts": [
            {"v": "ready",   "l": "Ready — telemetry flowing, owners named"},
            {"v": "partial", "l": "Partial — some instrumentation exists"},
            {"v": "missing", "l": "Starting from zero"},
        ],
        "show": lambda m, a: m != "discovery",
    },
    {
        "id": "p1_migVol",
        "q": "Roughly how many dashboards / alert rules exist in the tool being replaced?",
        "opts": [
            {"v": "s",   "l": "Under 50"},
            {"v": "m",   "l": "50–200"},
            {"v": "l",   "l": "200–500"},
            {"v": "xl",  "l": "500+"},
            {"v": "unk", "l": "Unknown yet"},
        ],
        "show": lambda m, a: m == "migration",
    },
    {
        "id": "p1_deadline",
        "q": "Is there a hard external deadline?",
        "opts": [
            {"v": "hard",   "l": "Yes — within 3 months"},
            {"v": "target", "l": "Target date (flexible)"},
            {"v": "flex",   "l": "No hard deadline"},
        ],
        "show": lambda m, a: m != "discovery",
    },
]


def p1_visible_questions(motion: str, answers: dict) -> list[dict]:
    return [q for q in P1_QUESTIONS if q["show"](motion, answers)]


def fast_estimate(motion: str, answers: dict) -> dict:
    """Rough day-range estimate from Phase 1 inputs.

    Returns keys: days_min, days_max (int or None), pm_required (bool).
    Resident Architect also returns a 'label' key in place of numeric range.
    """
    if motion == "discovery":
        return {"days_min": 5, "days_max": 10, "pm_required": False}

    if motion == "resident_architect":
        return {
            "days_min": None,
            "days_max": None,
            "pm_required": True,
            "label": "Sized by days/week × months — needs deeper scoping",
        }

    team = answers.get("p1_teamCount", "multi")
    products = answers.get("p1_products") or []
    readiness = answers.get("p1_readiness", "partial")
    mig_vol = answers.get("p1_migVol", "unk")

    tf = {"single": 1, "multi": 2, "enterprise": 3, "large": 5}.get(team, 2)
    pb = len([p for p in products if p != "obs"]) * 5
    rb = {"ready": 0, "partial": 5, "missing": 12}.get(readiness, 5)
    mv = {"s": 0, "m": 10, "l": 25, "xl": 45, "unk": 15}.get(mig_vol, 0)

    _base: dict[str, tuple[int, int]] = {
        "consultative": (8,  20),
        "onboarding":   (10, 30),
        "hok":          (12, 35),
        "migration":    (20, 55),
    }
    base_min, base_max = _base.get(motion, (10, 30))

    d_min = base_min + (tf - 1) * 5 + pb
    d_max = base_max + (tf - 1) * 12 + pb + rb + mv

    pm_required = d_max > 50 or motion == "migration"

    return {"days_min": d_min, "days_max": d_max, "pm_required": pm_required}


def merge_p1_seed(sf_answers: dict, p1_seed: dict) -> dict:
    """Merge Phase 1 seed answers into SF-prefilled answers.

    SF prefill wins for overlapping factual keys (SF data is authoritative).
    _p1_stated_motion is always kept — it has no SF equivalent.
    """
    merged = dict(p1_seed)
    merged.update(sf_answers)
    if "_p1_stated_motion" in p1_seed:
        merged["_p1_stated_motion"] = p1_seed["_p1_stated_motion"]
    return merged
```

- [ ] **Step 2.4: Run tests:**
  ```bash
  python -m pytest tests/test_phase1.py -v
  ```
  Expected: all 12 phase1/fast_estimate tests pass. merge_p1_seed tests are added in Task 3.

- [ ] **Step 2.5: Run full suite:**
  ```bash
  python -m pytest tests/ -v
  ```
  Expected: all tests pass.

- [ ] **Step 2.6: Commit:**
  ```bash
  git add phase1.py tests/test_phase1.py
  git commit -m "feat: Phase 1 question set and fast_estimate() engine"
  ```

---

## Task 3: Phase 1 UI screens

**Files:**
- Modify: `Scope_an_opportunity.py`

### Step 3.1: Add imports at top of file

After existing imports, add:

```python
from phase1 import MOTIONS, fast_estimate, p1_visible_questions
from diagnosis import to_service_motion
```

Also add this helper near the top (after imports):

```python
_P1_TO_P2_PRODUCTS = {
    "obs":      "infra_apm_logs",
    "dx":       "dx",
    "security": "security",
    "ai":       "ai",
    "finops":   "finops",
}


def _p1_products_to_p2(p1_products: list[str]) -> list[str]:
    return [_P1_TO_P2_PRODUCTS[p] for p in p1_products if p in _P1_TO_P2_PRODUCTS]
```

### Step 3.2: Update session state init

Find the `if "screen" not in st.session_state:` block and replace:

```python
if "screen" not in st.session_state:
    st.session_state.screen = "home"
    st.session_state.sf_data = None
    st.session_state.answers = {}
    st.session_state.step = 0
    st.session_state.search_results = []
    st.session_state.search_error = None
    st.session_state.prefilled_keys = set()
    st.session_state.p1_motion = None
    st.session_state.p1_answers = {}
    st.session_state.p1_seed = {}
```

Replace the body of `reset_to_search()`:

```python
def reset_to_search() -> None:
    st.session_state.screen = "home"
    st.session_state.sf_data = None
    st.session_state.answers = {}
    st.session_state.step = 0
    st.session_state.search_results = []
    st.session_state.search_error = None
    st.session_state.prefilled_keys = set()
    st.session_state.p1_motion = None
    st.session_state.p1_answers = {}
    st.session_state.p1_seed = {}
```

### Step 3.3: Add `render_home()` before `render_search()`

```python
def render_home() -> None:
    st.title("🧭 IS Scoping Tool")
    st.caption(f"Signed in as {st.user.email}")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Quick estimate")
        st.caption("Pick a motion, answer 3-5 questions, get a rough day range in under 2 minutes.")
        if st.button("Start quick estimate →", type="primary", use_container_width=True):
            st.session_state.screen = "p1_motion_select"
            st.rerun()
    with col2:
        st.subheader("Full scope")
        st.caption("Look up an opportunity in Salesforce, answer diagnostic questions, get a full diagnosis and copy-paste proposal.")
        if st.button("Look up opportunity →", use_container_width=True):
            st.session_state.screen = "search"
            st.rerun()
```

### Step 3.4: Add `render_p1_motion_select()`

```python
def render_p1_motion_select() -> None:
    st.title("What does the customer need?")
    st.caption("Pick the motion that best matches the customer's ask. Not sure? Use the full scope flow instead.")

    for key, m in MOTIONS.items():
        with st.container(border=True):
            col_icon, col_text, col_btn = st.columns([1, 8, 2])
            with col_icon:
                st.markdown(f"## {m['icon']}")
            with col_text:
                st.markdown(
                    f"**{m['label']}**  \n{m['ask']}  \n"
                    f"<span style='opacity:.7;font-size:.9em'>{m['desc']}</span>",
                    unsafe_allow_html=True,
                )
            with col_btn:
                if st.button("Select", key=f"p1_sel_{key}", use_container_width=True):
                    st.session_state.p1_motion = key
                    st.session_state.p1_answers = {}
                    st.session_state.screen = "p1_questionnaire"
                    st.rerun()

    st.markdown("---")
    if st.button("← Back"):
        st.session_state.screen = "home"
        st.rerun()
```

### Step 3.5: Add `render_p1_questionnaire()`

```python
def render_p1_questionnaire() -> None:
    motion = st.session_state.p1_motion
    m = MOTIONS[motion]
    st.title(f"Quick estimate: {m['label']}")
    st.caption("Answer these questions to get a rough day range.")

    answers = dict(st.session_state.p1_answers)
    qs = p1_visible_questions(motion, answers)

    with st.form("p1_form"):
        for q in qs:
            opts = q["opts"]
            if q.get("kind") == "multiselect":
                answers[q["id"]] = st.multiselect(
                    q["q"],
                    options=[o["v"] for o in opts],
                    format_func=lambda v, _opts=opts: next(o["l"] for o in _opts if o["v"] == v),
                    default=answers.get(q["id"]) or [],
                    help=q.get("hint"),
                )
            else:
                current = answers.get(q["id"])
                idx = next((i for i, o in enumerate(opts) if o["v"] == current), 0)
                answers[q["id"]] = st.radio(
                    q["q"],
                    options=[o["v"] for o in opts],
                    format_func=lambda v, _opts=opts: next(o["l"] for o in _opts if o["v"] == v),
                    index=idx,
                )
        submitted = st.form_submit_button("Get estimate →", type="primary")

    if submitted:
        st.session_state.p1_answers = answers
        st.session_state.screen = "p1_result"
        st.rerun()

    if st.button("← Change motion"):
        st.session_state.screen = "p1_motion_select"
        st.rerun()
```

### Step 3.6: Add `render_p1_result()`

**Critical design note:** The Refine CTA must NOT write into `st.session_state.answers` directly. `goto_next_after_search()` overwrites `answers` at lines 110 and 114 of `Scope_an_opportunity.py`. Instead, stash Phase 1 data in a separate `p1_seed` key. A `merge_p1_seed()` helper (added in Step 3.7) merges it into `answers` after SF lookup completes. SF prefill wins for overlapping factual keys; `_p1_stated_motion` is always preserved.

```python
def render_p1_result() -> None:
    motion = st.session_state.p1_motion
    answers = st.session_state.p1_answers
    m = MOTIONS[motion]
    est = fast_estimate(motion, answers)

    st.title(f"Phase 1 estimate: {m['label']}")
    st.caption("First-pass estimate only. Use 'Refine this estimate' for a defensible proposal.")

    if est["days_min"] is None:
        st.info(est.get("label", "Requires deeper scoping — use the full scope flow."))
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Recommended motion", m["label"])
        c2.metric("Estimated days", f"{est['days_min']}–{est['days_max']}")
        c3.metric("PM required?", "Yes" if est["pm_required"] else "No")
        if est["pm_required"]:
            st.warning("Engagements of this size typically need a Project Manager.")

    st.markdown("---")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("← Edit answers"):
            st.session_state.screen = "p1_questionnaire"
            st.rerun()
    with col_b:
        if st.button("🔬 Refine this estimate →", type="primary"):
            # Stash Phase 1 data separately — goto_next_after_search() will
            # merge it after SF lookup via merge_p1_seed().
            st.session_state.p1_seed = {k: v for k, v in {
                "teamCount":         answers.get("p1_teamCount"),
                "productScope":      _p1_products_to_p2(answers.get("p1_products") or []) or None,
                "urgency":           answers.get("p1_deadline"),
                "migVol":            answers.get("p1_migVol"),
                "_p1_stated_motion": motion,
            }.items() if v is not None}
            st.session_state.screen = "search"
            st.rerun()
    with col_c:
        if st.button("Start over"):
            reset_to_search()
            st.rerun()
```

### Step 3.7: Import `merge_p1_seed` from `phase1` and update `goto_next_after_search()`

`merge_p1_seed` is defined in `phase1.py`. Add it to the imports at the top of `Scope_an_opportunity.py`:

```python
from phase1 import MOTIONS, fast_estimate, merge_p1_seed, p1_visible_questions
```

Update `goto_next_after_search()`:

```python
def goto_next_after_search(sf_data: dict | None) -> None:
    """After SF lookup (or skip), pick the right next screen."""
    st.session_state.sf_data = sf_data
    p1_seed = st.session_state.get("p1_seed") or {}

    if sf_data and sf_data.get("prefill"):
        base = dict(sf_data["prefill"])
        st.session_state.answers = merge_p1_seed(base, p1_seed) if p1_seed else base
        st.session_state.prefilled_keys = set(sf_data["prefill"].keys())
        st.session_state.screen = "review"
    else:
        st.session_state.answers = dict(p1_seed)
        st.session_state.prefilled_keys = set()
        st.session_state.screen = "questionnaire"
    st.session_state.step = 0
```

### Step 3.7: Update the router at the bottom of the file

Replace the existing router block:

```python
screen = st.session_state.screen
if screen == "home":
    render_home()
elif screen == "p1_motion_select":
    render_p1_motion_select()
elif screen == "p1_questionnaire":
    render_p1_questionnaire()
elif screen == "p1_result":
    render_p1_result()
elif screen == "search":
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
```

### Step 3.8: Add merge_p1_seed tests to test_phase1.py

`merge_p1_seed` is now in `phase1.py` — no Streamlit import needed. Append to `tests/test_phase1.py`:

```python
from phase1 import merge_p1_seed


def test_merge_p1_seed_sf_wins_on_overlap():
    sf = {"teamCount": "enterprise", "compliance": "yes"}
    seed = {"teamCount": "single", "urgency": "hard"}
    result = merge_p1_seed(sf, seed)
    assert result["teamCount"] == "enterprise"
    assert result["urgency"] == "hard"


def test_merge_p1_seed_stated_motion_always_preserved():
    sf = {"teamCount": "enterprise", "_p1_stated_motion": "hok"}
    seed = {"_p1_stated_motion": "consultative"}
    result = merge_p1_seed(sf, seed)
    assert result["_p1_stated_motion"] == "consultative"


def test_merge_p1_seed_empty_seed_returns_sf_unchanged():
    sf = {"teamCount": "multi", "compliance": "no"}
    assert merge_p1_seed(sf, {}) == sf


def test_merge_p1_seed_empty_sf_returns_seed():
    seed = {"teamCount": "single", "_p1_stated_motion": "hok"}
    assert merge_p1_seed({}, seed) == seed
```

- [ ] **Run merge tests:**
  ```bash
  python -m pytest tests/test_phase1.py -k "merge" -v
  ```
  Expected: all 4 merge tests pass.

- [ ] **Manual smoke test:**
  ```bash
  streamlit run Scope_an_opportunity.py
  ```
  Walk through: Home → Quick estimate → pick HOK → answer questions → see estimate → Refine → confirm search screen loads with pre-filled answers.

- [ ] **Commit:**
  ```bash
  git add Scope_an_opportunity.py tests/test_phase1.py
  git commit -m "feat: Phase 1 UI — home, motion select, questionnaire, result screens"
  ```

---

## Task 4: Service motion label on Phase 2 result

**Files:**
- Modify: `Scope_an_opportunity.py` (inside `render_result()`)

### Step 4.1: Add service motion header block

`render_result()` has no single top-level metrics row — Defer and non-Defer each have their own metric structures (line 552 vs line 568 in `Scope_an_opportunity.py`). Add a dedicated service motion block that fires for BOTH branches.

Insert immediately after `is_defer = shape == "Defer"` (line 458) and before the prose/verdict if-else:

```python
# Service motion — shown for all engagement types including Defer
service_motion = to_service_motion(shape, diag["motion"]["value"])
st.caption(f"**Service motion:** {service_motion}")

stated_motion = answers.get("_p1_stated_motion")
if stated_motion and stated_motion != "discovery":
    stated_label = MOTIONS[stated_motion]["label"]
    if stated_label != service_motion:
        st.warning(
            f"Quick estimate used **{stated_label}**, but diagnostic signals "
            f"point to **{service_motion}**. Review before sending a proposal."
        )
```

The `st.caption` keeps it visually light — it is contextual metadata, not a primary output field.

- [ ] **Manual smoke test:** Run Phase 2 via search for both a Defer case (no sponsor) and a normal case. Confirm service motion label appears above the prose/verdict in both.

- [ ] **Run full suite:**
  ```bash
  python -m pytest tests/ -v
  ```
  Expected: all tests pass.

- [ ] **Commit:**
  ```bash
  git add Scope_an_opportunity.py
  git commit -m "feat: service motion label and Phase 1/2 tension warning on Phase 2 result"
  ```

---

## Self-Review Checklist

- [x] Phase 1 motion select (6 options) — Task 3.4
- [x] Phase 1 short question bank (3-5 Qs, migration-conditional) — Task 2
- [x] Phase 1 rough day estimate + PM flag — Task 2, `fast_estimate()`
- [x] Phase 1 result with "Refine →" CTA — Task 3.6
- [x] Phase 1 answers carry forward into Phase 2 — Task 3.6 (session state seeding)
- [x] Phase 2 unchanged except for motion label on result — Tasks 1 + 4
- [x] Phase 2 flags tension if diagnostic disagrees with stated motion — Task 4
- [x] Home screen as new entry point — Task 3.3
- [x] All new logic has unit tests — Tasks 1 + 2
