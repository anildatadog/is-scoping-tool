"""Synthesis rules — canonical archetype inputs.

These tests anchor the diagnosis rules against real customer profiles. If a
real engagement diagnoses surprisingly, add the answers + expected diagnosis
here as a new case before adjusting the rules.

Schema updates:
  Slice 3.7 : posture→motion (3 values); dominant_constraint→binding_constraints (list);
              Standards-setter precedence over Accelerator for broad-scope mature customers.
"""
from __future__ import annotations

from diagnosis import diagnose, package_label


BA_LIKE = {
    "ddStatus": "new",
    "replacingTool": "no",
    "teamCount": "enterprise",
    "productScope": ["security"],  # BA: governed self-service incl. CSPM/SDS
    "sponsor": "exec",
    "authority": "central",
    "capability": "strong",
    "urgency": "flex",
    "compliance": "yes",
    "infraTopology": "single-cloud",
}

FCA_LIKE = {
    "ddStatus": "live",
    "ddQuality": "good",
    "teamCount": "large",
    "productScope": ["security"],  # FCA: obs + cloud security stakeholders
    "sponsor": "exec",
    "authority": "central",
    "capability": "strong",
    "urgency": "flex",
    "compliance": "yes",
    "infraTopology": "single-cloud",
}

MIGRATION_HEAVY = {
    "ddStatus": "new",
    "replacingTool": "yes",
    "migVol": "xl",
    "teamCount": "enterprise",
    "productScope": [],  # obs-only
    "sponsor": "exec",
    "authority": "central",
    "capability": "some",
    "urgency": "hard",
    "compliance": "no",
    "infraTopology": "single-cloud",
}

SINGLE_TEAM_NEWBIE = {
    "ddStatus": "new",
    "replacingTool": "no",
    "teamCount": "multi",  # avoid the manager-sponsor + single-team Defer trigger
    "productScope": [],
    "sponsor": "manager",
    "capability": "limited",
    "urgency": "flex",
    "compliance": "no",
    "infraTopology": "single-cloud",
}

# Standards-setter precedence case (slice 3.7 fix): centrally-governed broad-scope
# strong-capability mature customer should now fire Standards-setter, NOT Accelerator.
STANDARDS_SETTER_LIKE = {
    "ddStatus": "live",
    "ddQuality": "good",
    "teamCount": "enterprise",
    "productScope": ["security", "dx"],  # broad scope = 2+ add-ons
    "sponsor": "exec",
    "authority": "central",
    "capability": "strong",
    "urgency": "flex",
    "compliance": "no",
    "infraTopology": "single-cloud",
}

# Defer cases — verdict, not engagement.

NO_SPONSOR = {
    "ddStatus": "new", "replacingTool": "no",
    "teamCount": "multi", "productScope": [],
    "sponsor": "none", "authority": "central",
    "capability": "some", "urgency": "flex",
    "compliance": "no",
}

ENGINEER_NO_FORCING = {
    "ddStatus": "live", "ddQuality": "good",
    "teamCount": "enterprise", "productScope": [],
    "sponsor": "engineer", "authority": "central",
    "capability": "some", "urgency": "flex",
    "compliance": "no",
}

ENGINEER_WITH_COMPLIANCE_OVERRIDE = {
    "ddStatus": "live", "ddQuality": "good",
    "teamCount": "enterprise", "productScope": [],
    "sponsor": "engineer", "authority": "central",
    "capability": "some", "urgency": "flex",
    "compliance": "yes",  # forcing function — overrides engineer-sponsor Defer
}

VANITY_TOOLING = {
    "ddStatus": "new", "replacingTool": "no",
    "teamCount": "single", "productScope": [],  # narrow: no add-ons
    "sponsor": "manager",
    "capability": "some", "urgency": "flex",
    "compliance": "no",
}


# ──────────────────────────────────────────────────────────────────
# Engagement-shape archetypes
# ──────────────────────────────────────────────────────────────────

def test_ba_like_diagnoses_as_foundation_customer_delivered():
    d = diagnose(BA_LIKE)
    assert d["shape"]["value"] == "Foundation"
    # BA: enterprise scale + central authority + strong capability → Customer-delivered.
    assert d["motion"]["value"] == "Customer-delivered"
    constraint_values = [c["value"] for c in d["binding_constraints"]]
    assert "regulation" in constraint_values
    assert any("security" in b.lower() for b in d["customer_ownership"])


