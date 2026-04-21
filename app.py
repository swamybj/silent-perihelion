"""
Flask API Server — Options Trading Analysis Platform.

Serves all REST API endpoints and the frontend.
"""

import json
import os
import traceback
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import (
    SECTION_1256_TICKERS, DEFAULT_CUSTOM_TICKERS,
    RISK_FREE_RATE, RISK_FREE_RATE_TICKER,
    BACKTEST_YEARS_OPTIONS, BACKTEST_DEFAULT_YEARS,
    HOST, PORT, DEBUG,
)
from greeks_engine import calc_all_greeks, calc_implied_volatility, find_strike_by_delta
from technical_analysis import run_technical_analysis, get_augmented_df
from strategy_engine import recommend_strategies, build_strategy_legs, STRATEGIES
from backtest_engine import run_backtest
from distribution_analysis import analyze_distribution
from forecaster import MLForecaster
from risk_engine import RiskEngine
from simulator import MarketSimulator


# ── App Setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

# In-memory ticker store
tickers_store = {}
tickers_store.update(SECTION_1256_TICKERS)
tickers_store.update({k: v for k, v in DEFAULT_CUSTOM_TICKERS.items()})

# Cache for fetched data (simple in-memory)
data_cache = {}
CACHE_TTL = 300  # 5 minutes


def _get_risk_free_rate():
    """Fetch the current 10Y Treasury yield, fallback to config."""
    try:
        tnx = yf.Ticker(RISK_FREE_RATE_TICKER)
        hist = tnx.history(period="5d")
        if hist is not None and len(hist) > 0:
            rate = float(hist["Close"].iloc[-1]) / 100.0  # Convert from % to decimal
            return rate
    except Exception:
        pass
    return RISK_FREE_RATE


