from datetime import date
from app.services.normalization import normalize_price, calculate_days_to_expiry, CONTRACT_SPECS


def test_contract_specs():
    assert "GOLDM" in CONTRACT_SPECS
    assert "GOLDTEN" in CONTRACT_SPECS
    assert "GOLDGUINEA" in CONTRACT_SPECS
    assert "GOLDPETAL" in CONTRACT_SPECS

    assert CONTRACT_SPECS["GOLDM"]["trading_unit_grams"] == 100.0
    assert CONTRACT_SPECS["GOLDM"]["quotation_base_grams"] == 10.0
    assert CONTRACT_SPECS["GOLDM"]["purity"] == 995.0

    assert CONTRACT_SPECS["GOLDTEN"]["trading_unit_grams"] == 10.0
    assert CONTRACT_SPECS["GOLDTEN"]["quotation_base_grams"] == 10.0
    assert CONTRACT_SPECS["GOLDTEN"]["purity"] == 999.0

    assert CONTRACT_SPECS["GOLDGUINEA"]["trading_unit_grams"] == 8.0
    assert CONTRACT_SPECS["GOLDGUINEA"]["quotation_base_grams"] == 8.0
    assert CONTRACT_SPECS["GOLDGUINEA"]["purity"] == 999.0

    assert CONTRACT_SPECS["GOLDPETAL"]["trading_unit_grams"] == 1.0
    assert CONTRACT_SPECS["GOLDPETAL"]["quotation_base_grams"] == 1.0
    assert CONTRACT_SPECS["GOLDPETAL"]["purity"] == 999.0


def test_normalize_goldm():
    # GOLDM quoted at ₹78,000 per 10g with 995 purity
    norm = normalize_price("GOLDM", 78000.0)
    assert norm["price_per_gram"] == 7800.0
    assert norm["price_per_10g"] == 78000.0
    assert norm["purity"] == 995.0
    assert norm["quotation_base_grams"] == 10.0
    # 999 purity basis: 7800.0 * (999/995)
    expected_pure = round(7800.0 * (999.0 / 995.0), 4)
    assert norm["price_per_pure_gram_999"] == expected_pure


def test_normalize_goldguinea():
    # GOLDGUINEA quoted at ₹62,400 per 8g (1 sovereign)
    norm = normalize_price("GOLDGUINEA", 62400.0)
    assert norm["price_per_gram"] == 7800.0
    assert norm["price_per_10g"] == 78000.0


def test_normalize_goldpetal():
    # GOLDPETAL quoted at ₹7,800 per 1g
    norm = normalize_price("GOLDPETAL", 7800.0)
    assert norm["price_per_gram"] == 7800.0
    assert norm["price_per_10g"] == 78000.0


def test_days_to_expiry():
    t_date = date(2026, 10, 20)
    exp_date = date(2026, 11, 5)
    dte = calculate_days_to_expiry(t_date, exp_date)
    assert dte == 16