def test_fca_like_diagnoses_as_accelerator_customer_delivered():
    d = diagnose(FCA_LIKE)
    assert d["shape"]["value"] == "Accelerator"
    # FCA has only 1 add-on (security) so doesn't trip the 2+ add-on Standards-setter
    # rule, even with central authority + large team. Falls through to Accelerator.
    assert d["motion"]["value"] == "Customer-delivered"
    constraint_values = [c["value"] for c in d["binding_constraints"]]
    # teamCount=large fires multi-team; compliance=yes ALSO fires regulation. Both bind.
    assert "multi-team" in constraint_values
    assert "regulation" in constraint_values
    assert any("workstream" in b.lower() or "execution" in b.lower()
               for b in d["customer_ownership"])


def test_migration_heavy_diagnoses_as_gapfiller_partner_delivered():
    # Policy 2026-05-27: high-volume migration (xl) goes to Partner-delivered.
    # IS architects the target state; partner or customer team does the cutover.
    d = diagnose(MIGRATION_HEAVY)
    assert d["shape"]["value"] == "Gap-filler"
    assert d["motion"]["value"] == "Partner-delivered"
    constraint_values = [c["value"] for c in d["binding_constraints"]]
    assert "deadline" in constraint_values
    assert any("partner" in b.lower() for b in d["customer_ownership"])
    assert any("decommission" in b.lower() for b in d["customer_ownership"])


def test_moderate_migration_with_weak_capability_is_is_delivered():
    answers = dict(MIGRATION_HEAVY)
    answers["migVol"] = "l"  # not xl
    answers["urgency"] = "flex"  # remove hard-deadline forcing
    d = diagnose(answers)
    assert d["motion"]["value"] == "IS-delivered", (
        "moderate migration with weak capability is the IS-pairs-hands-on case"
    )


def test_single_team_newbie_diagnoses_as_foundation_is_delivered():
    d = diagnose(SINGLE_TEAM_NEWBIE)
    assert d["shape"]["value"] == "Foundation"
    # limited capability dominates: IS-delivered.
    assert d["motion"]["value"] == "IS-delivered"
    constraint_values = [c["value"] for c in d["binding_constraints"]]
    assert "capability gap" in constraint_values


def test_standards_setter_precedence_over_accelerator():
    """Slice 3.7 fix: centrally-governed broad-scope mature strong-cap customer
    should fire Standards-setter, NOT Accelerator. Codex Finding 1."""
    d = diagnose(STANDARDS_SETTER_LIKE)
    assert d["shape"]["value"] == "Standards-setter", (
        "Standards-setter signals (live+good+central+enterprise/large+2+addons) "
        "should win over Accelerator's (live+good+strong) when both could fire"
    )
    # Mature strong customer → Customer-delivered motion.
    assert d["motion"]["value"] == "Customer-delivered"


# ──────────────────────────────────────────────────────────────────
# Defer cases
# ──────────────────────────────────────────────────────────────────

def test_no_sponsor_diagnoses_as_defer():
    d = diagnose(NO_SPONSOR)
    assert d["shape"]["value"] == "Defer"
    assert any("frederique" in b.lower() for b in d["customer_ownership"])


def test_engineer_sponsor_without_forcing_function_diagnoses_as_defer():
    d = diagnose(ENGINEER_NO_FORCING)
    assert d["shape"]["value"] == "Defer"


def test_engineer_sponsor_with_compliance_does_not_defer():
    d = diagnose(ENGINEER_WITH_COMPLIANCE_OVERRIDE)
    assert d["shape"]["value"] != "Defer", (
        "compliance=yes is a forcing function that should override the "
        "engineer-sponsor Defer rule"
    )


def test_manager_sponsor_small_scope_diagnoses_as_defer():
    d = diagnose(VANITY_TOOLING)
    assert d["shape"]["value"] == "Defer"


# ──────────────────────────────────────────────────────────────────
# Multi-select productScope add-ons
# ──────────────────────────────────────────────────────────────────

def test_dx_addon_adds_frontend_ownership_bullet():
    answers = dict(FCA_LIKE)
    answers["productScope"] = ["dx"]
    d = diagnose(answers)
    assert any("frontend" in b.lower() or "rum" in b.lower()
               for b in d["customer_ownership"])
    assert not any("security ops and identity" in b.lower()
                   for b in d["customer_ownership"])


def test_ai_addon_adds_ml_ownership_bullet():
    answers = dict(FCA_LIKE)
    answers["productScope"] = ["ai"]
    d = diagnose(answers)
    assert any("data science" in b.lower() or "ml platform" in b.lower() or "llm" in b.lower()
               for b in d["customer_ownership"])


