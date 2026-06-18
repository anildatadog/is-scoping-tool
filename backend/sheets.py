"""Google Sheets client for the IS Scoping Log.

Auth: Application Default Credentials (ADC).
Run `gcloud auth application-default login --scopes=https://www.googleapis.com/auth/spreadsheets`
once locally. In a hosted environment, the service account must have Sheets editor access.
"""
from __future__ import annotations

import gspread
from google.auth import default as _google_default
from google.auth.transport.requests import AuthorizedSession

SHEET_ID = "1StSXWGua4OwdlhQcMfDREhOdqr2UVaSusX30jyb1-74"

COLUMNS = [
    "timestamp", "estimator", "customer_name", "sf_account_id", "sf_opp_id",
    "motion", "p1_days_low", "p1_days_high", "p1_days_mid", "pm_required",
    "shape", "motion_p2", "binding_constraints", "prose_diagnosis",
    "prose_consequence", "quarter", "notes",
]

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_sheet() -> gspread.Worksheet:
    creds, _ = _google_default(scopes=_SCOPES)
    # gspread v6 removed gspread.authorize(); use Client directly
    client = gspread.Client(auth=creds)
    client.session = AuthorizedSession(creds)
    return client.open_by_key(SHEET_ID).sheet1


def read_scoping_log() -> list[dict]:
    """Return all non-header rows as dicts. Skips rows with blank p1_days_mid."""
    sheet = _get_sheet()
    all_rows = sheet.get_all_values()
    if not all_rows:
        return []
    data_rows = all_rows[1:]  # skip header
    result = []
    for row in data_rows:
        # Pad short rows to 17 columns
        padded = row + [""] * (17 - len(row))
        d = dict(zip(COLUMNS, padded))
        if not d.get("p1_days_mid", "").strip():
            continue  # resident_architect rows — excluded from capacity totals
        result.append(d)
    return result


def append_estimate_row(row: dict) -> None:
    """Append one estimate row to the sheet. `row` must have all 17 COLUMNS keys."""
    sheet = _get_sheet()
    values = [row.get(col, "") for col in COLUMNS]
    sheet.append_row(values, value_input_option="USER_ENTERED")
