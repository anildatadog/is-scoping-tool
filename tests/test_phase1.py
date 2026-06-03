"""Tests for Phase 1 fast-estimate logic."""
from phase1 import fast_estimate, merge_p1_seed, p1_visible_questions, MOTIONS


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


# ── merge_p1_seed ─────────────────────────────────────────────────

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
