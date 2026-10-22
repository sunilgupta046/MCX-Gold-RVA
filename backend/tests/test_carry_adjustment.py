from app.services.carry_adjustment import calculate_carry_adjustment, get_annualized_carry_rate


def test_carry_adjustment_zero_days():
    # If 0 days to expiry, discount factor should be 1.0 and price unchanged
    res = calculate_carry_adjustment(price_per_10g=78000.0, days_to_expiry=0)
    assert res["discount_factor"] == 1.0
    assert res["carry_adjusted_price_per_10g"] == 78000.0
    assert res["carry_drag_rupees"] == 0.0


def test_carry_adjustment_positive_days():
    # 60 days to expiry with 7% annual carry rate
    res = calculate_carry_adjustment(
        price_per_10g=78000.0,
        days_to_expiry=60,
        benchmark_dte=0,
        annual_carry_rate=0.07
    )
    # Futures price has positive carry, so spot equivalent is lower
    assert res["discount_factor"] < 1.0
    assert res["carry_adjusted_price_per_10g"] < 78000.0
    assert res["carry_drag_rupees"] > 0.0
