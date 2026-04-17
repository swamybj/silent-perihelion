"""
Configuration for the Options Trading Analysis Platform.
"""

# ── Section 1256 Eligible Tickers ──────────────────────────────────────────────
# These broad-based index options qualify for 60/40 tax treatment.
SECTION_1256_TICKERS = {
    "^SPX": {"name": "S&P 500 Index", "symbol": "^GSPC", "option_root": "SPX", "section_1256": True},
    "^NDX": {"name": "Nasdaq-100 Index", "symbol": "^NDX", "option_root": "NDX", "section_1256": True},
    "^RUT": {"name": "Russell 2000 Index", "symbol": "^RUT", "option_root": "RUT", "section_1256": True},
    "^XSP": {"name": "Mini S&P 500 Index", "symbol": "^XSP", "option_root": "XSP", "section_1256": True},
    "^DJX": {"name": "Dow Jones Index (1/100)", "symbol": "^DJI", "option_root": "DJX", "section_1256": True},
    "^VIX": {"name": "CBOE Volatility Index", "symbol": "^VIX", "option_root": "VIX", "section_1256": True},
}

# ── Default Custom Tickers (non-1256) ──────────────────────────────────────────
DEFAULT_CUSTOM_TICKERS = {
    "SPY": {"name": "SPDR S&P 500 ETF", "symbol": "SPY", "section_1256": False},
    "QQQ": {"name": "Invesco QQQ ETF", "symbol": "QQQ", "section_1256": False},
    "IWM": {"name": "iShares Russell 2000 ETF", "symbol": "IWM", "section_1256": False},
}

# ── Options Pricing Defaults ───────────────────────────────────────────────────
RISK_FREE_RATE = 0.045  # Fallback rate; app will try to fetch live 10Y Treasury
RISK_FREE_RATE_TICKER = "^TNX"  # 10-Year Treasury Yield (yfinance)

# ── Backtesting Defaults ──────────────────────────────────────────────────────
BACKTEST_YEARS_OPTIONS = [1, 2, 3, 5, 7, 10]
BACKTEST_DEFAULT_YEARS = 2

# ── Technical Analysis Parameters ─────────────────────────────────────────────
TA_CONFIG = {
    "rsi_period": 14,
    "atr_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "sma_periods": [20, 50, 200],
    "bollinger_period": 20,
    "bollinger_std": 2,
    "fib_lookback_days": 60,  # Days to look back for swing high/low
}

# ── Strategy Defaults ─────────────────────────────────────────────────────────
STRATEGY_DEFAULTS = {
    "delta_range": (0.05, 0.95),
    "default_delta": 0.16,
    "profit_target_pct": 50,  # Close at 50% of max profit
    "stop_loss_pct": 200,     # Close at 200% of credit received (2x loss)
    "min_dte": 7,
    "max_dte": 90,
}

import os

# ── Server Config ─────────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))
DEBUG = True

