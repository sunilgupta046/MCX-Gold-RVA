import pandas as pd
import numpy as np
from app.routers.analytics import get_correlation_matrix_endpoint
from app.services.spread_analytics import (
    calculate_pair_spread,
    calculate_rolling_z_score,
    calculate_half_life,
    compute_correlation_matrix
)


def test_spread_calculation():
    base = pd.Series([78000, 78100, 78200])
    quote = pd.Series([78020, 78080, 78250])
    spread = calculate_pair_spread(base, quote)
    assert list(spread) == [-20, 20, -50]


def test_rolling_z_score():
    s = pd.Series(np.linspace(10, 50, 30))
    rm, rstd, z = calculate_rolling_z_score(s, window=10)
    assert len(z) == 30
    assert not z.isna().any()


def test_half_life():
    # Mean-reverting synthetic series
    np.random.seed(123)
    series = [10.0]
    for _ in range(50):
        series.append(0.7 * series[-1] + np.random.normal(0, 1))
    hl = calculate_half_life(pd.Series(series))
    assert hl > 0


def test_half_life_is_unavailable_without_enough_data():
    assert calculate_half_life(pd.Series([1.0, 2.0, 3.0])) is None


def test_half_life_is_unavailable_for_non_mean_reverting_series():
    series = pd.Series(np.arange(20, dtype=float))
    assert calculate_half_life(series) is None


def test_correlation_matrix_is_empty_without_price_data():
    class EmptyQuery:
        def all(self):
            return []

    class EmptyDatabase:
        def query(self, _model):
            return EmptyQuery()

    response = get_correlation_matrix_endpoint(EmptyDatabase())

    assert response.contracts == []
    assert response.matrix == []
