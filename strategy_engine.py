"""
Strategy Engine.

Recommends options strategies based on technical signals and market conditions.
Supports: Long Call/Put, Vertical Spreads, Iron Condor, Iron Butterfly,
Calendar Spread, Straddle, Strangle, Diagonal Spread.
"""

import numpy as np
from greeks_engine import (
    black_scholes_price, calc_all_greeks, find_strike_by_delta, option_payoff_at_expiry, option_payoff_at_t
)
from config import STRATEGY_DEFAULTS


# ── Strategy Definitions ──────────────────────────────────────────────────────

STRATEGIES = {
    "long_call": {
        "name": "Long Call",
        "legs": 1,
        "direction": "bullish",
        "description": "Buy a call option. Profits from upward price movement.",
        "best_when": "Strong bullish signal, low IV, expecting large upward move",
        "education": {
            "entry_criteria": "Target Delta: 0.30 to 0.50 (OTM to ATM). Enter when IV Rank is Low (<30).",
            "greeks_impact": "Delta: + (Profits as price rises). Theta: - (Loses value daily). Vega: + (Profits if IV expands).",
            "win_probability": "Lower (~30-45% depending on delta), but potential reward is unlimited."
        }
    },
    "long_put": {
        "name": "Long Put",
        "legs": 1,
        "direction": "bearish",
        "description": "Buy a put option. Profits from downward price movement.",
        "best_when": "Strong bearish signal, low IV, expecting large downward move",
        "education": {
            "entry_criteria": "Target Delta: -0.30 to -0.50 (OTM to ATM). Enter when IV Rank is Low (<30).",
            "greeks_impact": "Delta: - (Profits as price falls). Theta: - (Loses value daily). Vega: + (Profits if IV expands).",
            "win_probability": "Lower (~30-45% depending on delta), but potential reward is substantial."
        }
    },
    "bull_call_spread": {
        "name": "Bull Call Spread",
        "legs": 2,
        "direction": "bullish",
        "description": "Buy a call, sell a higher-strike call. Limited risk/reward bullish trade.",
        "best_when": "Moderate bullish signal, moderate IV",
        "education": {
            "entry_criteria": "Buy ATM/ITM Call (Delta ~0.50), Sell OTM Call (Delta ~0.20-0.30). IV Rank: Any, but prefer Low to Medium.",
            "greeks_impact": "Delta: + (Profits as price rises). Theta: Neutral/Slightly Negative. Vega: Neutral/Slightly Positive.",
            "win_probability": "Moderate (~45-55%), with defined maximum loss and maximum profit."
        }
    },
    "bear_put_spread": {
        "name": "Bear Put Spread",
        "legs": 2,
        "direction": "bearish",
        "description": "Buy a put, sell a lower-strike put. Limited risk/reward bearish trade.",
        "best_when": "Moderate bearish signal, moderate IV",
        "education": {
            "entry_criteria": "Buy ATM/ITM Put (Delta ~-0.50), Sell OTM Put (Delta ~-0.20 to -0.30). IV Rank: Any.",
            "greeks_impact": "Delta: - (Profits as price falls). Theta: Neutral/Slightly Negative. Vega: Neutral/Slightly Positive.",
            "win_probability": "Moderate (~45-55%), with defined maximum loss and maximum profit."
        }
    },
    "iron_condor": {
        "name": "Iron Condor",
        "legs": 4,
        "direction": "neutral",
        "description": "Sell OTM put spread + sell OTM call spread. Profits from low volatility.",
        "best_when": "Neutral / range-bound, high IV, expecting price to stay within range",
        "education": {
            "entry_criteria": "Sell Wings at Delta ~0.10 - 0.20. Buy protection further OTM. Enter when IV Rank is High (>70).",
            "greeks_impact": "Delta: Neutral. Theta: + (Profits actively from time decay). Vega: - (Profits when IV contracts/crushes).",
            "win_probability": "High (~65-80%), but maximum loss is usually larger than maximum profit."
        }
    },
    "iron_butterfly": {
        "name": "Iron Butterfly",
        "legs": 4,
        "direction": "neutral",
        "description": "Sell ATM straddle + buy OTM wings. Profits from very low movement.",
        "best_when": "Very neutral outlook, very high IV",
        "education": {
            "entry_criteria": "Sell ATM Straddle (Delta ~0.50). Buy OTM protection at wings. Enter when IV Rank is Very High (>80).",
            "greeks_impact": "Delta: Neutral. Theta: Highly + (Profits heavily from time decay). Vega: Highly - (Needs IV crush).",
            "win_probability": "Moderate (~50%), highest profit at exactly the short strike."
        }
    },
    "straddle": {
        "name": "Long Straddle",
        "legs": 2,
        "direction": "volatile",
        "description": "Buy ATM call + ATM put. Profits from large moves in either direction.",
        "best_when": "Expecting high volatility, pre-earnings, low IV currently",
        "education": {
            "entry_criteria": "Buy ATM Call & Put (Delta ~0.50/-0.50). Enter when IV Rank is Very Low (<20) before a known catalyst.",
            "greeks_impact": "Delta: Neutral. Theta: Highly - (Burns value rapidly every day). Vega: Highly + (Loves IV expansion).",
            "win_probability": "Low (~30%), requires a massive price move to overcome the high debit paid."
        }
    },
    "strangle": {
        "name": "Long Strangle",
        "legs": 2,
        "direction": "volatile",
        "description": "Buy OTM call + OTM put. Cheaper than straddle, needs bigger move.",
        "best_when": "Expecting very high volatility, low IV currently",
        "education": {
            "entry_criteria": "Buy OTM Call & Put (Delta ~0.20 to 0.30). Enter when IV is Low (<20).",
            "greeks_impact": "Delta: Neutral. Theta: - (Loses value daily). Vega: + (Profits heavily if IV surges).",
            "win_probability": "Very Low (~20-25%), requires an explosive move, but costs less than a Straddle."
        }
    },
    "calendar_spread": {
        "name": "Calendar Spread",
        "legs": 2,
        "direction": "neutral",
        "description": "Sell front-month, buy back-month at same strike. Profits from time decay.",
        "best_when": "Neutral outlook, front month IV higher than back month",
        "education": {
            "entry_criteria": "Sell Near-Term (~20 DTE), Buy Long-Term (~50 DTE) at identical strikes. Enter when Implied Volatility is Low.",
            "greeks_impact": "Delta: Neutral. Theta: + (Front month decays faster than back month). Vega: + (Long term option benefits more from IV increase).",
            "win_probability": "Moderate to High, benefits from passing time while underlying stays pinned to the strike."
        }
    },
    "diagonal_spread": {
        "name": "Diagonal Spread",
        "legs": 2,
        "direction": "slightly_directional",
        "description": "Sell front-month, buy back-month at different strikes. Direction + decay.",
        "best_when": "Slight directional bias with time decay benefit",
        "education": {
            "entry_criteria": "Buy ITM/ATM Long-Term Option, Sell OTM Near-Term Option. IV Rank: Low to Medium.",
            "greeks_impact": "Delta: Directional bias (Long). Theta: + (Near-term shorts decay faster). Vega: + (Net long Vega).",
            "win_probability": "Moderate (~50-60%), acts like a covered call but using LEAPS/Long-term options (Poor Man's Covered Call)."
        }
    },
}


