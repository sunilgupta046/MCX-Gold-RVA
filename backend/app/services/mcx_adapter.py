import uuid
import logging
import httpx
from datetime import date, timedelta
from typing import Optional, List, Dict, Any, Union, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.models.bhavcopy import BhavcopyRecord
from app.models.ingestion_log import IngestionLog
from app.services.bhavcopy_parser import (
    parse_requested_date,
    parse_and_validate_bhavcopy_csv,
    TARGET_SYMBOLS
)
from app.services.ingestion import process_normalization_and_spreads, seed_contracts

logger = logging.getLogger("mcx_gold_rva.ingestion")

# Standard MCX Trading Holidays (National/Gazetted Indian Holidays)
KNOWN_MCX_HOLIDAYS_FIXED = {
    (1, 26): "Republic Day",
    (5, 1): "Maharashtra Day",
    (8, 15): "Independence Day",
    (10, 2): "Mahatma Gandhi Jayanti",
    (12, 25): "Christmas",
}


def is_known_holiday_or_weekend(d: date) -> Tuple[bool, str]:
    """Checks if date is a Saturday, Sunday, or fixed national holiday."""
    if d.weekday() == 5:
        return True, "Saturday (Market Closed)"
    if d.weekday() == 6:
        return True, "Sunday (Market Closed)"
    
    holiday_name = KNOWN_MCX_HOLIDAYS_FIXED.get((d.month, d.day))
    if holiday_name:
        return True, f"Official Market Holiday: {holiday_name}"
    
    return False, ""


