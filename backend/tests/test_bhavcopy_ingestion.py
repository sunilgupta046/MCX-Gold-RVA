import io
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app
from app.services.bhavcopy_parser import (
    parse_requested_date,
    parse_compact_expiry_date,
    parse_response_date,
    parse_and_validate_bhavcopy_csv,
)
from app.services.mcx_adapter import MCXBhavcopyAdapter, is_known_holiday_or_weekend
from app.models.bhavcopy import BhavcopyRecord
from app.models.ingestion_log import IngestionLog

client = TestClient(app)


def test_parse_requested_date_ddmmyyyy():
    # Requirement 3: Parse requested date in DD/MM/YYYY format
    d = parse_requested_date("21/10/2026")
    assert d == date(2026, 10, 21)

    d2 = parse_requested_date("04/09/2024")
    assert d2 == date(2024, 9, 4)

    # Invalid formats
    with pytest.raises(ValueError):
        parse_requested_date("invalid-date-string")


def test_parse_compact_expiry_date():
    # Requirement 5: Parse compact ExpiryDate values such as 04SEP2026
    d1 = parse_compact_expiry_date("04SEP2026")
    assert d1 == date(2026, 9, 4)

    d2 = parse_compact_expiry_date("27NOV2024")
    assert d2 == date(2024, 11, 27)

    d3 = parse_compact_expiry_date("05OCT26")
    assert d3 == date(2026, 10, 5)

    d4 = parse_compact_expiry_date("04-SEP-2026")
    assert d4 == date(2026, 9, 4)

    d5 = parse_compact_expiry_date("2026-09-04")
    assert d5 == date(2026, 9, 4)


def test_parse_response_date_formats():
    # Requirement 4: Parse response Date according to source format, including MM/DD/YYYY
    # Unambiguous DD/MM/YYYY (day > 12)
    d1 = parse_response_date("21/10/2026")
    assert d1 == date(2026, 10, 21)

    # Unambiguous MM/DD/YYYY (second part > 12)
    d2 = parse_response_date("10/21/2026")
    assert d2 == date(2026, 10, 21)

    # Ambiguous date with requested_date hint
    req = date(2026, 5, 10)  # 10th May
    d3 = parse_response_date("10/05/2026", requested_date=req)
    assert d3 == req

    # Standard format
    d4 = parse_response_date("2026-10-21")
    assert d4 == date(2026, 10, 21)


def test_symbol_trimming_and_contract_identification():
    # Requirements 6 & 7: Trim whitespace from Symbol and identify GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL
    sample_csv = """Date,Symbol,ExpiryDate,SettlePrice,Volume,OpenInterest
21/10/2026,   GOLDM   ,04SEP2026,78500,5000,10000
21/10/2026, GOLDTEN ,04SEP2026,78520,1200,2000
21/10/2026,GOLDGUINEA  ,04SEP2026,62800,2500,4000
21/10/2026,  GOLDPETAL,04SEP2026,7855,30000,35000
21/10/2026,CRUDEOIL,15NOV2026,6100,50000,20000
21/10/2026,SILVER,05DEC2026,92000,15000,12000
"""
    result = parse_and_validate_bhavcopy_csv(sample_csv.encode("utf-8"), requested_date=date(2026, 10, 21))
    assert result["success"] is True
    assert result["records_count"] == 4
    symbols = {r["symbol"] for r in result["records"]}
    assert symbols == {"GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"}
    assert "CRUDEOIL" not in symbols
    assert "SILVER" not in symbols


def test_never_silently_substitute_different_date():
    # Requirements 8 & 9: Validate requested date against returned date.
    # Never silently substitute a different trading date.
    sample_csv = """Date,Symbol,ExpiryDate,SettlePrice,Volume
20/10/2026,GOLDM,04SEP2026,78400,5000
20/10/2026,GOLDPETAL,04SEP2026,7845,30000
"""
    # User requested 21/10/2026, but file has 20/10/2026
    req_date = date(2026, 10, 21)
    result = parse_and_validate_bhavcopy_csv(sample_csv.encode("utf-8"), requested_date=req_date)
    assert result["success"] is False
    assert result["status"] == "REJECTED_DATE_MISMATCH"
    assert "Silent date substitution is strictly rejected" in result["error_message"]
    assert len(result["records"]) == 0


def test_preserve_distinct_expiry_dates_no_stitching():
    # Requirement 13: Preserve historical contracts by expiry_date; never stitch continuous near-month series.
    sample_csv = """Date,Symbol,ExpiryDate,SettlePrice,Volume
21/10/2026,GOLDM,04SEP2026,78500,5000
21/10/2026,GOLDM,05OCT2026,78650,2000
21/10/2026,GOLDM,04DEC2026,78900,1000
"""
    result = parse_and_validate_bhavcopy_csv(sample_csv.encode("utf-8"), requested_date=date(2026, 10, 21))
    assert result["success"] is True
    assert result["records_count"] == 3
    expiries = {r["expiry_date"] for r in result["records"]}
    assert expiries == {date(2026, 9, 4), date(2026, 10, 5), date(2026, 12, 4)}


def test_deduplication():
    # Requirement 12: Deduplicate records using symbol, trade_date, and expiry_date
    sample_csv = """Date,Symbol,ExpiryDate,SettlePrice,Volume
21/10/2026,GOLDM,04SEP2026,78500,5000
21/10/2026,GOLDM,04SEP2026,78500,5000
21/10/2026,GOLDPETAL,04SEP2026,7855,30000
"""
    result = parse_and_validate_bhavcopy_csv(sample_csv.encode("utf-8"), requested_date=date(2026, 10, 21))
    assert result["success"] is True
    assert result["records_count"] == 2  # GOLDM deduplicated to 1, plus GOLDPETAL


def test_holiday_and_weekend_detection():
    # Requirement 10: Handle holidays, unavailable files
    # Saturday
    is_sat, reason = is_known_holiday_or_weekend(date(2026, 10, 24))
    assert is_sat is True
    assert "Saturday" in reason

    # Sunday
    is_sun, reason = is_known_holiday_or_weekend(date(2026, 10, 25))
    assert is_sun is True
    assert "Sunday" in reason

    # Republic Day (26 Jan)
    is_rep, reason = is_known_holiday_or_weekend(date(2026, 1, 26))
    assert is_rep is True
    assert "Republic Day" in reason


def test_ingestion_api_endpoints():
    # Test status endpoint
    response = client.get("/api/ingestion/status")
    assert response.status_code == 200
    data = response.json()
    assert "total_sessions" in data
    assert "successful_sessions" in data
    assert "rejected_sessions" in data
    assert "recent_logs" in data


def test_manual_csv_upload_endpoint():
    # Test uploading valid CSV
    csv_data = """Date,Symbol,ExpiryDate,SettlePrice,Volume,OpenInterest
21/10/2026,GOLDM,04SEP2026,78500,5000,10000
21/10/2026,GOLDPETAL,04SEP2026,7855,30000,35000
"""
    file_bytes = io.BytesIO(csv_data.encode("utf-8"))
    response = client.post(
        "/api/ingestion/upload?requested_date_str=21/10/2026",
        files={"file": ("test_bhavcopy.csv", file_bytes, "text/csv")}
    )
    assert response.status_code == 200
    log = response.json()
    assert log["status"] in ("SUCCESS", "PARTIAL")
    assert log["records_imported"] == 2
    assert "GOLDM" in log["contracts_found"]
