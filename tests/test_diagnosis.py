"""Synthesis rules — canonical archetype inputs.

These tests anchor the slice-1 rules against the four shapes / four postures.
If a real engagement diagnoses surprisingly, the answers + expected diagnosis
should be added here as a new case before adjusting the rules.
"""
from __future__ import annotations

from diagnosis import diagnose, package_label


BA_LIKE = {
    "ddStatus": "new",
    "replacingTool": "no",
    "teamCount": "enterprise",
    "productCount": "5-7",
    "sponsor": "exec",
    "authority": "central",
    "capability": "strong",
    "urgency": "flex",
    "compliance": "yes",
    "securityScope": "yes",
}

FCA_LIKE = {
    "ddStatus": "live",
    "ddQuality": "good",
    "teamCount": "large",
    "productCount": "5-7",
    "sponsor": "exec",
    "authority": "central",
    "capability": "strong",
    "urgency": "flex",
    "compliance": "yes",
    "securityScope": "no",
}

MIGRATION_HEAVY = {
    "ddStatus": "new",
    "replacingTool": "yes",
    "migVol": "xl",
    "teamCount": "enterprise",
    "productCount": "3-4",
    "sponsor": "exec",
    "authority": "central",
    "capability": "some",
    "urgency": "hard",
    "compliance": "no",
    "securityScope": "no",
}

SINGLE_TEAM_NEWBIE = {
    "ddStatus": "new",
    "replacingTool": "no",
    "teamCount": "single",
    "productCount": "1-2",
    "sponsor": "manager",
    "capability": "limited",
    "urgency": "flex",
    "compliance": "no",
    "securityScope": "no",
}


def test_ba_like_diagnoses_as_foundation_is_led_or_pattern_source():
    d = diagnose(BA_LIKE)
    assert d["shape"]["value"] == "Foundation"
    # BA had strong customer capability, so posture lands on IS-as-pattern-source
    # in the v2 vocabulary. Allow IS-led too — the ambiguity is documented and
    # the next slice will sharpen this.
    assert d["posture"]["value"] in {"IS-led", "IS-as-pattern-source"}
    assert d["dominant_constraint"]["value"] == "regulation"
    assert any("security" in b.lower() for b in d["customer_ownership"])


def test_fca_like_diagnoses_as_accelerator_advisory_multi_team():
    d = diagnose(FCA_LIKE)
    assert d["shape"]["value"] == "Accelerator"
    assert d["posture"]["value"] == "IS-advisory"
    # teamCount=large fires multi-team before regulation can become dominant.
    assert d["dominant_constraint"]["value"] == "multi-team"
    assert any("workstream" in b.lower() or "execution" in b.lower()
               for b in d["customer_ownership"])


def test_migration_heavy_diagnoses_as_gapfiller_executes_deadline():
    d = diagnose(MIGRATION_HEAVY)
    assert d["shape"]["value"] == "Gap-filler"
    assert d["posture"]["value"] == "IS-executes"
    assert d["dominant_constraint"]["value"] == "deadline"
    assert any("decommission" in b.lower() for b in d["customer_ownership"])


def test_single_team_newbie_diagnoses_as_foundation_led_capability_gap():
    d = diagnose(SINGLE_TEAM_NEWBIE)
    assert d["shape"]["value"] == "Foundation"
    assert d["posture"]["value"] == "IS-led"
    assert d["dominant_constraint"]["value"] == "capability gap"


def test_diagnose_returns_full_dict_shape():
    d = diagnose(FCA_LIKE)
    assert set(d.keys()) == {
        "shape", "posture", "dominant_constraint", "triggers", "customer_ownership",
    }
    assert d["triggers"], "triggers list should never be empty for a valid input"
    for t in d["triggers"]:
        assert set(t.keys()) == {"signal", "value", "contributed_to"}
        assert t["contributed_to"], "every trigger must contribute to at least one field"


def test_package_label_thresholds():
    assert package_label(None) == "Resolve sponsor blocker first"
    assert package_label(20) == "Starter"
    assert package_label(30) == "Starter"
    assert package_label(45) == "Standard"
    assert package_label(60) == "Standard"
    assert package_label(85) == "Enterprise"
    assert package_label(100) == "Enterprise"
    assert package_label(150) == "Multi-phase"
