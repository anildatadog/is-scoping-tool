import pytest
from unittest.mock import MagicMock, patch

SAMPLE_ROWS = [
    ["Timestamp", "Estimator", "Customer Name", "SF Account ID", "SF Opp ID",
     "Motion", "P1 Days Low", "P1 Days High", "P1 Days Mid", "PM Required",
     "Shape", "Motion P2", "Binding Constraints", "Prose Diagnosis",
     "Prose Consequence", "Quarter", "Notes"],
    ["2026-01-01T10:00:00", "anil.d", "Acme Corp", "001abc", "006abc",
     "migration", "35", "99", "67", "Yes", "gap-filler", "advisory", "",
     "diag text", "cons text", "Q1 2026", ""],
    ["2026-01-02T10:00:00", "anil.d", "Beta Inc", "001def", "006def",
     "onboarding", "20", "50", "35", "", "team-onboarding", "", "",
     "", "", "Q1 2026", ""],
    # row with blank p1_days_mid — should be excluded
    ["2026-01-03T10:00:00", "anil.d", "Gamma Ltd", "001ghi", "006ghi",
     "resident_architect", "", "", "", "", "", "", "", "", "", "Q1 2026", ""],
]

def _mock_sheet(rows):
    sheet = MagicMock()
    sheet.get_all_values.return_value = rows
    return sheet

def _mock_client(sheet):
    client = MagicMock()
    client.open_by_key.return_value.sheet1 = sheet
    return client

def test_read_scoping_log_parses_rows():
    from sheets import read_scoping_log
    sheet = _mock_sheet(SAMPLE_ROWS)
    with patch("sheets._get_sheet", return_value=sheet):
        rows = read_scoping_log()
    assert len(rows) == 2  # 3 data rows minus 1 blank-mid row
    assert rows[0]["customer_name"] == "Acme Corp"
    assert rows[0]["p1_days_mid"] == "67"

def test_read_scoping_log_skips_blank_mid():
    from sheets import read_scoping_log
    sheet = _mock_sheet(SAMPLE_ROWS)
    with patch("sheets._get_sheet", return_value=sheet):
        rows = read_scoping_log()
    names = [r["customer_name"] for r in rows]
    assert "Gamma Ltd" not in names

def test_append_estimate_row_calls_append():
    from sheets import append_estimate_row
    sheet = _mock_sheet([])
    with patch("sheets._get_sheet", return_value=sheet):
        append_estimate_row({
            "timestamp": "2026-06-18T12:00:00",
            "estimator": "anil.d",
            "customer_name": "Test Corp",
            "sf_account_id": "001xxx",
            "sf_opp_id": "006xxx",
            "motion": "migration",
            "p1_days_low": "35",
            "p1_days_high": "99",
            "p1_days_mid": "67",
            "pm_required": "Yes",
            "shape": "gap-filler",
            "motion_p2": "advisory",
            "binding_constraints": "",
            "prose_diagnosis": "",
            "prose_consequence": "",
            "quarter": "Q2 2026",
            "notes": "",
        })
    sheet.append_row.assert_called_once()
    call_args = sheet.append_row.call_args[0][0]
    assert len(call_args) == 17
    assert call_args[2] == "Test Corp"  # column C = index 2