def _fetch_historical_data(symbol, years=2):
    """Fetch historical OHLCV data with caching."""
    cache_key = f"{symbol}_{years}"
    now = datetime.now().timestamp()

    if cache_key in data_cache:
        cached_time, cached_data = data_cache[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_data

    try:
        ticker = yf.Ticker(symbol)
        period = f"{years}y"
        df = ticker.history(period=period)
        if df is not None and len(df) > 0:
            data_cache[cache_key] = (now, df)
            return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")

    return None


def _get_symbol(ticker_key):
    """Get the yfinance symbol for a ticker key."""
    info = tickers_store.get(ticker_key, {})
    return info.get("symbol", ticker_key)


# ── Static Files ──────────────────────────────────────────────────────────────

@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(".", path)


# ── API: Tickers ──────────────────────────────────────────────────────────────

@app.route("/api/tickers", methods=["GET"])
def get_tickers():
    """List all configured tickers."""
    result = []
    for key, info in tickers_store.items():
        result.append({
            "key": key,
            "name": info.get("name", key),
            "symbol": info.get("symbol", key),
            "section_1256": info.get("section_1256", False),
        })
    return jsonify(result)


@app.route("/api/tickers", methods=["POST"])
def add_ticker():
    """Add a custom ticker."""
    data = request.json
    symbol = data.get("symbol", "").upper().strip()
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400

    # Verify the ticker exists
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if hist is None or len(hist) == 0:
            return jsonify({"error": f"No data found for {symbol}"}), 404
        name = data.get("name", symbol)
    except Exception as e:
        return jsonify({"error": f"Could not validate ticker: {str(e)}"}), 400

    tickers_store[symbol] = {
        "name": name,
        "symbol": symbol,
        "section_1256": data.get("section_1256", False),
    }

    return jsonify({"message": f"Added {symbol}", "key": symbol})


@app.route("/api/tickers/<key>", methods=["DELETE"])
def remove_ticker(key):
    """Remove a ticker."""
    if key in tickers_store:
        del tickers_store[key]
        return jsonify({"message": f"Removed {key}"})
    return jsonify({"error": "Ticker not found"}), 404


# ── API: Market Data ──────────────────────────────────────────────────────────

@app.route("/api/market-data/<ticker_key>", methods=["GET"])
def get_market_data(ticker_key):
    """Get current price and key stats for a ticker."""
    symbol = _get_symbol(ticker_key)
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if hist is None or len(hist) == 0:
            return jsonify({"error": "No data available"}), 404

        current_price = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current_price
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100

        # Try to get option chain expiration dates
        try:
            expirations = list(t.options) if hasattr(t, 'options') else []
        except Exception:
            expirations = []

        return jsonify({
            "symbol": symbol,
            "ticker_key": ticker_key,
            "name": tickers_store.get(ticker_key, {}).get("name", symbol),
            "current_price": round(current_price, 2),
            "prev_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "section_1256": tickers_store.get(ticker_key, {}).get("section_1256", False),
            "option_expirations": expirations[:12],  # Limit to 12
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Technical Analysis ───────────────────────────────────────────────────

@app.route("/api/technical-analysis/<ticker_key>", methods=["GET"])
def get_technical_analysis(ticker_key):
    """Run full technical analysis for a ticker."""
    symbol = _get_symbol(ticker_key)
    try:
        df = _fetch_historical_data(symbol, years=2)
        if df is None or len(df) < 50:
            return jsonify({"error": "Not enough historical data"}), 404

        result = run_technical_analysis(df)
        result["ticker_key"] = ticker_key
        result["symbol"] = symbol
        result["name"] = tickers_store.get(ticker_key, {}).get("name", symbol)

        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── API: Greeks Calculator ────────────────────────────────────────────────────

@app.route("/api/greeks", methods=["POST"])
def calculate_greeks():
    """Calculate Greeks for a specific option."""
    data = request.json
    try:
        S = float(data["underlying_price"])
        K = float(data["strike_price"])
        T = float(data["dte"]) / 365.0
        r = float(data.get("risk_free_rate", _get_risk_free_rate()))
        sigma = float(data["volatility"]) / 100.0  # Input as percentage
        option_type = data.get("option_type", "call").lower()

        greeks = calc_all_greeks(S, K, T, r, sigma, option_type)

        return jsonify({
            "inputs": {"S": S, "K": K, "T": T, "r": r, "sigma": sigma, "type": option_type},
            "greeks": greeks,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ── API: Strategy Analysis ────────────────────────────────────────────────────

@app.route("/api/strategy/analyze", methods=["POST"])
def analyze_strategy():
    """Analyze a specific options strategy."""
    data = request.json
    try:
        ticker_key = data["ticker_key"]
        symbol = _get_symbol(ticker_key)

        # Fetch current price
        df = _fetch_historical_data(symbol, years=1)
        if df is None or len(df) == 0:
            return jsonify({"error": "No data available"}), 404

        S = float(df["Close"].iloc[-1])
        r = _get_risk_free_rate()

        # Compute historical volatility for default sigma
        log_returns = np.log(df["Close"] / df["Close"].shift(1)).dropna()
        hist_vol = float(log_returns.std() * np.sqrt(252))
        sigma = float(data.get("volatility", hist_vol * 100)) / 100.0

        strategy_type = data["strategy_type"]
        front_dte = int(data.get("front_dte", 30))
        back_dte = int(data["back_dte"]) if data.get("back_dte") else None
        delta_target = float(data.get("delta_target", 0.16))
        strike_override = float(data["strike"]) if data.get("strike") else None

        result = build_strategy_legs(
            strategy_type, S, r, sigma, front_dte, back_dte,
            delta_target, strike_override
        )

        result["underlying_price"] = round(S, 2)
        result["historical_volatility"] = round(hist_vol * 100, 2)
        result["risk_free_rate"] = round(r * 100, 2)
        result["ticker_key"] = ticker_key
        result["section_1256"] = tickers_store.get(ticker_key, {}).get("section_1256", False)

        if result["section_1256"]:
            result["tax_treatment"] = "Section 1256: 60% long-term / 40% short-term capital gains"
        else:
            result["tax_treatment"] = "Standard: Short-term capital gains (< 1 year)"

        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400


# ── API: Strategy Recommendations ─────────────────────────────────────────────

@app.route("/api/strategy/recommend/<ticker_key>", methods=["GET"])
def get_recommendations(ticker_key):
    """Auto-recommend strategies based on technical analysis."""
    symbol = _get_symbol(ticker_key)
    try:
        df = _fetch_historical_data(symbol, years=2)
        if df is None or len(df) < 50:
            return jsonify({"error": "Not enough data"}), 404

        ta_result = run_technical_analysis(df)
        composite = ta_result["composite_signal"]

        # Estimate IV percentile (using historical vol)
        log_returns = np.log(df["Close"] / df["Close"].shift(1)).dropna()
        current_vol = float(log_returns.tail(20).std() * np.sqrt(252))
        rolling_vol = log_returns.rolling(20).std() * np.sqrt(252)
        iv_percentile = float((rolling_vol < current_vol).mean() * 100)

        recommendations = recommend_strategies(
            composite, iv_percentile, float(df["Close"].iloc[-1])
        )

        return jsonify({
            "ticker_key": ticker_key,
            "symbol": symbol,
            "current_price": round(float(df["Close"].iloc[-1]), 2),
            "composite_signal": composite,
            "iv_percentile": round(iv_percentile, 1),
            "historical_vol": round(current_vol * 100, 2),
            "recommendations": recommendations,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── API: Backtest ─────────────────────────────────────────────────────────────

@app.route("/api/backtest", methods=["POST"])
def run_backtest_endpoint():
    """Run a historical backtest."""
    data = request.json
    try:
        ticker_key = data["ticker_key"]
        symbol = _get_symbol(ticker_key)
        years = int(data.get("years", BACKTEST_DEFAULT_YEARS))

        df = _fetch_historical_data(symbol, years=years)
        if df is None or len(df) < 60:
            return jsonify({"error": "Not enough historical data"}), 404

        r = _get_risk_free_rate()
        strategy_type = data["strategy_type"]
        delta_target = float(data.get("delta_target", 0.16))
        front_dte = int(data.get("front_dte", 30))
        back_dte = int(data["back_dte"]) if data.get("back_dte") else None
        entry_interval = int(data.get("entry_interval", 5))
        profit_target = float(data.get("profit_target_pct", 50))
        stop_loss = float(data.get("stop_loss_pct", 200))

        result = run_backtest(
            df, strategy_type, r, delta_target, front_dte, back_dte,
            entry_interval, profit_target, stop_loss
        )

        result["ticker_key"] = ticker_key
        result["symbol"] = symbol
        result["years"] = years
        result["years_options"] = BACKTEST_YEARS_OPTIONS
        result["strategy_type"] = strategy_type

        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── API: Distribution Analysis ────────────────────────────────────────────────

@app.route("/api/distribution/<ticker_key>", methods=["GET"])
def get_distribution(ticker_key):
    """Get price change distribution analysis."""
    symbol = _get_symbol(ticker_key)
    years = int(request.args.get("years", 2))
    try:
        df = _fetch_historical_data(symbol, years=years)
        if df is None or len(df) < 30:
            return jsonify({"error": "Not enough data"}), 404

        result = analyze_distribution(df)
        result["ticker_key"] = ticker_key
        result["symbol"] = symbol
        result["name"] = tickers_store.get(ticker_key, {}).get("name", symbol)
        result["years"] = years
        result["years_options"] = BACKTEST_YEARS_OPTIONS

        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── API: AI Forecast ──────────────────────────────────────────────────────────

@app.route("/api/forecast/<ticker_key>", methods=["GET"])
def get_ai_forecast(ticker_key):
    """Run ML-based 30-day forecast."""
    symbol = _get_symbol(ticker_key)
    try:
        df = _fetch_historical_data(symbol, years=2)
        if df is None or len(df) < 60:
            return jsonify({"error": "Not enough data"}), 404

        # Augmented DF for ML features
        df = get_augmented_df(df)
        
        # 1. Multi-horizon predictions
        forecaster = MLForecaster(df)
        forecasts = forecaster.predict_multi_horizon(periods=[7, 14, 30])
        
        # 2. Extract Indicator Details for UI Grid
        ta_results = run_technical_analysis(df)
        
        # 3. Best Strategy Suggestion Logic
        # Analyze alignment of forecasts
        directions = [f['direction'] for f in forecasts.values()]
        alignment = "Mixed"
        if all(d == "UP" for d in directions): alignment = "Strong Bullish"
        elif all(d == "DOWN" for d in directions): alignment = "Strong Bearish"
        
        result = {
            "ticker_key": ticker_key,
            "symbol": symbol,
            "current_price": ta_results["current_price"],
            "forecasts": forecasts,
            "alignment": alignment,
            "technical_indicators": {
                "rsi": ta_results["rsi"],
                "macd": ta_results["macd"],
                "bollinger": ta_results["bollinger"],
                "stoch": ta_results["stoch"],
                "adx": ta_results["adx"],
                "vwap": ta_results["vwap"],
                "obv": ta_results["obv"],
                "levels": ta_results["levels"],
                "composite": ta_results["composite_signal"]
            }
        }
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── API: Risk Management (Hybrid VaR) ─────────────────────────────────────────

@app.route("/api/risk/<ticker_key>", methods=["GET"])
def get_risk_analysis(ticker_key):
    """Get Hybrid VaR and risk backtest."""
    symbol = _get_symbol(ticker_key)
    try:
        df = _fetch_historical_data(symbol, years=2)
        if df is None or len(df) < 60:
            return jsonify({"error": "Not enough data"}), 404

        # Augmented DF for risk model features
        df = get_augmented_df(df)
        
        engine = RiskEngine(df)
        var_data = engine.calculate_hybrid_var(confidence=0.95)
        backtest = engine.backtest_risk_model(confidence=0.95)
        
        return jsonify({
            "ticker_key": ticker_key,
            "symbol": symbol,
            "var": var_data,
            "backtest": backtest
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── API: Market Simulation (What-If) ───────────────────────────────────────────

@app.route("/api/simulate/<ticker_key>", methods=["GET"])
def get_simulation(ticker_key):
    """Run what-if scenarios."""
    symbol = _get_symbol(ticker_key)
    try:
        df = _fetch_historical_data(symbol, years=1)
        if df is None or len(df) == 0:
            return jsonify({"error": "No data"}), 404

        current_price = float(df["Close"].iloc[-1])
        # Estimate daily volatility score
        returns = df["Close"].pct_change().dropna()
        vol_score = float(returns.std())
        
        sim = MarketSimulator(symbol, current_price, volatility_score=vol_score)
        scenarios = sim.run_scenarios()
        
        return jsonify({
            "ticker_key": ticker_key,
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "scenarios": scenarios
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── API: Available Strategies ─────────────────────────────────────────────────

@app.route("/api/strategies", methods=["GET"])
def get_strategies():
    """List all available strategy types."""
    return jsonify([
        {"key": k, **v} for k, v in STRATEGIES.items()
    ])


# ── API: Configuration ───────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
def get_config():
    """Return app configuration for frontend."""
    return jsonify({
        "backtest_years_options": BACKTEST_YEARS_OPTIONS,
        "backtest_default_years": BACKTEST_DEFAULT_YEARS,
        "risk_free_rate": round(_get_risk_free_rate() * 100, 2),
    })


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Options Trading Analysis Platform")
    print(f"  Server running at http://{HOST}:{PORT}")
    print("=" * 60)
    app.run(host=HOST, port=PORT, debug=DEBUG)
