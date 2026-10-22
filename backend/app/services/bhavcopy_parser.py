import re
import io
import pandas as pd
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Union, Tuple

TARGET_SYMBOLS = {"GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"}

MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}


def parse_requested_date(date_str: Union[str, date]) -> date:
    """
    Parses user-requested date in DD/MM/YYYY format per Requirement 3.
    Also accepts date objects or ISO YYYY-MM-DD for API convenience.
    """
    if isinstance(date_str, date):
        return date_str
    
    clean_str = date_str.strip()
    
    # Try DD/MM/YYYY or DD-MM-YYYY
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(clean_str, fmt).date()
        except ValueError:
            pass

    # Try ISO YYYY-MM-DD
    try:
        return datetime.strptime(clean_str, "%Y-%m-%d").date()
    except ValueError:
        pass

    raise ValueError(f"Invalid date format '{date_str}'. Expected DD/MM/YYYY (e.g., 21/10/2026).")


def parse_compact_expiry_date(raw_expiry: Any) -> date:
    """
    Parses compact ExpiryDate values such as '04SEP2026', '04-SEP-2026',
    '27NOV2024', '05OCT26', '04/09/2026', or '2026-09-04' per Requirement 5.
    """
    if isinstance(raw_expiry, (datetime, pd.Timestamp)):
        return raw_expiry.date()
    if isinstance(raw_expiry, date):
        return raw_expiry

    val = str(raw_expiry).strip().upper()
    if not val or val == "NAN" or val == "NONE":
        raise ValueError("Expiry date is empty or null.")

    # 1. Match compact format like 04SEP2026 or 04SEP26 or 04-SEP-2026
    match_alpha = re.match(r"^(\d{1,2})[-/]?([A-Z]{3})[-/]?(\d{2,4})$", val)
    if match_alpha:
        day = int(match_alpha.group(1))
        mon_str = match_alpha.group(2)
        year_val = int(match_alpha.group(3))
        
        # 2-digit year conversion
        if year_val < 100:
            year_val = 2000 + year_val

        month = MONTH_MAP.get(mon_str)
        if not month:
            raise ValueError(f"Unrecognized month abbreviation '{mon_str}' in expiry '{val}'.")

        return date(year_val, month, day)

    # 2. Match standard date formats DD/MM/YYYY, YYYY-MM-DD, MM/DD/YYYY
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y", "%d/%b/%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            pass

    raise ValueError(f"Unable to parse compact ExpiryDate '{raw_expiry}'.")


def parse_response_date(raw_val: Any, requested_date: Optional[date] = None) -> date:
    """
    Parses the response Date from Bhavcopy source, intelligently handling:
      - DD/MM/YYYY
      - MM/DD/YYYY
      - YYYY-MM-DD
      - DD-Mon-YYYY
    If requested_date is provided, uses it to disambiguate DD/MM vs MM/DD if ambiguous.
    """
    if isinstance(raw_val, (datetime, pd.Timestamp)):
        return raw_val.date()
    if isinstance(raw_val, date):
        return raw_val

    val = str(raw_val).strip()
    if not val or val.upper() in ("NAN", "NONE"):
        raise ValueError("Response date is empty or null.")

    # Check DD-Mon-YYYY first (e.g. 21-Oct-2026)
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d/%b/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            pass

    # For numeric slashed or hyphenated dates like 10/05/2026 or 21/10/2026
    match = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", val)
    if match:
        p1 = int(match.group(1))
        p2 = int(match.group(2))
        year = int(match.group(3))

        # If p1 > 12, p1 MUST be day -> DD/MM/YYYY
        if p1 > 12:
            return date(year, p2, p1)
        # If p2 > 12, p2 MUST be day -> MM/DD/YYYY
        if p2 > 12:
            return date(year, p1, p2)

        # If ambiguous (both <= 12), use requested_date to disambiguate if available
        if requested_date:
            if requested_date.year == year:
                if requested_date.day == p1 and requested_date.month == p2:
                    return date(year, p2, p1)
                elif requested_date.day == p2 and requested_date.month == p1:
                    return date(year, p1, p2)

        # Default standard Indian format DD/MM/YYYY
        return date(year, p2, p1)

    raise ValueError(f"Unable to parse response date '{raw_val}'.")


