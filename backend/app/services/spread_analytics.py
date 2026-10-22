import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from datetime import date
from scipy import stats


def calculate_pair_spread(
    base_prices: pd.Series,
    quote_prices: pd.Series
) -> pd.Series:
    """Calculates price difference (Base - Quote) per 10g."""
    return base_prices - quote_prices


def calculate_rolling_z_score(
    spread_series: pd.Series,
    window: int = 20
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Computes rolling mean, rolling standard deviation, and rolling Z-Score.
    Z = (Spread - Mean) / Std
    """
    rolling_mean = spread_series.rolling(window=window, min_periods=max(3, window // 2)).mean()
    rolling_std = spread_series.rolling(window=window, min_periods=max(3, window // 2)).std()
    
    # Avoid zero division
    rolling_std_clamped = rolling_std.replace(0, np.nan)
    z_score = (spread_series - rolling_mean) / rolling_std_clamped
    z_score = z_score.fillna(0.0)

    return rolling_mean, rolling_std, z_score


def calculate_half_life(spread_series: pd.Series) -> float | None:
    """
    Estimates the half-life of mean reversion using an Ornstein-Uhlenbeck / AR(1) process:
      Delta Spread_t = lambda * (Spread_{t-1} - mu) + error
      Half-life = -ln(2) / lambda
    """
    clean_series = spread_series.dropna()
    if len(clean_series) < 10:
        return None

    lagged = clean_series.shift(1).dropna()
    delta = (clean_series - clean_series.shift(1)).dropna()

    # Align series
    common_idx = lagged.index.intersection(delta.index)
    x = lagged.loc[common_idx].values
    y = delta.loc[common_idx].values

    # Add constant for OLS
    x_matrix = np.vstack([x, np.ones(len(x))]).T
    try:
        slope, intercept = np.linalg.lstsq(x_matrix, y, rcond=None)[0]
        if not np.isfinite(slope) or slope >= 0 or np.isclose(slope, 0.0, atol=1e-12):
            return None
        half_life = -np.log(2) / slope
        if not np.isfinite(half_life):
            return None
        return round(float(half_life), 2)
    except np.linalg.LinAlgError:
        return None


def compute_correlation_matrix(df_pivoted: pd.DataFrame) -> Dict[str, Any]:
    """Computes correlation matrix between all gold contracts normalized prices."""
    corr_matrix = df_pivoted.corr().fillna(0.0)
    contracts = list(corr_matrix.columns)
    matrix_values = [[round(float(val), 4) for val in row] for row in corr_matrix.values]
    
    return {
        "contracts": contracts,
        "matrix": matrix_values
    }
