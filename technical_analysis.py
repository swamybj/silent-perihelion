"""
Technical Analysis Module.

Computes key indicators using pandas-ta:
- ATR (Average True Range)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- SMA (Simple Moving Averages: 20, 50, 200)
- Bollinger Bands
- Fibonacci Retracement Levels
- Composite Signal Score
"""

import pandas as pd
import numpy as np

try:
    import pandas_ta as ta_lib
    HAS_PANDAS_TA = True
except ImportError:
    HAS_PANDAS_TA = False

import ta

from config import TA_CONFIG


def _compute_sma(df, period):
    """Compute Simple Moving Average."""
    return df["Close"].rolling(window=period).mean()


def _compute_rsi(df, period=14):
    """Compute RSI manually if pandas_ta is not available."""
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def _compute_atr(df, period=14):
    """Compute ATR manually if pandas_ta is not available."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def _compute_macd(df, fast=12, slow=26, signal=9):
    """Compute MACD manually if pandas_ta is not available."""
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _compute_historical_iv(df, window):
    """Compute rolling historical (realized) volatility, annualized, as IV proxy."""
    log_returns = np.log(df["Close"] / df["Close"].shift(1))
    return log_returns.rolling(window=window).std() * np.sqrt(252) * 100  # As percentage


def _compute_bollinger(df, period=20, std_dev=2):
    """Compute Bollinger Bands."""
    sma = df["Close"].rolling(window=period).mean()
    std = df["Close"].rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return upper, sma, lower


def compute_fibonacci_levels(df, lookback_days=60):
    """
    Compute Fibonacci retracement levels from recent swing high/low.

    Parameters:
        df: DataFrame with OHLCV data
        lookback_days: Number of days to look back for swing high/low

    Returns:
        dict with Fibonacci levels and direction
    """
    recent = df.tail(lookback_days)
    swing_high = recent["High"].max()
    swing_low = recent["Low"].min()
    high_idx = recent["High"].idxmax()
    low_idx = recent["Low"].idxmin()

    # Determine trend direction
    if high_idx > low_idx:
        direction = "uptrend"  # Low came first, then high
        diff = swing_high - swing_low
        levels = {
            "0.0%": round(swing_high, 2),
            "23.6%": round(swing_high - 0.236 * diff, 2),
            "38.2%": round(swing_high - 0.382 * diff, 2),
            "50.0%": round(swing_high - 0.500 * diff, 2),
            "61.8%": round(swing_high - 0.618 * diff, 2),
            "78.6%": round(swing_high - 0.786 * diff, 2),
            "100.0%": round(swing_low, 2),
        }
    else:
        direction = "downtrend"  # High came first, then low
        diff = swing_high - swing_low
        levels = {
            "0.0%": round(swing_low, 2),
            "23.6%": round(swing_low + 0.236 * diff, 2),
            "38.2%": round(swing_low + 0.382 * diff, 2),
            "50.0%": round(swing_low + 0.500 * diff, 2),
            "61.8%": round(swing_low + 0.618 * diff, 2),
            "78.6%": round(swing_low + 0.786 * diff, 2),
            "100.0%": round(swing_high, 2),
        }

    return {
        "swing_high": round(swing_high, 2),
        "swing_low": round(swing_low, 2),
        "direction": direction,
        "levels": levels,
    }


def _compute_stoch(df, k=14, d=3):
    """Compute Stochastic Oscillator."""
    s = ta.momentum.StochasticOscillator(df['High'], df['Low'], df['Close'], window=k, smooth_window=d)
    return s.stoch(), s.stoch_signal()


def _compute_obv(df):
    """Compute On-Balance Volume."""
    return ta.volume.OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()


def _compute_vwap(df, window=14):
    """Compute Volume Weighted Average Price (rolling proxy)."""
    return ta.volume.VolumeWeightedAveragePrice(df['High'], df['Low'], df['Close'], df['Volume'], window=window).volume_weighted_average_price()


def _compute_adx(df, window=14):
    """Compute Average Directional Index."""
    a = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=window)
    return a.adx(), a.adx_pos(), a.adx_neg()


def _compute_ema(df, period):
    """Compute Exponential Moving Average."""
    return ta.trend.EMAIndicator(df['Close'], window=period).ema_indicator()


def _compute_support_resistance(df, window=20):
    """Identify local support and resistance."""
    low_roll = df['Low'].rolling(window=window, center=True).min()
    high_roll = df['High'].rolling(window=window, center=True).max()
    return low_roll.iloc[-window-1:].min(), high_roll.iloc[-window-1:].max()


def get_augmented_df(df):
    """Returns a copy of the DataFrame with all indicator columns added."""
    df = df.copy()
    
    # EMAs
    df['EMA_9'] = _compute_ema(df, 9)
    df['EMA_26'] = _compute_ema(df, 26)
    df['EMA_50'] = _compute_ema(df, 50)
    df['EMA_200'] = _compute_ema(df, 200)
    
    # MACD
    macd, signal, hist = _compute_macd(df)
    df['MACD'] = macd
    df['MACD_Signal'] = signal
    df['MACD_Hist'] = hist
    
    # RSI
    df['RSI'] = _compute_rsi(df)
    
    # Stoch
    k, d = _compute_stoch(df)
    df['Stoch_K'] = k
    df['Stoch_D'] = d
    
    # OBV
    df['OBV'] = _compute_obv(df)
    
    # VWAP
    df['VWAP'] = _compute_vwap(df)
    
    # ADX
    adx, pos, neg = _compute_adx(df)
    df['ADX'] = adx
    df['ADX_Pos'] = pos
    df['ADX_Neg'] = neg
    
    # ATR
    df['ATR'] = _compute_atr(df)
    
    # BB
    upper, mid, lower = _compute_bollinger(df)
    df['BB_High'] = upper
    df['BB_Mid'] = mid
    df['BB_Low'] = lower
    df['BB_Width'] = (upper - lower) / mid
    
    return df




def run_technical_analysis(df):
    """
    Run all technical indicators on a DataFrame.

    Parameters:
        df: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
            Must have a DatetimeIndex.

    Returns:
        dict with all indicator values and a composite signal.
    """
    if df is None or len(df) < 200:
        # Need at least 200 rows for SMA 200
        min_needed = 200
        if df is not None and len(df) < min_needed:
            pass  # We'll compute what we can

    result = {}
    latest = df.iloc[-1]
    current_price = float(latest["Close"])
    result["current_price"] = current_price
    result["date"] = str(df.index[-1].date()) if hasattr(df.index[-1], 'date') else str(df.index[-1])

    # ── SMA ────────────────────────────────────────────────────────────────
    sma_data = {}
    for period in TA_CONFIG["sma_periods"]:
        sma = _compute_sma(df, period)
        val = float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else None
        sma_data[f"sma_{period}"] = val
        if val:
            sma_data[f"sma_{period}_signal"] = "above" if current_price > val else "below"
    result["sma"] = sma_data

    # ── RSI ────────────────────────────────────────────────────────────────
    rsi_period = TA_CONFIG["rsi_period"]
    if HAS_PANDAS_TA:
        rsi_series = ta.rsi(df["Close"], length=rsi_period)
    else:
        rsi_series = _compute_rsi(df, rsi_period)

    rsi_val = float(rsi_series.iloc[-1]) if rsi_series is not None and not pd.isna(rsi_series.iloc[-1]) else None
    rsi_signal = "neutral"
    if rsi_val is not None:
        if rsi_val > 70:
            rsi_signal = "overbought"
        elif rsi_val < 30:
            rsi_signal = "oversold"
    result["rsi"] = {"value": round(rsi_val, 2) if rsi_val else None, "signal": rsi_signal}
    # RSI history for charting
    result["rsi_history"] = [round(float(v), 2) if not pd.isna(v) else None for v in rsi_series.tail(60).tolist()]

    # ── ATR ────────────────────────────────────────────────────────────────
    atr_period = TA_CONFIG["atr_period"]
    if HAS_PANDAS_TA:
        atr_series = ta.atr(df["High"], df["Low"], df["Close"], length=atr_period)
    else:
        atr_series = _compute_atr(df, atr_period)

    atr_val = float(atr_series.iloc[-1]) if atr_series is not None and not pd.isna(atr_series.iloc[-1]) else None
    result["atr"] = {
        "value": round(atr_val, 2) if atr_val else None,
        "pct_of_price": round((atr_val / current_price) * 100, 2) if atr_val else None,
    }

    # ── MACD ───────────────────────────────────────────────────────────────
    fast = TA_CONFIG["macd_fast"]
    slow = TA_CONFIG["macd_slow"]
    sig = TA_CONFIG["macd_signal"]

    macd_line, signal_line, histogram = _compute_macd(df, fast, slow, sig)
    macd_val = float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else None
    signal_val = float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else None
    hist_val = float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else None

    macd_signal = "neutral"
    if macd_val is not None and signal_val is not None:
        if macd_val > signal_val:
            macd_signal = "bullish"
        else:
            macd_signal = "bearish"

    result["macd"] = {
        "macd": round(macd_val, 4) if macd_val else None,
        "signal": round(signal_val, 4) if signal_val else None,
        "histogram": round(hist_val, 4) if hist_val else None,
        "signal_name": macd_signal,
    }
    # MACD history for charting
    result["macd_history"] = {
        "macd": [round(float(v), 4) if not pd.isna(v) else None for v in macd_line.tail(60).tolist()],
        "signal": [round(float(v), 4) if not pd.isna(v) else None for v in signal_line.tail(60).tolist()],
        "histogram": [round(float(v), 4) if not pd.isna(v) else None for v in histogram.tail(60).tolist()],
    }

    # ── Bollinger Bands ────────────────────────────────────────────────────
    bb_upper, bb_mid, bb_lower = _compute_bollinger(
        df, TA_CONFIG["bollinger_period"], TA_CONFIG["bollinger_std"]
    )
    result["bollinger"] = {
        "upper": round(float(bb_upper.iloc[-1]), 2) if not pd.isna(bb_upper.iloc[-1]) else None,
        "middle": round(float(bb_mid.iloc[-1]), 2) if not pd.isna(bb_mid.iloc[-1]) else None,
        "lower": round(float(bb_lower.iloc[-1]), 2) if not pd.isna(bb_lower.iloc[-1]) else None,
        "bandwidth": round(float((bb_upper.iloc[-1] - bb_lower.iloc[-1]) / bb_mid.iloc[-1] * 100), 2)
            if not pd.isna(bb_mid.iloc[-1]) and bb_mid.iloc[-1] != 0 else None,
    }

    # ── Fibonacci Retracement ──────────────────────────────────────────────
    result["fibonacci"] = compute_fibonacci_levels(df, TA_CONFIG["fib_lookback_days"])

    # ── Historical IV (Realized Volatility as proxy) ── 30/60/90 day ──────
    iv_windows = [30, 60, 90]
    iv_current = {}
    iv_history = {}
    chart_len = 120  # Match price_history length
    for w in iv_windows:
        iv_series = _compute_historical_iv(df, window=w)
        latest = float(iv_series.iloc[-1]) if not pd.isna(iv_series.iloc[-1]) else None
        iv_current[f"iv_{w}d"] = round(latest, 2) if latest else None
        iv_history[f"iv_{w}d"] = [
            round(float(v), 2) if not pd.isna(v) else None
            for v in iv_series.tail(chart_len).tolist()
        ]

    # IV percentile: where current 30d IV sits relative to its own 1-year range
    iv_30_full = _compute_historical_iv(df, window=30).dropna()
    if len(iv_30_full) > 20:
        iv_pct = float((iv_30_full < iv_30_full.iloc[-1]).mean() * 100)
    else:
        iv_pct = None

    result["historical_iv"] = {
        "current": iv_current,
        "percentile_30d": round(iv_pct, 1) if iv_pct is not None else None,
        "history": iv_history,
    }

    # ── Price History for Charting (last 120 days) ─────────────────────────
    chart_data = df.tail(120)
    dates = [str(d.date()) if hasattr(d, 'date') else str(d) for d in chart_data.index]
    result["price_history"] = {
        "dates": dates,
        "open": [round(float(v), 2) for v in chart_data["Open"].tolist()],
        "high": [round(float(v), 2) for v in chart_data["High"].tolist()],
        "low": [round(float(v), 2) for v in chart_data["Low"].tolist()],
        "close": [round(float(v), 2) for v in chart_data["Close"].tolist()],
        "volume": [int(v) if not pd.isna(v) else 0 for v in chart_data["Volume"].tolist()],
    }
    # ── SMA Overlay ──
    for period in TA_CONFIG["sma_periods"]:
        sma = _compute_sma(df, period)
        result["price_history"][f"sma_{period}"] = [
            round(float(v), 2) if not pd.isna(v) else None
            for v in sma.tail(120).tolist()
        ]

    # ── ADVANCED INDICATORS ──
    # EMAs
    ema_9 = _compute_ema(df, 9)
    ema_26 = _compute_ema(df, 26)
    ema_50 = _compute_ema(df, 50)
    ema_200 = _compute_ema(df, 200)
    
    # Stochastics
    stoch_k, stoch_d = _compute_stoch(df)
    result["stoch"] = {
        "k": round(float(stoch_k.iloc[-1]), 2) if not pd.isna(stoch_k.iloc[-1]) else None,
        "d": round(float(stoch_d.iloc[-1]), 2) if not pd.isna(stoch_d.iloc[-1]) else None,
    }
    
    # OBV
    obv = _compute_obv(df)
    result["obv"] = {"value": float(obv.iloc[-1]) if not pd.isna(obv.iloc[-1]) else None}
    
    # VWAP
    vwap = _compute_vwap(df)
    result["vwap"] = {"value": round(float(vwap.iloc[-1]), 2) if not pd.isna(vwap.iloc[-1]) else None}
    
    # ADX
    adx, adx_pos, adx_neg = _compute_adx(df)
    result["adx"] = {
        "adx": round(float(adx.iloc[-1]), 2) if not pd.isna(adx.iloc[-1]) else None,
        "pos": round(float(adx_pos.iloc[-1]), 2) if not pd.isna(adx_pos.iloc[-1]) else None,
        "neg": round(float(adx_neg.iloc[-1]), 2) if not pd.isna(adx_neg.iloc[-1]) else None,
    }
    
    # Support / Resistance
    supp, resis = _compute_support_resistance(df)
    result["levels"] = {"support": round(float(supp), 2), "resistance": round(float(resis), 2)}

    # ── COMPOSITE SCORING (AZIMUTHAL-STELLAR STYLE) ──
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    scores = {}
    weights = {'MACD': 0.15, 'RSI': 0.10, 'Bollinger': 0.10, 'Stochastic': 0.10, 'Trend': 0.15, 'Cross': 0.10, 'OBV': 0.05, 'VWAP': 0.05, 'ADX': 0.10}
    
    # 1. MACD
    if result["macd"]["macd"] > result["macd"]["signal"]: scores['MACD'] = 1
    else: scores['MACD'] = -1
    
    # 2. RSI
    if rsi_val:
        if rsi_val < 30: scores['RSI'] = 1
        elif rsi_val > 70: scores['RSI'] = -1
        else: scores['RSI'] = 0
        
    # 3. Bollinger
    if result["bollinger"]["lower"] and current_price < result["bollinger"]["lower"]: scores['Bollinger'] = 1
    elif result["bollinger"]["upper"] and current_price > result["bollinger"]["upper"]: scores['Bollinger'] = -1
    else: scores['Bollinger'] = 0
    
    # 4. Stochastic
    if result["stoch"]["k"]:
        if result["stoch"]["k"] < 20: scores['Stochastic'] = 1
        elif result["stoch"]["k"] > 80: scores['Stochastic'] = -1
        else: scores['Stochastic'] = 0
        
    # 5. Trend (EMA 200)
    if current_price > ema_200.iloc[-1]: scores['Trend'] = 0.5
    else: scores['Trend'] = -0.5
    
    # 6. EMA Cross
    if ema_50.iloc[-1] > ema_200.iloc[-1]: scores['Cross'] = 1
    else: scores['Cross'] = -1
    
    # 7. OBV
    if obv.iloc[-1] > obv.iloc[-2]: scores['OBV'] = 0.5
    else: scores['OBV'] = -0.5
    
    # 8. VWAP
    if result["vwap"]["value"] and current_price > result["vwap"]["value"]: scores['VWAP'] = 1
    else: scores['VWAP'] = -1
    
    # 9. ADX
    if result["adx"]["adx"] and result["adx"]["adx"] > 25:
        if result["adx"]["pos"] > result["adx"]["neg"]: scores['ADX'] = 1
        else: scores['ADX'] = -1
    else: scores['ADX'] = 0

    # Total Score
    total_score = sum(scores.get(k, 0) * weights[k] for k in weights)
    
    # Refined Recommendation
    is_above_emas = current_price > ema_50.iloc[-1] and current_price > ema_200.iloc[-1]
    is_below_emas = current_price < ema_50.iloc[-1] and current_price < ema_200.iloc[-1]
    
    if is_above_emas and result["macd"]["signal_name"] == "bullish" and 50 < rsi_val < 75 and result["adx"]["adx"] > 20:
        overall = "STRONG BUY"
    elif is_below_emas and result["macd"]["signal_name"] == "bearish" and 25 < rsi_val < 50 and result["adx"]["adx"] > 20:
        overall = "STRONG SELL"
    elif current_price > ema_200.iloc[-1] and (current_price < ema_50.iloc[-1] or rsi_val < 45):
        overall = "BUY DIP"
    elif total_score > 0.25:
        overall = "BUY"
    elif total_score < -0.25:
        overall = "SELL"
    else:
        overall = "NEUTRAL"

    result["composite_signal"] = {
        "score": round(total_score, 2),
        "signal": overall,
        "detail_scores": scores
    }

    return result
