from datetime import date
from typing import Dict, Any

# Standard MCX contract specifications (verified from MCX exchange circulars)
# Source: MCX Contract Specifications, https://www.mcxindia.com/trade/contract-specifications
# Reference purity standard: 999 fineness (24-carat, 99.9% pure gold)
# Formula: normalized_price_per_pure_gram = settle_price / quotation_base_grams * (REFERENCE_PURITY / contract_purity)
REFERENCE_PURITY = 999.0  # Standard 999 fineness reference

CONTRACT_SPECS: Dict[str, Dict[str, Any]] = {
    "GOLDM": {
        "name": "Gold Mini",
        "trading_unit_grams": 100.0,
        "quotation_base_grams": 10.0,   # Quoted in ₹ per 10 grams
        "quotation_unit_grams": 10.0,   # Alias kept for backward compat
        "purity": 995.0,                # 995 fineness (99.5%) – verified MCX spec
        "tick_size": 1.0,
        "contract_multiplier": 10.0,    # 100g / 10g quote = 10
        "description": "MCX Gold Mini 100 grams contract, quoted in ₹ per 10 grams. Purity: 995 (99.5%)."
    },
    "GOLDTEN": {
        "name": "Gold Ten",
        "trading_unit_grams": 10.0,
        "quotation_base_grams": 10.0,   # Quoted in ₹ per 10 grams
        "quotation_unit_grams": 10.0,
        "purity": 999.0,                # 999 fineness (99.9%) – verified MCX spec
        "tick_size": 1.0,
        "contract_multiplier": 1.0,     # 10g / 10g quote = 1
        "description": "MCX Gold 10 grams contract, quoted in ₹ per 10 grams. Purity: 999 (99.9%)."
    },
    "GOLDGUINEA": {
        "name": "Gold Guinea",
        "trading_unit_grams": 8.0,
        "quotation_base_grams": 8.0,    # Quoted in ₹ per 8 grams (1 sovereign)
        "quotation_unit_grams": 8.0,
        "purity": 999.0,                # 999 fineness (99.9%) – verified MCX spec
        "tick_size": 1.0,
        "contract_multiplier": 1.0,     # 8g / 8g quote = 1
        "description": "MCX Gold Guinea 8 grams contract, quoted in ₹ per 8 grams. Purity: 999 (99.9%)."
    },
    "GOLDPETAL": {
        "name": "Gold Petal",
        "trading_unit_grams": 1.0,
        "quotation_base_grams": 1.0,    # Quoted in ₹ per 1 gram
        "quotation_unit_grams": 1.0,
        "purity": 999.0,                # 999 fineness (99.9%) – verified MCX spec
        "tick_size": 1.0,
        "contract_multiplier": 1.0,     # 1g / 1g quote = 1
        "description": "MCX Gold Petal 1 gram contract, quoted in ₹ per 1 gram. Purity: 999 (99.9%)."
    }
}


def normalize_price(symbol: str, raw_settle_price: float) -> Dict[str, float]:
    """
    Normalizes any MCX gold contract settlement price to a common 999-purity basis.

    This allows meaningful cross-contract comparisons by removing purity differences.
    GOLDM trades at 995 fineness; GOLDTEN/GUINEA/PETAL at 999 fineness.

    Formula:
        price_per_gram         = raw_settle_price / quotation_base_grams
        price_per_10g          = price_per_gram * 10.0
        price_per_pure_gram_999 = price_per_gram * (REFERENCE_PURITY / contract_purity)
                                = price_per_gram * (999 / purity)

    The ~0.4% GOLDM purity adjustment (999/995 ≈ 1.00402) is critical for
    accurate cross-contract spread analytics. Without it, GOLDM appears
    persistently cheap by ~₹320/10g at ₹80,000 levels.

    Returns:
        price_per_gram:          Raw INR per 1 gram (no purity adjustment)
        price_per_10g:           Raw INR per 10 grams (no purity adjustment)
        price_per_pure_gram_999: INR per 1 gram of 999-purity gold (cross-contract comparable)
        quotation_base_grams:    The contract's quotation base in grams
        purity:                  Contract fineness (e.g. 995 or 999)
        purity_adjustment_factor: REFERENCE_PURITY / purity applied
    """
    spec = CONTRACT_SPECS.get(symbol.upper())
    if not spec:
        # Unknown symbol: assume 999 purity and per-10g quotation
        quotation_base = 10.0
        purity = 999.0
    else:
        quotation_base = spec["quotation_base_grams"]
        purity = spec["purity"]

    purity_adjustment_factor = REFERENCE_PURITY / purity

    price_per_gram = raw_settle_price / quotation_base
    price_per_10g = price_per_gram * 10.0
    price_per_pure_gram_999 = price_per_gram * purity_adjustment_factor

    return {
        "price_per_gram": round(price_per_gram, 4),
        "price_per_10g": round(price_per_10g, 2),
        "price_per_pure_gram_999": round(price_per_pure_gram_999, 4),
        "quotation_base_grams": quotation_base,
        "purity": purity,
        "purity_adjustment_factor": round(purity_adjustment_factor, 6)
    }


def calculate_days_to_expiry(trade_date: date, expiry_date: date) -> int:
    """Calculates integer calendar days remaining until contract expiry."""
    return max(0, (expiry_date - trade_date).days)
