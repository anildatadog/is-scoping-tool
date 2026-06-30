"""Tests for the /scoping/* HTTP endpoints — Snowflake and GSheet are mocked."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


# --- /scoping/search_account ---

def test_search_account_by_name(client):
    mock_results = [{"ACCOUNT_ID": "001abc", "ACCOUNT_NAME": "Acme Corp"}]
    with patch("snowflake_lookup.search_accounts", return_value=mock_results):
        resp = client.post("/scoping/search_account", json={"q": "Acme"})
    assert resp.status_code == 200
    assert resp.json()[0]["ACCOUNT_NAME"] == "Acme Corp"

def test_search_account_by_opp_id(client):
    mock_opp = {"OPPORTUNITY_ID": "006abc", "ACCOUNT_ID": "001abc"}
    mock_full = {"account": {}, "opportunity": mock_opp}
    mock_sf_data = {"oppId": "006abc", "accountName": "Acme Corp"}
    with (
        patch("snowflake_lookup.is_opp_id", return_value=True),
        patch("snowflake_lookup.lookup_opp_by_id", return_value=mock_opp),
        patch("snowflake_lookup.fetch_full", return_value=mock_full),
        patch("snowflake_lookup.to_sf_data", return_value=mock_sf_data),
    ):
        resp = client.post("/scoping/search_account", json={"q": "006abc"})
    assert resp.status_code == 200
    assert resp.json() == [mock_sf_data]


# --- /scoping/get_account_details ---

def test_get_account_details_found(client):
    mock_opp = {"OPPORTUNITY_ID": "006abc", "ACCOUNT_ID": "001abc"}
    mock_full = {"account": {}, "opportunity": mock_opp}
    mock_sf_data = {"oppId": "006abc", "accountName": "Acme Corp"}
    with (
        patch("snowflake_lookup.lookup_opp_by_id", return_value=mock_opp),
        patch("snowflake_lookup.fetch_full", return_value=mock_full),
        patch("snowflake_lookup.to_sf_data", return_value=mock_sf_data),
    ):
        resp = client.post("/scoping/get_account_details", json={"opp_id": "006abc"})
    assert resp.status_code == 200
    assert resp.json()["accountName"] == "Acme Corp"

def test_get_account_details_not_found(client):
    with patch("snowflake_lookup.lookup_opp_by_id", return_value=None):
        resp = client.post("/scoping/get_account_details", json={"opp_id": "006xyz"})
    assert resp.status_code == 200
    assert "error" in resp.json()


# --- /scoping/run_estimate ---

def test_run_estimate_returns_structured_result(client):
    answers = {"ddStatus": "new", "teamCount": "single", "sponsor": "exec"}
    mock_diag = {"shape": {"value": "team-onboarding"}, "motion": {"value": "onboarding"}, "binding_constraints": []}
    mock_rec = {"key": "onboarding", "sMin": 20, "sMax": 50}
    with (
        patch("diagnosis.diagnose", return_value=mock_diag),
        patch("methodologies.recommend", return_value=mock_rec),
        patch("methodologies.build_flags", return_value=[]),
        patch("methodologies.build_next_steps", return_value=["step 1"]),
        patch("diagnosis.to_service_motion", return_value="Guided Delivery"),
    ):
        resp = client.post("/scoping/run_estimate", json={"answers": answers})
    assert resp.status_code == 200
    body = resp.json()
    assert body["methodology"] == "onboarding"
    assert body["p1_days_low"] == 20
    assert body["p1_days_high"] == 50
    assert body["service_motion"] == "Guided Delivery"
    assert body["pm_required"] is False  # sMax=50 is NOT > 50, motion != migration

def test_run_estimate_pm_required_true(client):
    answers = {"ddStatus": "new", "motion": "migration"}
    mock_diag = {"shape": {"value": "gap-filler"}, "motion": {"value": "migration"}, "binding_constraints": []}
    mock_rec = {"key": "migration", "sMin": 35, "sMax": 99}
    with (
        patch("diagnosis.diagnose", return_value=mock_diag),
        patch("methodologies.recommend", return_value=mock_rec),
        patch("methodologies.build_flags", return_value=[]),
        patch("methodologies.build_next_steps", return_value=[]),
        patch("diagnosis.to_service_motion", return_value="Advisory"),
    ):
        resp = client.post("/scoping/run_estimate", json={"answers": answers})
    assert resp.status_code == 200
    body = resp.json()
    assert body["pm_required"] is True  # key == "migration"


# --- /scoping/governed_handoff ---

def test_governed_handoff_returns_initialize_engagement_payload(client):
    answers = {"productScope": ["infra_apm_logs", "dx"]}
    estimate = {
        "methodology": "onboarding",
        "p1_days_low": 20,
        "p1_days_high": 50,
        "p1_days_mid": 35,
        "pm_required": False,
        "shape": "team-onboarding",
        "motion": "onboarding",
        "service_motion": "Guided Delivery",
        "binding_constraints": [],
        "flags": [],
        "next_steps": ["step 1"],
    }
    with patch("scoping_handlers.run_estimate", return_value=estimate):
        resp = client.post("/scoping/governed_handoff", json={
            "org_id": "acme",
            "engagement_id": "006abc",
            "answers": answers,
            "sf_data": {"opportunityId": "006abc", "accountName": "Acme Corp"},
            "scoping_summary": "Scoped in Salesforce.",
        })

    assert resp.status_code == 200
    body = resp.json()
    assert body["target_mcp"] == "dd-governed-onboarding-mcp"
    assert body["tool"] == "initialize_engagement"
    args = body["arguments"]
    assert args["org_id"] == "acme"
    assert args["engagement_id"] == "006abc"
    assert args["engagement_type"] == "pair_programming"
    assert args["session_count"] == 35
    assert args["source_opportunity_id"] == "006abc"
    assert args["products_in_scope"] == ["infra", "apm", "logs", "rum", "synthetics_api"]
    assert args["scoping_payload"]["estimate"] == estimate
    assert body["next_tool"] == "batch_submit_intake"


def test_governed_handoff_defaults_to_standard_observability_when_scope_empty(client):
    estimate = {
        "methodology": "governedPlatform",
        "p1_days_low": 40,
        "p1_days_high": 80,
        "p1_days_mid": 60,
        "pm_required": True,
        "shape": "foundation",
        "motion": "platform",
        "service_motion": "Governed Platform",
        "binding_constraints": [],
        "flags": [],
        "next_steps": [],
    }
    with patch("scoping_handlers.run_estimate", return_value=estimate):
        resp = client.post("/scoping/governed_handoff", json={
            "org_id": "acme",
            "answers": {},
        })

    assert resp.status_code == 200
    args = resp.json()["arguments"]
    assert args["products_in_scope"] == ["infra", "apm", "logs"]
    assert args["engagement_type"] == "governed_platform"
    assert args["engagement_id"] == "acme-engagement"


def test_governed_handoff_uses_opportunity_id_as_fallback_engagement_id(client):
    estimate = {
        "methodology": "onboarding",
        "p1_days_low": 20,
        "p1_days_high": 50,
        "p1_days_mid": 35,
        "pm_required": False,
        "shape": "team-onboarding",
        "motion": "onboarding",
        "service_motion": "Guided Delivery",
        "binding_constraints": [],
        "flags": [],
        "next_steps": [],
    }
    with patch("scoping_handlers.run_estimate", return_value=estimate):
        resp = client.post("/scoping/governed_handoff", json={
            "org_id": "acme",
            "answers": {},
            "sf_data": {"opportunityId": "006abc"},
        })

    assert resp.status_code == 200
    assert resp.json()["arguments"]["engagement_id"] == "006abc"


def test_governed_handoff_rejects_parallel_id_for_salesforce_opportunity(client):
    estimate = {
        "methodology": "onboarding",
        "p1_days_low": 20,
        "p1_days_high": 50,
        "p1_days_mid": 35,
        "pm_required": False,
        "shape": "team-onboarding",
        "motion": "onboarding",
        "service_motion": "Guided Delivery",
        "binding_constraints": [],
        "flags": [],
        "next_steps": [],
    }
    with patch("scoping_handlers.run_estimate", return_value=estimate):
        resp = client.post("/scoping/governed_handoff", json={
            "org_id": "acme",
            "engagement_id": "eng-acme-rollout",
            "answers": {},
            "sf_data": {"opportunityId": "006abc"},
        })

    assert resp.status_code == 200
    body = resp.json()
    assert body["error"].startswith("engagement_id must match")
    assert body["expected_engagement_id"] == "006abc"


# --- /scoping/log_estimate ---

def test_log_estimate_calls_append(client):
    row = {
        "timestamp": "2026-06-18T12:00:00", "estimator": "anil.d",
        "customer_name": "Acme Corp", "sf_account_id": "001abc",
        "sf_opp_id": "006abc", "motion": "migration",
        "p1_days_low": "35", "p1_days_high": "99", "p1_days_mid": "67",
        "pm_required": "Yes", "shape": "gap-filler", "motion_p2": "advisory",
        "binding_constraints": "", "prose_diagnosis": "", "prose_consequence": "",
        "quarter": "Q2 2026", "notes": "",
    }
    with patch("sheets.append_estimate_row") as mock_append:
        resp = client.post("/scoping/log_estimate", json={"row": row})
    assert resp.status_code == 200
    assert resp.json() == {"status": "logged"}
    mock_append.assert_called_once_with(row)


# --- /scoping/get_pipeline ---

def test_get_pipeline_capacity(client):
    mock_rows = [
        {"customer_name": "A", "p1_days_mid": "67", "motion": "migration",
         "pm_required": "Yes", "shape": "gap-filler", "quarter": "Q2 2026",
         "estimator": "anil.d", "motion_p2": "", "binding_constraints": "",
         "p1_days_low": "35", "p1_days_high": "99", "notes": ""},
    ]
    with patch("sheets.read_scoping_log", return_value=mock_rows):
        resp = client.post("/scoping/get_pipeline", json={
            "question": "total IS days in Q2", "quarter": "Q2 2026"
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["query_type"] == "capacity"
    assert body["total_days_mid"] == 67