class MCXBhavcopyAdapter:
    """
    Configurable adapter for MCX India Bhavcopy ingestion.
    Adheres strictly to project rules:
      - Uses official base URL https://www.mcxindia.com/market-data/bhavcopy
      - Does NOT invent undocumented permanent URLs
      - Robustly handles holidays, 403 WAF challenges, network timeouts, malformed files
      - Provides seamless fallback to manual CSV upload
      - Idempotent database storage preserving all expiry dates
    """

    def __init__(
        self,
        base_url: str = "https://www.mcxindia.com/market-data/bhavcopy",
        custom_download_template: Optional[str] = None,
        timeout: float = 15.0
    ):
        self.base_url = base_url
        self.custom_download_template = custom_download_template
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/csv,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.mcxindia.com/",
            "Connection": "keep-alive",
        }

    async def fetch_daily_bhavcopy(
        self,
        target_date: date,
        batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Attempts to fetch Bhavcopy from MCX for a specific date using HTTPX.
        Handles weekends, holidays, WAF challenges, and network errors.
        """
        batch_id = batch_id or str(uuid.uuid4())
        date_str_ddmmyyyy = target_date.strftime("%d/%m/%Y")

        # 1. Check for weekend / holiday
        is_holiday, reason = is_known_holiday_or_weekend(target_date)
        if is_holiday:
            return {
                "success": False,
                "status": "HOLIDAY_OR_WEEKEND",
                "batch_id": batch_id,
                "requested_date": target_date,
                "requested_date_str": date_str_ddmmyyyy,
                "returned_date": None,
                "error_message": f"Non-trading date: {reason}",
                "records": [],
                "contracts_found": [],
                "missing_contracts": list(TARGET_SYMBOLS),
                "validation_errors": [reason],
                "raw_file_size": 0,
                "http_status_code": None
            }

        # 2. Construct download target if custom template configured, or use official page
        download_url = self.base_url
        if self.custom_download_template:
            # e.g., if user configures a local mirror or authorized proxy
            download_url = self.custom_download_template.format(
                date=target_date.strftime("%d%m%Y"),
                date_iso=target_date.isoformat(),
                year=target_date.year,
                month=target_date.strftime("%m"),
                day=target_date.strftime("%d")
            )

        logger.info(f"Attempting to fetch MCX Bhavcopy for {date_str_ddmmyyyy} from {download_url}")

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(download_url)
                status_code = response.status_code

                if status_code == 403:
                    # Akamai / WAF challenge
                    err_msg = (
                        f"MCX India server returned HTTP 403 Forbidden (Akamai bot protection). "
                        f"Direct automated HTTP download is blocked by exchange firewall rules. "
                        f"Please use the Manual CSV Upload button to upload official Bhavcopy for {date_str_ddmmyyyy}."
                    )
                    return {
                        "success": False,
                        "status": "UNAVAILABLE_FILE",
                        "batch_id": batch_id,
                        "requested_date": target_date,
                        "requested_date_str": date_str_ddmmyyyy,
                        "error_message": err_msg,
                        "records": [],
                        "contracts_found": [],
                        "missing_contracts": list(TARGET_SYMBOLS),
                        "validation_errors": [err_msg],
                        "raw_file_size": len(response.content),
                        "http_status_code": 403
                    }

                if status_code == 404:
                    err_msg = f"MCX Bhavcopy not found (404) for {date_str_ddmmyyyy}. File may not yet be published or market was closed."
                    return {
                        "success": False,
                        "status": "HOLIDAY_OR_WEEKEND",
                        "batch_id": batch_id,
                        "requested_date": target_date,
                        "requested_date_str": date_str_ddmmyyyy,
                        "error_message": err_msg,
                        "records": [],
                        "contracts_found": [],
                        "missing_contracts": list(TARGET_SYMBOLS),
                        "validation_errors": [err_msg],
                        "raw_file_size": 0,
                        "http_status_code": 404
                    }

                if status_code != 200:
                    err_msg = f"Unexpected HTTP status {status_code} returned by MCX portal."
                    return {
                        "success": False,
                        "status": "NETWORK_ERROR",
                        "batch_id": batch_id,
                        "requested_date": target_date,
                        "requested_date_str": date_str_ddmmyyyy,
                        "error_message": err_msg,
                        "records": [],
                        "contracts_found": [],
                        "missing_contracts": list(TARGET_SYMBOLS),
                        "validation_errors": [err_msg],
                        "raw_file_size": len(response.content),
                        "http_status_code": status_code
                    }

                # If returned HTML instead of CSV (e.g. portal search page)
                content_type = response.headers.get("content-type", "").lower()
                if "html" in content_type and not (b"FUTCOM" in response.content or b"GOLDM" in response.content):
                    err_msg = (
                        f"MCX returned an HTML landing page instead of a CSV data stream for {date_str_ddmmyyyy}. "
                        f"Direct programmatic download is restricted without session cookies. Use manual CSV upload."
                    )
                    return {
                        "success": False,
                        "status": "UNAVAILABLE_FILE",
                        "batch_id": batch_id,
                        "requested_date": target_date,
                        "requested_date_str": date_str_ddmmyyyy,
                        "error_message": err_msg,
                        "records": [],
                        "contracts_found": [],
                        "missing_contracts": list(TARGET_SYMBOLS),
                        "validation_errors": [err_msg],
                        "raw_file_size": len(response.content),
                        "http_status_code": 200
                    }

                # Parse CSV content using robust parser
                parse_result = parse_and_validate_bhavcopy_csv(
                    csv_content=response.content,
                    requested_date=target_date,
                    filename=f"mcx_bhavcopy_{target_date.strftime('%Y%m%d')}.csv"
                )
                parse_result["batch_id"] = batch_id
                parse_result["requested_date"] = target_date
                parse_result["requested_date_str"] = date_str_ddmmyyyy
                parse_result["http_status_code"] = 200
                return parse_result

        except (httpx.TimeoutException, httpx.NetworkError) as net_err:
            err_msg = f"Network connection error contacting MCX portal: {str(net_err)}"
            return {
                "success": False,
                "status": "NETWORK_ERROR",
                "batch_id": batch_id,
                "requested_date": target_date,
                "requested_date_str": date_str_ddmmyyyy,
                "error_message": err_msg,
                "records": [],
                "contracts_found": [],
                "missing_contracts": list(TARGET_SYMBOLS),
                "validation_errors": [err_msg],
                "raw_file_size": 0,
                "http_status_code": None
            }
        except Exception as e:
            err_msg = f"Unexpected ingestion error: {str(e)}"
            return {
                "success": False,
                "status": "ERROR",
                "batch_id": batch_id,
                "requested_date": target_date,
                "requested_date_str": date_str_ddmmyyyy,
                "error_message": err_msg,
                "records": [],
                "contracts_found": [],
                "missing_contracts": list(TARGET_SYMBOLS),
                "validation_errors": [err_msg],
                "raw_file_size": 0,
                "http_status_code": None
            }

    @staticmethod
    def save_parsed_records(
        db: Session,
        parsed_data: Dict[str, Any],
        source_type: str = "MCX_HTTP_FETCH"
    ) -> IngestionLog:
        """
        Idempotently persists validated Bhavcopy records and creates an IngestionLog entry.
        Preserves all contracts by expiry_date (never stitches near-month series).
        """
        seed_contracts(db)

        batch_id = parsed_data.get("batch_id") or str(uuid.uuid4())
        req_date = parsed_data.get("requested_date")
        req_date_str = parsed_data.get("requested_date_str") or (req_date.strftime("%d/%m/%Y") if req_date else None)
        ret_date = parsed_data.get("returned_date") or parsed_data.get("trade_date")
        ret_date_str = ret_date.strftime("%d/%m/%Y") if ret_date else None
        status = parsed_data.get("status", "ERROR")
        records = parsed_data.get("records", [])

        records_imported = 0

        # Requirement 12, 13, 14: Deduplicate and save idempotently
        if parsed_data.get("success") and records:
            for r in records:
                # Check for existing record by (trade_date, symbol, expiry_date)
                existing = (
                    db.query(BhavcopyRecord)
                    .filter(
                        BhavcopyRecord.trade_date == r["trade_date"],
                        BhavcopyRecord.symbol == r["symbol"],
                        BhavcopyRecord.expiry_date == r["expiry_date"]
                    )
                    .first()
                )

                if existing:
                    # Update fields idempotently
                    existing.open_price = r["open_price"]
                    existing.high_price = r["high_price"]
                    existing.low_price = r["low_price"]
                    existing.close_price = r["close_price"]
                    existing.settle_price = r["settle_price"]
                    existing.volume_lots = r["volume_lots"]
                    existing.volume_value_lakhs = r["volume_value_lakhs"]
                    existing.open_interest = r["open_interest"]
                    existing.change_in_oi = r["change_in_oi"]
                    existing.is_demo = False
                    existing.data_source = r.get("data_source", "MCX_BHAVCOPY")
                else:
                    new_rec = BhavcopyRecord(**r)
                    db.add(new_rec)

                records_imported += 1

            db.commit()
            # Recompute analytics pipeline
            process_normalization_and_spreads(db)

        # Requirement 11: Store raw import metadata and validation errors
        log_entry = IngestionLog(
            batch_id=batch_id,
            requested_date=req_date,
            requested_date_str=req_date_str,
            returned_date=ret_date,
            returned_date_str=ret_date_str,
            source_type=source_type,
            status=status,
            records_imported=records_imported,
            contracts_found=parsed_data.get("contracts_found", []),
            missing_contracts=parsed_data.get("missing_contracts", []),
            error_message=parsed_data.get("error_message"),
            validation_errors=parsed_data.get("validation_errors"),
            raw_file_name=parsed_data.get("raw_file_name"),
            raw_file_size=parsed_data.get("raw_file_size"),
            http_status_code=parsed_data.get("http_status_code")
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        return log_entry