def recommend_strategies(composite_signal, iv_percentile=50, current_price=None):
    """
    Recommend strategies based on the composite technical signal and IV level.

    Parameters:
        composite_signal: dict from technical_analysis with 'signal' and 'score'
        iv_percentile: Current IV percentile (0-100). Higher = more expensive options.
        current_price: Current underlying price (for context).

    Returns:
        list of recommended strategy dicts, ordered by confidence.
    """
    signal = composite_signal.get("signal", "NEUTRAL")
    score = composite_signal.get("score", 0)
    recommendations = []

    high_iv = iv_percentile > 60
    low_iv = iv_percentile < 40

    if signal in ("STRONG_BULLISH",):
        if low_iv:
            recommendations.append({
                "strategy": "long_call",
                "confidence": "HIGH",
                "reason": "Strong bullish signal with low IV — calls are cheap",
                **STRATEGIES["long_call"],
            })
        recommendations.append({
            "strategy": "bull_call_spread",
            "confidence": "HIGH" if high_iv else "MEDIUM",
            "reason": "Bullish signal. Spread reduces cost in higher IV.",
            **STRATEGIES["bull_call_spread"],
        })

    elif signal == "BULLISH":
        recommendations.append({
            "strategy": "bull_call_spread",
            "confidence": "MEDIUM",
            "reason": "Moderate bullish signal favors defined-risk spread.",
            **STRATEGIES["bull_call_spread"],
        })
        if high_iv:
            recommendations.append({
                "strategy": "diagonal_spread",
                "confidence": "MEDIUM",
                "reason": "Bullish bias + high IV — sell front month premium.",
                **STRATEGIES["diagonal_spread"],
            })

    elif signal in ("STRONG_BEARISH",):
        if low_iv:
            recommendations.append({
                "strategy": "long_put",
                "confidence": "HIGH",
                "reason": "Strong bearish signal with low IV — puts are cheap",
                **STRATEGIES["long_put"],
            })
        recommendations.append({
            "strategy": "bear_put_spread",
            "confidence": "HIGH" if high_iv else "MEDIUM",
            "reason": "Bearish signal. Spread reduces cost in higher IV.",
            **STRATEGIES["bear_put_spread"],
        })

    elif signal == "BEARISH":
        recommendations.append({
            "strategy": "bear_put_spread",
            "confidence": "MEDIUM",
            "reason": "Moderate bearish signal favors defined-risk spread.",
            **STRATEGIES["bear_put_spread"],
        })

    elif signal == "NEUTRAL":
        if high_iv:
            recommendations.append({
                "strategy": "iron_condor",
                "confidence": "HIGH",
                "reason": "Neutral signal + high IV — sell premium with iron condor.",
                **STRATEGIES["iron_condor"],
            })
            recommendations.append({
                "strategy": "iron_butterfly",
                "confidence": "MEDIUM",
                "reason": "Very neutral — max premium at ATM strikes.",
                **STRATEGIES["iron_butterfly"],
            })
        else:
            recommendations.append({
                "strategy": "iron_condor",
                "confidence": "MEDIUM",
                "reason": "Neutral signal — range-bound strategy.",
                **STRATEGIES["iron_condor"],
            })
            recommendations.append({
                "strategy": "calendar_spread",
                "confidence": "MEDIUM",
                "reason": "Neutral signal — benefit from time decay differential.",
                **STRATEGIES["calendar_spread"],
            })

    # Always add straddle/strangle as an option if IV is very low
    if low_iv:
        recommendations.append({
            "strategy": "straddle",
            "confidence": "LOW",
            "reason": "Low IV — options are cheap, potential vol expansion play.",
            **STRATEGIES["straddle"],
        })

    return recommendations


