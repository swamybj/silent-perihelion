"""
Backtesting Engine.

Runs historical backtests for options strategies by simulating option prices
through the Black-Scholes model using historical underlying prices and volatility.
"""

import numpy as np
import pandas as pd
from greeks_engine import black_scholes_price, calc_all_greeks, find_strike_by_delta
from config import STRATEGY_DEFAULTS


def _compute_historical_vol(prices, window=20):
    """Compute rolling historical volatility (annualized)."""
    log_returns = np.log(prices / prices.shift(1))
    return log_returns.rolling(window=window).std() * np.sqrt(252)


def run_backtest(df, strategy_type, r, delta_target=None, front_dte=30,
                  back_dte=None, entry_interval=5, profit_target_pct=50,
                  stop_loss_pct=200):
    """
    Run a historical backtest for an options strategy.

    Parameters:
        df: DataFrame with OHLCV data (DatetimeIndex, columns: Open, High, Low, Close, Volume)
        strategy_type: Strategy key (e.g., 'iron_condor', 'bull_call_spread')
        r: Risk-free rate
        delta_target: Target delta for OTM legs
        front_dte: DTE for front leg
        back_dte: DTE for back leg (calendar/diagonal only)
        entry_interval: Enter a new trade every N trading days
        profit_target_pct: Close at this % of max profit
        stop_loss_pct: Close at this % of max loss (as % of credit for credit strategies)

    Returns:
        dict with backtest results
    """
    if delta_target is None:
        delta_target = STRATEGY_DEFAULTS["default_delta"]

    prices = df["Close"].copy()
    hist_vol = _compute_historical_vol(prices, window=20)

    # Skip initial NaN rows — convert Timestamp to positional index
    first_valid = hist_vol.first_valid_index()
    if first_valid is not None:
        first_valid_pos = df.index.get_loc(first_valid)
        if isinstance(first_valid_pos, slice):
            first_valid_pos = first_valid_pos.start
        start_pos = max(30, int(first_valid_pos))
    else:
        start_pos = 30

    trades = []
    equity_curve = [0.0]
    equity_dates = [str(df.index[start_pos].date()) if hasattr(df.index[start_pos], 'date') else str(df.index[start_pos])]
    cumulative_pnl = 0.0

    entry_idx = start_pos

    while entry_idx < len(df) - front_dte - 1:
        entry_date = df.index[entry_idx]
        S_entry = float(prices.iloc[entry_idx])
        sigma = float(hist_vol.iloc[entry_idx]) if not pd.isna(hist_vol.iloc[entry_idx]) else 0.20

        if sigma <= 0.01:
            sigma = 0.20

        T_front = front_dte / 365.0
        T_back = (back_dte / 365.0) if back_dte else None

        # ── Build legs at entry ──────────────────────────────────────────
        legs_entry = _build_backtest_legs(
            strategy_type, S_entry, r, sigma, T_front, T_back, delta_target
        )

        if not legs_entry:
            entry_idx += entry_interval
            continue

        # Calculate initial position value
        entry_value = sum(
            leg["premium"] * (1 if leg["action"] == "sell" else -1)
            for leg in legs_entry
        )
        is_credit = entry_value > 0

        # ── Track daily P&L ──────────────────────────────────────────────
        daily_pnl = []
        exit_reason = "expiration"
        exit_day = front_dte
        exit_pnl = 0

        for day in range(1, front_dte + 1):
            if entry_idx + day >= len(df):
                exit_day = day - 1
                exit_reason = "end_of_data"
                break

            S_now = float(prices.iloc[entry_idx + day])
            T_remaining = (front_dte - day) / 365.0
            if T_remaining <= 0:
                T_remaining = 0.001

            # Current sigma (use the day's hist vol if available)
            current_sigma = float(hist_vol.iloc[entry_idx + day]) if not pd.isna(hist_vol.iloc[entry_idx + day]) else sigma

            # Recalculate option values
            current_value = 0
            for leg in legs_entry:
                dte_to_use = T_remaining
                if strategy_type in ("calendar_spread", "diagonal_spread") and "back" in leg.get("role", ""):
                    back_remaining = ((back_dte or front_dte + 30) - day) / 365.0
                    dte_to_use = max(back_remaining, 0.001)

                price_now = black_scholes_price(
                    S_now, leg["strike"], dte_to_use, r, current_sigma, leg["type"]
                )
                mult = 1 if leg["action"] == "sell" else -1
                current_value += price_now * mult

            # P&L is current_value - entry_value for credit,
            # or current_value - entry_value for debit (entry_value is negative)
            day_pnl = current_value - entry_value
            # For credit strategies: profit = entry_value - current_close_cost
            # For debit: profit = current_mark - entry_cost
            if is_credit:
                position_pnl = entry_value - (current_value - entry_value + entry_value)
                # Simplify: position_pnl = entry_credit - cost_to_close
                cost_to_close = 0
                for leg in legs_entry:
                    dte_to_use = T_remaining
                    if strategy_type in ("calendar_spread", "diagonal_spread") and "back" in leg.get("role", ""):
                        back_remaining = ((back_dte or front_dte + 30) - day) / 365.0
                        dte_to_use = max(back_remaining, 0.001)
                    price_now = black_scholes_price(
                        S_now, leg["strike"], dte_to_use, r, current_sigma, leg["type"]
                    )
                    # To close: reverse the position
                    mult = -1 if leg["action"] == "sell" else 1  # buy back sells, sell back buys
                    cost_to_close += price_now * mult
                position_pnl = entry_value + cost_to_close  # entry_value is positive credit
            else:
                # Debit strategy: what are the options worth now minus what we paid
                mark_value = 0
                for leg in legs_entry:
                    dte_to_use = T_remaining
                    if strategy_type in ("calendar_spread", "diagonal_spread") and "back" in leg.get("role", ""):
                        back_remaining = ((back_dte or front_dte + 30) - day) / 365.0
                        dte_to_use = max(back_remaining, 0.001)
                    price_now = black_scholes_price(
                        S_now, leg["strike"], dte_to_use, r, current_sigma, leg["type"]
                    )
                    mult = 1 if leg["action"] == "buy" else -1
                    mark_value += price_now * mult
                position_pnl = mark_value + entry_value  # entry_value is negative debit

            daily_pnl.append(round(float(position_pnl), 2))

            # Check exit conditions
            if is_credit:
                max_profit = entry_value
                if position_pnl >= max_profit * (profit_target_pct / 100.0):
                    exit_reason = "profit_target"
                    exit_day = day
                    exit_pnl = position_pnl
                    break
                if position_pnl <= -abs(max_profit) * (stop_loss_pct / 100.0):
                    exit_reason = "stop_loss"
                    exit_day = day
                    exit_pnl = position_pnl
                    break
            else:
                debit_paid = abs(entry_value)
                if position_pnl >= debit_paid * 0.5:  # 50% return
                    exit_reason = "profit_target"
                    exit_day = day
                    exit_pnl = position_pnl
                    break
                if position_pnl <= -debit_paid * 0.5:  # 50% loss
                    exit_reason = "stop_loss"
                    exit_day = day
                    exit_pnl = position_pnl
                    break

        if not daily_pnl:
            entry_idx += entry_interval
            continue

        if exit_reason == "expiration":
            exit_pnl = daily_pnl[-1]

        exit_date_idx = min(entry_idx + exit_day, len(df) - 1)
        exit_date = df.index[exit_date_idx]

        cumulative_pnl += exit_pnl

        trades.append({
            "entry_date": str(entry_date.date()) if hasattr(entry_date, 'date') else str(entry_date),
            "exit_date": str(exit_date.date()) if hasattr(exit_date, 'date') else str(exit_date),
            "entry_price": S_entry,
            "exit_price": float(prices.iloc[exit_date_idx]),
            "entry_value": round(entry_value, 2),
            "pnl": round(exit_pnl, 2),
            "exit_reason": exit_reason,
            "holding_days": exit_day,
            "daily_pnl": daily_pnl,
        })

        equity_curve.append(round(cumulative_pnl, 2))
        equity_dates.append(str(exit_date.date()) if hasattr(exit_date, 'date') else str(exit_date))

        entry_idx += max(exit_day, entry_interval)

    # ── Compute summary statistics ────────────────────────────────────────
    if not trades:
        return {
            "total_trades": 0,
            "message": "No trades generated in the backtest period.",
        }

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    # Drawdown calculation
    peak = 0
    max_drawdown = 0
    for val in equity_curve:
        peak = max(peak, val)
        drawdown = peak - val
        max_drawdown = max(max_drawdown, drawdown)

    return {
        "total_trades": len(trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "total_pnl": round(sum(pnls), 2),
        "average_pnl": round(np.mean(pnls), 2),
        "median_pnl": round(float(np.median(pnls)), 2),
        "best_trade": round(max(pnls), 2),
        "worst_trade": round(min(pnls), 2),
        "max_drawdown": round(max_drawdown, 2),
        "avg_holding_days": round(np.mean([t["holding_days"] for t in trades]), 1),
        "profit_target_exits": sum(1 for t in trades if t["exit_reason"] == "profit_target"),
        "stop_loss_exits": sum(1 for t in trades if t["exit_reason"] == "stop_loss"),
        "expiration_exits": sum(1 for t in trades if t["exit_reason"] == "expiration"),
        "equity_curve": equity_curve,
        "equity_dates": equity_dates,
        "trades": trades,
        "pnl_distribution": {
            "values": pnls,
            "mean": round(np.mean(pnls), 2),
            "std": round(float(np.std(pnls)), 2),
        },
    }


def _build_backtest_legs(strategy_type, S, r, sigma, T_front, T_back, delta_target):
    """Build simplified legs for backtesting (no full Greeks needed, just prices and strikes)."""
    legs = []

    if strategy_type == "long_call":
        K = find_strike_by_delta(S, T_front, r, sigma, delta_target, "call") or round(S)
        premium = black_scholes_price(S, K, T_front, r, sigma, "call")
        legs.append({"type": "call", "action": "buy", "strike": K, "premium": premium})

    elif strategy_type == "long_put":
        K = find_strike_by_delta(S, T_front, r, sigma, delta_target, "put") or round(S)
        premium = black_scholes_price(S, K, T_front, r, sigma, "put")
        legs.append({"type": "put", "action": "buy", "strike": K, "premium": premium})

    elif strategy_type == "bull_call_spread":
        K_long = find_strike_by_delta(S, T_front, r, sigma, 0.40, "call") or round(S * 0.98)
        K_short = find_strike_by_delta(S, T_front, r, sigma, delta_target, "call") or round(S * 1.03)
        if K_short <= K_long:
            K_short = K_long + round(S * 0.03)
        legs.append({"type": "call", "action": "buy", "strike": K_long,
                      "premium": black_scholes_price(S, K_long, T_front, r, sigma, "call")})
        legs.append({"type": "call", "action": "sell", "strike": K_short,
                      "premium": black_scholes_price(S, K_short, T_front, r, sigma, "call")})

    elif strategy_type == "bear_put_spread":
        K_long = find_strike_by_delta(S, T_front, r, sigma, 0.40, "put") or round(S * 1.02)
        K_short = find_strike_by_delta(S, T_front, r, sigma, delta_target, "put") or round(S * 0.97)
        if K_short >= K_long:
            K_short = K_long - round(S * 0.03)
        legs.append({"type": "put", "action": "buy", "strike": K_long,
                      "premium": black_scholes_price(S, K_long, T_front, r, sigma, "put")})
        legs.append({"type": "put", "action": "sell", "strike": K_short,
                      "premium": black_scholes_price(S, K_short, T_front, r, sigma, "put")})

    elif strategy_type == "iron_condor":
        K_ps = find_strike_by_delta(S, T_front, r, sigma, delta_target, "put") or round(S * 0.95)
        K_pb = K_ps - round(S * 0.02)
        K_cs = find_strike_by_delta(S, T_front, r, sigma, delta_target, "call") or round(S * 1.05)
        K_cb = K_cs + round(S * 0.02)

        for K, action, opt_type in [
            (K_pb, "buy", "put"), (K_ps, "sell", "put"),
            (K_cs, "sell", "call"), (K_cb, "buy", "call")
        ]:
            premium = black_scholes_price(S, K, T_front, r, sigma, opt_type)
            legs.append({"type": opt_type, "action": action, "strike": K, "premium": premium})

    elif strategy_type == "iron_butterfly":
        K_atm = round(S)
        wing = round(S * 0.03)
        K_pb = K_atm - wing
        K_cb = K_atm + wing
        for K, action, opt_type in [
            (K_pb, "buy", "put"), (K_atm, "sell", "put"),
            (K_atm, "sell", "call"), (K_cb, "buy", "call")
        ]:
            premium = black_scholes_price(S, K, T_front, r, sigma, opt_type)
            legs.append({"type": opt_type, "action": action, "strike": K, "premium": premium})

    elif strategy_type == "straddle":
        K = round(S)
        legs.append({"type": "call", "action": "buy", "strike": K,
                      "premium": black_scholes_price(S, K, T_front, r, sigma, "call")})
        legs.append({"type": "put", "action": "buy", "strike": K,
                      "premium": black_scholes_price(S, K, T_front, r, sigma, "put")})

    elif strategy_type == "strangle":
        K_call = find_strike_by_delta(S, T_front, r, sigma, delta_target, "call") or round(S * 1.03)
        K_put = find_strike_by_delta(S, T_front, r, sigma, delta_target, "put") or round(S * 0.97)
        legs.append({"type": "call", "action": "buy", "strike": K_call,
                      "premium": black_scholes_price(S, K_call, T_front, r, sigma, "call")})
        legs.append({"type": "put", "action": "buy", "strike": K_put,
                      "premium": black_scholes_price(S, K_put, T_front, r, sigma, "put")})

    elif strategy_type == "calendar_spread":
        K = round(S)
        T_b = T_back or (T_front + 30 / 365.0)
        legs.append({"type": "call", "action": "sell", "strike": K, "role": "front",
                      "premium": black_scholes_price(S, K, T_front, r, sigma, "call")})
        legs.append({"type": "call", "action": "buy", "strike": K, "role": "back",
                      "premium": black_scholes_price(S, K, T_b, r, sigma, "call")})

    elif strategy_type == "diagonal_spread":
        K_front = find_strike_by_delta(S, T_front, r, sigma, delta_target, "call") or round(S * 1.02)
        K_back = round(S * 0.99)
        T_b = T_back or (T_front + 30 / 365.0)
        legs.append({"type": "call", "action": "sell", "strike": K_front, "role": "front",
                      "premium": black_scholes_price(S, K_front, T_front, r, sigma, "call")})
        legs.append({"type": "call", "action": "buy", "strike": K_back, "role": "back",
                      "premium": black_scholes_price(S, K_back, T_b, r, sigma, "call")})

    return legs
