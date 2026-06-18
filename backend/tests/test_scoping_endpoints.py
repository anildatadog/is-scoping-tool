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
