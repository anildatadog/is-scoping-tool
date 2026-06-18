import pytest
from pipeline import classify_intent, synthesise_pipeline

ROWS = [
    {"customer_name": "Acme Corp", "estimator": "anil.d", "motion": "migration",
     "p1_days_low": "35", "p1_days_high": "99", "p1_days_mid": "67",
     "pm_required": "Yes", "shape": "gap-filler", "motion_p2": "advisory",
     "binding_constraints": "compliance", "quarter": "Q2 2026", "notes": ""},
    {"customer_name": "Beta Inc", "estimator": "jay.b", "motion": "onboarding",
     "p1_days_low": "20", "p1_days_high": "50", "p1_days_mid": "35",
     "pm_required": "", "shape": "team-onboarding", "motion_p2": "",
     "binding_constraints": "", "quarter": "Q2 2026", "notes": ""},
    {"customer_name": "Gamma Ltd", "estimator": "anil.d", "motion": "consultative",
     "p1_days_low": "10", "p1_days_high": "25", "p1_days_mid": "17",
     "pm_required": "", "shape": "advisory", "motion_p2": "",
     "binding_constraints": "", "quarter": "Q1 2026", "notes": ""},
]

def test_classify_drill():
    assert classify_intent("show me the FCA estimate") == "drill"

def test_classify_filter():
    assert classify_intent("which deals are over 50 days") == "filter"

def test_classify_aggregate():
    assert classify_intent("pipeline by motion this quarter") == "aggregate"

def test_classify_capacity():
    assert classify_intent("total IS days committed in Q2") == "capacity"

def test_drill_by_customer():
    result = synthesise_pipeline(ROWS, "drill", customer="Acme Corp",
                                  estimator=None, quarter=None, threshold_days=None)
    assert result["query_type"] == "drill"
    assert len(result["matches"]) == 1
    assert result["matches"][0]["customer_name"] == "Acme Corp"

def test_filter_by_threshold():
    result = synthesise_pipeline(ROWS, "filter", customer=None,
                                  estimator=None, quarter=None, threshold_days=50)
    assert result["query_type"] == "filter"
    # Only Acme Corp (67 days) exceeds 50
    assert len(result["matches"]) == 1
    assert result["matches"][0]["customer_name"] == "Acme Corp"

def test_aggregate_by_motion():
    result = synthesise_pipeline(ROWS, "aggregate", customer=None,
                                  estimator=None, quarter=None, threshold_days=None)
    assert result["query_type"] == "aggregate"
    assert "groups" in result
    motions = {g["key"] for g in result["groups"]}
    assert "migration" in motions

def test_capacity_sum():
    result = synthesise_pipeline(ROWS, "capacity", customer=None,
                                  estimator=None, quarter="Q2 2026", threshold_days=None)
    assert result["query_type"] == "capacity"
    assert result["total_days_mid"] == 102  # 67 + 35

def test_capacity_caveat_present():
    result = synthesise_pipeline(ROWS, "capacity", customer=None,
                                  estimator=None, quarter=None, threshold_days=None)
    assert "midpoint estimates" in result["caveat"]