def test_dx_and_ai_combo_fires_both_bullets():
    # User raised this combo explicitly: obs + DX + AI without security.
    answers = dict(FCA_LIKE)
    answers["productScope"] = ["dx", "ai"]
    d = diagnose(answers)
    assert any("frontend" in b.lower() or "rum" in b.lower() for b in d["customer_ownership"])
    assert any("data science" in b.lower() or "ml platform" in b.lower() for b in d["customer_ownership"])
    assert not any("security ops and identity" in b.lower() for b in d["customer_ownership"])


def test_three_addons_fires_platform_lead_bullet():
    answers = dict(FCA_LIKE)
    answers["productScope"] = ["dx", "security", "ai"]
    d = diagnose(answers)
    assert any("frontend" in b.lower() or "rum" in b.lower() for b in d["customer_ownership"])
    assert any("security ops and identity" in b.lower() for b in d["customer_ownership"])
    assert any("data science" in b.lower() or "ml platform" in b.lower() for b in d["customer_ownership"])
    assert any("category lead" in b.lower() for b in d["customer_ownership"])


def test_obs_only_no_addons_fires_no_extra_category_bullets():
    answers = dict(FCA_LIKE)
    answers["productScope"] = []
    d = diagnose(answers)
    assert not any("frontend" in b.lower() or "rum" in b.lower()
                   for b in d["customer_ownership"])
    assert not any("data science" in b.lower() or "ml platform" in b.lower()
                   for b in d["customer_ownership"])


# ──────────────────────────────────────────────────────────────────
# Infra topology add-ons (slice 3.1)
# ──────────────────────────────────────────────────────────────────

def test_multi_cloud_topology_adds_ownership_bullet():
    answers = dict(FCA_LIKE)
    answers["infraTopology"] = "multi-cloud"
    d = diagnose(answers)
    assert any("cloud-platform lead per cloud" in b.lower() or "cloud-platform" in b.lower()
               for b in d["customer_ownership"])


def test_byoc_topology_adds_ownership_bullet():
    answers = dict(FCA_LIKE)
    answers["infraTopology"] = "byoc"
    d = diagnose(answers)
    assert any("install" in b.lower() and "upgrade" in b.lower()
               for b in d["customer_ownership"])


# ──────────────────────────────────────────────────────────────────
# binding_constraints — list, multiple can fire (slice 3.7)
# ──────────────────────────────────────────────────────────────────

def test_multiple_binding_constraints_for_regulated_multi_team():
    """Codex/user Q3 fix: a regulated multi-team customer surfaces BOTH
    constraints, ordered by priority."""
    d = diagnose(FCA_LIKE)
    values = [c["value"] for c in d["binding_constraints"]]
    assert "multi-team" in values
    assert "regulation" in values
    # multi-team is priority 4, regulation is priority 5 → multi-team first
    assert values.index("multi-team") < values.index("regulation")


def test_single_binding_constraint_when_only_one_fires():
    answers = {
        "ddStatus": "new", "replacingTool": "no",
        "teamCount": "multi", "productScope": [],
        "sponsor": "exec", "authority": "central",
        "capability": "some", "urgency": "hard",  # deadline fires
        "compliance": "no", "infraTopology": "single-cloud",
    }
    d = diagnose(answers)
    values = [c["value"] for c in d["binding_constraints"]]
    assert "deadline" in values
    assert len(values) == 1


# ──────────────────────────────────────────────────────────────────
# Output shape + package label
# ──────────────────────────────────────────────────────────────────

def test_diagnose_returns_full_dict_shape():
    d = diagnose(FCA_LIKE)
    assert set(d.keys()) == {
        "shape", "motion", "binding_constraints", "triggers", "customer_ownership",
    }
    assert d["triggers"], "triggers list should never be empty for a valid input"
    for t in d["triggers"]:
        assert set(t.keys()) == {"signal", "value", "contributed_to"}
        assert t["contributed_to"], "every trigger must contribute to at least one field"
    assert isinstance(d["binding_constraints"], list)
    assert d["binding_constraints"], "binding_constraints should never be empty"


def test_package_label_thresholds():
    assert package_label(None) == "Resolve sponsor blocker first"
    assert package_label(20) == "Starter"
    assert package_label(30) == "Starter"
    assert package_label(45) == "Standard"
    assert package_label(60) == "Standard"
    assert package_label(85) == "Enterprise"
    assert package_label(100) == "Enterprise"
    assert package_label(150) == "Multi-phase"
