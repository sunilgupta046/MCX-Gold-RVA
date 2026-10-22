from app.services.transaction_costs import calculate_transaction_costs, calculate_pair_roundtrip_cost_bps


def test_buy_transaction_costs():
    turnover = 78000.0  # ₹78,000 turnover
    costs = calculate_transaction_costs(turnover_inr=turnover, is_buy=True, slippage_ticks=1)
    
    # Stamp duty should apply on buy leg
    assert costs["stamp_duty"] > 0
    # CTT should be 0 on buy leg
    assert costs["ctt"] == 0.0
    assert costs["total_cost"] > 0
    assert costs["cost_in_bps"] > 0


def test_sell_transaction_costs():
    turnover = 78000.0
    costs = calculate_transaction_costs(turnover_inr=turnover, is_buy=False, slippage_ticks=1)
    
    # CTT applies on sell leg
    assert costs["ctt"] > 0
    # Stamp duty is 0 on sell leg
    assert costs["stamp_duty"] == 0.0
    assert costs["total_cost"] > 0


def test_pair_roundtrip_friction():
    rt = calculate_pair_roundtrip_cost_bps(78000.0, 78050.0, "GOLDM", "GOLDPETAL")
    assert rt["roundtrip_cost_bps"] > 0
    assert rt["total_rt_cost_inr"] > 0