def parse_and_validate_bhavcopy_csv(
    csv_content: Union[bytes, str],
    requested_date: Optional[date] = None,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parses and thoroughly validates an MCX Bhavcopy CSV file according to requirements:
      - Trims whitespace from Symbol values
      - Identifies GOLDM, GOLDTEN, GOLDGUINEA, and GOLDPETAL
      - Validates requested date against returned date (never silently substitutes)
      - Parses compact ExpiryDate (e.g. 04SEP2026)
      - Preserves historical contracts by distinct expiry_date (no near-month stitching)
      - Deduplicates records
      - Flags missing contracts
    """
    if isinstance(csv_content, str):
        csv_bytes = csv_content.encode("utf-8")
    else:
        csv_bytes = csv_content

    file_size = len(csv_bytes)
    if file_size == 0:
        return {
            "success": False,
            "status": "MALFORMED",
            "error_message": "Empty file received (0 bytes).",
            "records": [],
            "raw_file_name": filename,
            "raw_file_size": 0,
            "validation_errors": ["File contains no data."]
        }

    # Attempt to read CSV with pandas
    try:
        # Try utf-8 first, fallback to latin1
        try:
            df = pd.read_csv(io.BytesIO(csv_bytes), skipinitialspace=True)
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(csv_bytes), encoding="latin1", skipinitialspace=True)
    except Exception as e:
        return {
            "success": False,
            "status": "MALFORMED",
            "error_message": f"Malformed CSV structure: {str(e)}",
            "records": [],
            "raw_file_name": filename,
            "raw_file_size": file_size,
            "validation_errors": [str(e)]
        }

    if df.empty:
        return {
            "success": False,
            "status": "MALFORMED",
            "error_message": "CSV file contains header only with zero data rows.",
            "records": [],
            "raw_file_name": filename,
            "raw_file_size": file_size,
            "validation_errors": ["Zero data rows found in CSV."]
        }

    # Normalize column names (strip whitespace and lower case)
    col_map = {str(c).strip().lower(): c for c in df.columns}

    # Identify essential columns
    sym_col = None
    for candidate in ["symbol", "instrument_name", "commodity", "scrip"]:
        for k in col_map:
            if candidate == k or candidate in k:
                sym_col = col_map[k]
                break
        if sym_col:
            break

    date_col = None
    for candidate in ["date", "trade_date", "tradedate", "business_date"]:
        for k in col_map:
            if candidate == k or k.startswith("date"):
                date_col = col_map[k]
                break
        if date_col:
            break

    expiry_col = None
    for candidate in ["expiry_date", "expirydate", "expiry", "exp_date"]:
        for k in col_map:
            if candidate == k.replace(" ", "_"):
                expiry_col = col_map[k]
                break
        if expiry_col:
            break

    settle_col = None
    for candidate in ["settle_price", "settlement_price", "settleprice", "close", "closing_price"]:
        for k in col_map:
            if candidate in k.replace(" ", "_"):
                settle_col = col_map[k]
                break
        if settle_col:
            break

    # Optional price and volume columns
    open_col = next((col_map[k] for k in col_map if k in ["open", "open_price", "openprice"]), None)
    high_col = next((col_map[k] for k in col_map if k in ["high", "high_price", "highprice"]), None)
    low_col = next((col_map[k] for k in col_map if k in ["low", "low_price", "lowprice"]), None)
    close_col = next((col_map[k] for k in col_map if k in ["close", "close_price", "closeprice"]), None)
    vol_col = next((col_map[k] for k in col_map if any(v in k for v in ["volume", "qty", "volume_lots"])), None)
    val_col = next((col_map[k] for k in col_map if any(v in k for v in ["value", "turnover"])), None)
    oi_col = next((col_map[k] for k in col_map if any(v in k for v in ["oi", "open_interest", "openinterest"])), None)
    coi_col = next((col_map[k] for k in col_map if any(v in k for v in ["change_in_oi", "chg_in_oi", "changeinoi"])), None)

    if not sym_col or not date_col or not settle_col:
        missing_cols = []
        if not sym_col: missing_cols.append("Symbol")
        if not date_col: missing_cols.append("Date")
        if not settle_col: missing_cols.append("Settlement Price")
        return {
            "success": False,
            "status": "MALFORMED",
            "error_message": f"CSV missing mandatory columns: {', '.join(missing_cols)}. Found headers: {list(df.columns)}",
            "records": [],
            "raw_file_name": filename,
            "raw_file_size": file_size,
            "validation_errors": [f"Missing required columns: {missing_cols}"]
        }

    # Process and filter records
    validation_errors = []
    valid_records = []
    seen_keys = set()
    contracts_found = set()
    detected_trade_dates = set()

    for idx, row in df.iterrows():
        raw_sym = row[sym_col]
        if pd.isna(raw_sym):
            continue

        # Requirement 6: Trim whitespace from Symbol values
        symbol = str(raw_sym).strip().upper()

        # Requirement 7: Identify GOLDM, GOLDTEN, GOLDGUINEA, and GOLDPETAL
        if symbol not in TARGET_SYMBOLS:
            continue

        contracts_found.add(symbol)

        # Parse trade date
        raw_date = row[date_col]
        try:
            trade_date = parse_response_date(raw_date, requested_date)
            detected_trade_dates.add(trade_date)
        except Exception as e:
            validation_errors.append(f"Row {idx}: Invalid trade date '{raw_date}' for {symbol}: {str(e)}")
            continue

        # Parse expiry date
        raw_expiry = row[expiry_col] if expiry_col and pd.notna(row[expiry_col]) else None
        if raw_expiry is not None:
            try:
                # Requirement 5: Parse compact ExpiryDate values such as 04SEP2026
                expiry_date = parse_compact_expiry_date(raw_expiry)
            except Exception as e:
                validation_errors.append(f"Row {idx}: Invalid expiry date '{raw_expiry}' for {symbol}: {str(e)}")
                continue
        else:
            # Fallback default 1 month if expiry column omitted in custom feed
            expiry_date = trade_date

        # Parse settlement price
        try:
            settle_val = float(str(row[settle_col]).replace(",", "").strip())
            if settle_val <= 0 or pd.isna(settle_val):
                validation_errors.append(f"Row {idx}: Non-positive settle price '{row[settle_col]}' for {symbol}.")
                continue
        except Exception:
            validation_errors.append(f"Row {idx}: Malformed settle price '{row[settle_col]}' for {symbol}.")
            continue

        # Parse optional fields
        def _get_float(c):
            if c and pd.notna(row[c]):
                try:
                    return float(str(row[c]).replace(",", "").strip())
                except:
                    return None
            return None

        def _get_int(c):
            if c and pd.notna(row[c]):
                try:
                    return int(float(str(row[c]).replace(",", "").strip()))
                except:
                    return 0
            return 0

        open_p = _get_float(open_col) or settle_val
        high_p = _get_float(high_col) or max(open_p, settle_val)
        low_p = _get_float(low_col) or min(open_p, settle_val)
        close_p = _get_float(close_col) or settle_val
        vol_val = _get_int(vol_col)
        val_lakhs = _get_float(val_col) or 0.0
        oi_val = _get_int(oi_col)
        coi_val = _get_int(coi_col)

        # Requirement 12 & 13: Deduplicate records using (symbol, trade_date, expiry_date)
        # Preserve historical contracts by expiry_date; never stitch a continuous near-month series.
        dedup_key = (symbol, trade_date, expiry_date)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        valid_records.append({
            "trade_date": trade_date,
            "symbol": symbol,
            "expiry_date": expiry_date,
            "open_price": round(open_p, 2),
            "high_price": round(high_p, 2),
            "low_price": round(low_p, 2),
            "close_price": round(close_p, 2),
            "settle_price": round(settle_val, 2),
            "volume_lots": vol_val,
            "volume_value_lakhs": round(val_lakhs, 2),
            "open_interest": oi_val,
            "change_in_oi": coi_val,
            "is_demo": False,
            "data_source": f"MCX_BHAVCOPY_{filename or 'PUBLIC'}"
        })

    # Requirement 8 & 9: Validate requested date against returned date.
    # Never silently substitute a different trading date.
    primary_returned_date = next(iter(detected_trade_dates), None)
    if requested_date and primary_returned_date:
        if primary_returned_date != requested_date:
            err_msg = (
                f"Date Mismatch Violation: Requested date was {requested_date.strftime('%d/%m/%Y')} "
                f"({requested_date}), but source Bhavcopy file contains trading date "
                f"{primary_returned_date.strftime('%d/%m/%Y')} ({primary_returned_date}). "
                f"Silent date substitution is strictly rejected per Rule 9."
            )
            return {
                "success": False,
                "status": "REJECTED_DATE_MISMATCH",
                "error_message": err_msg,
                "requested_date": requested_date,
                "returned_date": primary_returned_date,
                "records": [],
                "contracts_found": list(contracts_found),
                "missing_contracts": list(TARGET_SYMBOLS - contracts_found),
                "raw_file_name": filename,
                "raw_file_size": file_size,
                "validation_errors": [err_msg]
            }

    # Requirement 10: Check if gold contracts were found
    if not valid_records:
        err_msg = "No valid MCX Gold contracts (GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL) found in Bhavcopy."
        return {
            "success": False,
            "status": "MISSING_CONTRACTS",
            "error_message": err_msg,
            "requested_date": requested_date,
            "returned_date": primary_returned_date,
            "records": [],
            "contracts_found": [],
            "missing_contracts": list(TARGET_SYMBOLS),
            "raw_file_name": filename,
            "raw_file_size": file_size,
            "validation_errors": validation_errors or [err_msg]
        }

    missing_contracts = list(TARGET_SYMBOLS - contracts_found)
    status = "SUCCESS" if not missing_contracts else "PARTIAL"

    return {
        "success": True,
        "status": status,
        "trade_date": primary_returned_date or requested_date,
        "requested_date": requested_date,
        "returned_date": primary_returned_date,
        "records": valid_records,
        "records_count": len(valid_records),
        "contracts_found": sorted(list(contracts_found)),
        "missing_contracts": sorted(missing_contracts),
        "raw_file_name": filename,
        "raw_file_size": file_size,
        "validation_errors": validation_errors
    }
