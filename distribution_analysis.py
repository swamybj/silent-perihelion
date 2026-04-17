"""
Distribution Analysis Module.

Analyzes historical price change distributions:
- Daily return distribution from -5% to +5%
- Normal distribution fit
- Directional probability
- Skewness and kurtosis analysis
"""

import numpy as np
import pandas as pd
from scipy import stats


def analyze_distribution(df, bucket_size=0.5, range_pct=5.0):
    """
    Analyze the distribution of daily price changes.

    Parameters:
        df: DataFrame with OHLCV data (DatetimeIndex)
        bucket_size: Size of each histogram bucket in percentage points
        range_pct: Range to analyze (e.g., 5.0 means -5% to +5%)

    Returns:
        dict with distribution data, statistics, and probabilities
    """
    prices = df["Close"]
    daily_returns = prices.pct_change().dropna() * 100  # Convert to percentage

    # ── Create histogram buckets ─────────────────────────────────────────
    bin_edges = np.arange(-range_pct, range_pct + bucket_size, bucket_size)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    counts, _ = np.histogram(daily_returns, bins=bin_edges)
    total = len(daily_returns)
    frequencies = (counts / total * 100).round(2)  # As percentages

    histogram = []
    for i in range(len(bin_centers)):
        label = f"{bin_edges[i]:+.1f}% to {bin_edges[i+1]:+.1f}%"
        histogram.append({
            "label": label,
            "center": round(float(bin_centers[i]), 2),
            "count": int(counts[i]),
            "frequency_pct": float(frequencies[i]),
        })

    # ── Normal distribution fit ──────────────────────────────────────────
    mean_return = float(daily_returns.mean())
    std_return = float(daily_returns.std())

    normal_pdf = stats.norm.pdf(bin_centers, mean_return, std_return)
    normal_pdf_scaled = normal_pdf * total * bucket_size  # Scale to match histogram

    # ── Directional probabilities ─────────────────────────────────────────
    up_days = (daily_returns > 0).sum()
    down_days = (daily_returns < 0).sum()
    flat_days = (daily_returns == 0).sum()

    # Probability of various moves
    prob_up_1pct = float((daily_returns > 1.0).mean() * 100)
    prob_up_2pct = float((daily_returns > 2.0).mean() * 100)
    prob_up_3pct = float((daily_returns > 3.0).mean() * 100)
    prob_down_1pct = float((daily_returns < -1.0).mean() * 100)
    prob_down_2pct = float((daily_returns < -2.0).mean() * 100)
    prob_down_3pct = float((daily_returns < -3.0).mean() * 100)

    # ── Skewness & Kurtosis ──────────────────────────────────────────────
    skewness = float(daily_returns.skew())
    kurtosis = float(daily_returns.kurtosis())  # Excess kurtosis

    # ── Weekly returns distribution ───────────────────────────────────────
    weekly_prices = prices.resample('W').last().dropna()
    weekly_returns = weekly_prices.pct_change().dropna() * 100

    weekly_bin_edges = np.arange(-range_pct * 2, range_pct * 2 + bucket_size * 2, bucket_size * 2)
    weekly_bin_centers = (weekly_bin_edges[:-1] + weekly_bin_edges[1:]) / 2
    weekly_counts, _ = np.histogram(weekly_returns, bins=weekly_bin_edges)
    weekly_total = len(weekly_returns)
    weekly_freq = (weekly_counts / weekly_total * 100).round(2) if weekly_total > 0 else weekly_counts * 0

    weekly_histogram = []
    for i in range(len(weekly_bin_centers)):
        weekly_histogram.append({
            "label": f"{weekly_bin_edges[i]:+.1f}% to {weekly_bin_edges[i+1]:+.1f}%",
            "center": round(float(weekly_bin_centers[i]), 2),
            "count": int(weekly_counts[i]),
            "frequency_pct": float(weekly_freq[i]),
        })

    return {
        "daily": {
            "histogram": histogram,
            "bin_centers": [round(float(c), 2) for c in bin_centers],
            "counts": [int(c) for c in counts],
            "frequencies": [float(f) for f in frequencies],
            "normal_fit": [round(float(n), 2) for n in normal_pdf_scaled],
        },
        "weekly": {
            "histogram": weekly_histogram,
            "bin_centers": [round(float(c), 2) for c in weekly_bin_centers],
            "counts": [int(c) for c in weekly_counts],
            "frequencies": [float(f) for f in weekly_freq],
        },
        "statistics": {
            "total_days": int(total),
            "mean_daily_return": round(mean_return, 4),
            "std_daily_return": round(std_return, 4),
            "annualized_return": round(mean_return * 252, 2),
            "annualized_vol": round(std_return * np.sqrt(252), 2),
            "skewness": round(skewness, 4),
            "excess_kurtosis": round(kurtosis, 4),
            "fat_tails": "Yes" if kurtosis > 1 else "No",
        },
        "probabilities": {
            "up_day": round(float(up_days / total * 100), 1),
            "down_day": round(float(down_days / total * 100), 1),
            "flat_day": round(float(flat_days / total * 100), 1),
            "up_more_than_1pct": round(prob_up_1pct, 2),
            "up_more_than_2pct": round(prob_up_2pct, 2),
            "up_more_than_3pct": round(prob_up_3pct, 2),
            "down_more_than_1pct": round(prob_down_1pct, 2),
            "down_more_than_2pct": round(prob_down_2pct, 2),
            "down_more_than_3pct": round(prob_down_3pct, 2),
        },
        "extremes": {
            "max_daily_gain": round(float(daily_returns.max()), 2),
            "max_daily_loss": round(float(daily_returns.min()), 2),
            "max_weekly_gain": round(float(weekly_returns.max()), 2) if len(weekly_returns) > 0 else None,
            "max_weekly_loss": round(float(weekly_returns.min()), 2) if len(weekly_returns) > 0 else None,
        },
    }