def build_strategy_legs(strategy_type, S, r, sigma, front_dte, back_dte=None,
                         delta_target=None, strike_override=None):
    """
    Build the option legs for a given strategy.

    Parameters:
        strategy_type: Key from STRATEGIES dict
        S: Current underlying price
        r: Risk-free rate
        sigma: Implied volatility
        front_dte: Front leg DTE (days to expiration)
        back_dte: Back leg DTE (for calendar/diagonal)
        delta_target: Target delta for OTM legs (e.g., 0.16)
        strike_override: Manual strike price override

    Returns:
        dict with legs, max_profit, max_loss, breakeven points, greeks
    """
    if delta_target is None:
        delta_target = STRATEGY_DEFAULTS["default_delta"]

    T_front = front_dte / 365.0
    T_back = (back_dte / 365.0) if back_dte else T_front

    legs = []
    net_premium = 0

    if strategy_type == "long_call":
        K = strike_override or find_strike_by_delta(S, T_front, r, sigma, delta_target, "call") or round(S)
        greeks = calc_all_greeks(S, K, T_front, r, sigma, "call")
        premium = greeks["price"]
        legs.append({
            "type": "call", "action": "buy", "strike": K, "dte": front_dte,
            "premium": premium, "greeks": greeks
        })
        net_premium = -premium

    elif strategy_type == "long_put":
        K = strike_override or find_strike_by_delta(S, T_front, r, sigma, delta_target, "put") or round(S)
        greeks = calc_all_greeks(S, K, T_front, r, sigma, "put")
        premium = greeks["price"]
        legs.append({
            "type": "put", "action": "buy", "strike": K, "dte": front_dte,
            "premium": premium, "greeks": greeks
        })
        net_premium = -premium

    elif strategy_type == "bull_call_spread":
        K_long = strike_override or find_strike_by_delta(S, T_front, r, sigma, 0.40, "call") or round(S * 0.98)
        K_short = find_strike_by_delta(S, T_front, r, sigma, delta_target, "call") or round(S * 1.03)
        if K_short <= K_long:
            K_short = K_long + 5

        g_long = calc_all_greeks(S, K_long, T_front, r, sigma, "call")
        g_short = calc_all_greeks(S, K_short, T_front, r, sigma, "call")

        legs.append({"type": "call", "action": "buy", "strike": K_long, "dte": front_dte,
                      "premium": g_long["price"], "greeks": g_long})
        legs.append({"type": "call", "action": "sell", "strike": K_short, "dte": front_dte,
                      "premium": g_short["price"], "greeks": g_short})
        net_premium = g_short["price"] - g_long["price"]

    elif strategy_type == "bear_put_spread":
        K_long = strike_override or find_strike_by_delta(S, T_front, r, sigma, 0.40, "put") or round(S * 1.02)
        K_short = find_strike_by_delta(S, T_front, r, sigma, delta_target, "put") or round(S * 0.97)
        if K_short >= K_long:
            K_short = K_long - 5

        g_long = calc_all_greeks(S, K_long, T_front, r, sigma, "put")
        g_short = calc_all_greeks(S, K_short, T_front, r, sigma, "put")

        legs.append({"type": "put", "action": "buy", "strike": K_long, "dte": front_dte,
                      "premium": g_long["price"], "greeks": g_long})
        legs.append({"type": "put", "action": "sell", "strike": K_short, "dte": front_dte,
                      "premium": g_short["price"], "greeks": g_short})
        net_premium = g_short["price"] - g_long["price"]

    elif strategy_type == "iron_condor":
        # Sell OTM put spread + sell OTM call spread
        K_put_sell = find_strike_by_delta(S, T_front, r, sigma, delta_target, "put") or round(S * 0.95)
        K_put_buy = K_put_sell - round(S * 0.02)
        K_call_sell = find_strike_by_delta(S, T_front, r, sigma, delta_target, "call") or round(S * 1.05)
        K_call_buy = K_call_sell + round(S * 0.02)

        for K, action, opt_type in [
            (K_put_buy, "buy", "put"), (K_put_sell, "sell", "put"),
            (K_call_sell, "sell", "call"), (K_call_buy, "buy", "call")
        ]:
            g = calc_all_greeks(S, K, T_front, r, sigma, opt_type)
            multiplier = 1 if action == "sell" else -1
            net_premium += multiplier * g["price"]
            legs.append({"type": opt_type, "action": action, "strike": K,
                          "dte": front_dte, "premium": g["price"], "greeks": g})

    elif strategy_type == "iron_butterfly":
        K_atm = round(S)
        wing_width = round(S * 0.03)
        K_put_buy = K_atm - wing_width
        K_call_buy = K_atm + wing_width

        for K, action, opt_type in [
            (K_put_buy, "buy", "put"), (K_atm, "sell", "put"),
            (K_atm, "sell", "call"), (K_call_buy, "buy", "call")
        ]:
            g = calc_all_greeks(S, K, T_front, r, sigma, opt_type)
            multiplier = 1 if action == "sell" else -1
            net_premium += multiplier * g["price"]
            legs.append({"type": opt_type, "action": action, "strike": K,
                          "dte": front_dte, "premium": g["price"], "greeks": g})

    elif strategy_type == "straddle":
        K = strike_override or round(S)
        g_call = calc_all_greeks(S, K, T_front, r, sigma, "call")
        g_put = calc_all_greeks(S, K, T_front, r, sigma, "put")
        legs.append({"type": "call", "action": "buy", "strike": K, "dte": front_dte,
                      "premium": g_call["price"], "greeks": g_call})
        legs.append({"type": "put", "action": "buy", "strike": K, "dte": front_dte,
                      "premium": g_put["price"], "greeks": g_put})
        net_premium = -(g_call["price"] + g_put["price"])

    elif strategy_type == "strangle":
        K_call = find_strike_by_delta(S, T_front, r, sigma, delta_target, "call") or round(S * 1.03)
        K_put = find_strike_by_delta(S, T_front, r, sigma, delta_target, "put") or round(S * 0.97)
        g_call = calc_all_greeks(S, K_call, T_front, r, sigma, "call")
        g_put = calc_all_greeks(S, K_put, T_front, r, sigma, "put")
        legs.append({"type": "call", "action": "buy", "strike": K_call, "dte": front_dte,
                      "premium": g_call["price"], "greeks": g_call})
        legs.append({"type": "put", "action": "buy", "strike": K_put, "dte": front_dte,
                      "premium": g_put["price"], "greeks": g_put})
        net_premium = -(g_call["price"] + g_put["price"])

    elif strategy_type == "calendar_spread":
        K = strike_override or round(S)
        g_front = calc_all_greeks(S, K, T_front, r, sigma, "call")
        g_back = calc_all_greeks(S, K, T_back, r, sigma, "call")
        legs.append({"type": "call", "action": "sell", "strike": K, "dte": front_dte,
                      "premium": g_front["price"], "greeks": g_front})
        legs.append({"type": "call", "action": "buy", "strike": K, "dte": back_dte or front_dte + 30,
                      "premium": g_back["price"], "greeks": g_back})
        net_premium = g_front["price"] - g_back["price"]

    elif strategy_type == "diagonal_spread":
        K_front = find_strike_by_delta(S, T_front, r, sigma, delta_target, "call") or round(S * 1.02)
        K_back = strike_override or round(S * 0.99)
        g_front = calc_all_greeks(S, K_front, T_front, r, sigma, "call")
        g_back = calc_all_greeks(S, K_back, T_back, r, sigma, "call")
        legs.append({"type": "call", "action": "sell", "strike": K_front, "dte": front_dte,
                      "premium": g_front["price"], "greeks": g_front})
        legs.append({"type": "call", "action": "buy", "strike": K_back, "dte": back_dte or front_dte + 30,
                      "premium": g_back["price"], "greeks": g_back})
        net_premium = g_front["price"] - g_back["price"]

    # ── Compute aggregate Greeks ──────────────────────────────────────────
    agg_greeks = {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}
    for leg in legs:
        mult = 1 if leg["action"] == "buy" else -1
        agg_greeks["delta"] += mult * leg["greeks"]["delta"]
        agg_greeks["gamma"] += mult * leg["greeks"]["gamma"]
        agg_greeks["theta"] += mult * leg["greeks"]["theta"]
        agg_greeks["vega"] += mult * leg["greeks"]["vega"]

    for k in agg_greeks:
        agg_greeks[k] = round(agg_greeks[k], 4)

    # ── Compute payoff diagram ────────────────────────────────────────────
    price_range = np.linspace(S * 0.85, S * 1.15, 200)
    total_payoff = np.zeros(len(price_range))
    total_payoff_t0 = np.zeros(len(price_range))

    for leg in legs:
        position = "long" if leg["action"] == "buy" else "short"
        # At expiration payoff
        payoff = option_payoff_at_expiry(
            price_range, leg["strike"], leg["type"], position, leg["premium"]
        )
        total_payoff += payoff
        
        # Today (T+0) payoff evaluation
        try:
            # Re-evaluate BS for all prices at current DTE.
            from greeks_engine import option_payoff_at_t
            t0_payoff = option_payoff_at_t(
                price_range, leg["strike"], leg["dte"] / 365.0, r, sigma, 
                leg["type"], position, leg["premium"]
            )
            total_payoff_t0 += t0_payoff
        except Exception:
            pass # fallback if t0 fails


    max_profit = float(np.max(total_payoff))
    max_loss = float(np.min(total_payoff))

    # Find breakeven points (where payoff crosses zero)
    breakevens = []
    for i in range(len(total_payoff) - 1):
        if total_payoff[i] * total_payoff[i + 1] < 0:
            # Linear interpolation
            x = price_range[i] - total_payoff[i] * (price_range[i + 1] - price_range[i]) / (total_payoff[i + 1] - total_payoff[i])
            breakevens.append(round(float(x), 2))

    # ── Holding period & exit strategy ────────────────────────────────────
    if net_premium > 0:
        # Credit strategy
        exit_strategy = {
            "profit_target": f"Close at {STRATEGY_DEFAULTS['profit_target_pct']}% of max profit (${round(net_premium * STRATEGY_DEFAULTS['profit_target_pct'] / 100, 2)})",
            "stop_loss": f"Close if loss reaches {STRATEGY_DEFAULTS['stop_loss_pct']}% of credit received (${round(net_premium * STRATEGY_DEFAULTS['stop_loss_pct'] / 100, 2)})",
            "time_exit": f"Close at 50% of DTE remaining ({front_dte // 2} days)",
            "holding_period": f"{front_dte // 2} to {front_dte} days",
        }
    else:
        # Debit strategy
        debit_paid = abs(net_premium)
        exit_strategy = {
            "profit_target": f"Close at 50-100% gain on debit (${round(debit_paid * 0.5, 2)} - ${round(debit_paid, 2)} profit)",
            "stop_loss": f"Close if loss reaches 50% of debit paid (${round(debit_paid * 0.5, 2)} loss)",
            "time_exit": f"Close with at least {front_dte // 3} DTE remaining to avoid theta decay",
            "holding_period": f"{front_dte // 4} to {front_dte * 2 // 3} days",
        }

    return {
        "strategy_type": strategy_type,
        "strategy_info": STRATEGIES.get(strategy_type, {}),
        "legs": legs,
        "net_premium": round(net_premium, 4),
        "is_credit": net_premium > 0,
        "max_profit": round(max_profit, 2),
        "max_loss": round(max_loss, 2),
        "breakevens": breakevens,
        "aggregate_greeks": agg_greeks,
        "exit_strategy": exit_strategy,
        "payoff_diagram": {
            "prices": [round(float(p), 2) for p in price_range],
            "payoffs": [round(float(p), 2) for p in total_payoff],
            "payoffs_t0": [round(float(p), 2) for p in total_payoff_t0]
        },
    }
