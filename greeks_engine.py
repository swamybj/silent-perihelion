"""
Black-Scholes Options Pricing & Greeks Calculator.

Provides functions for:
- European option pricing (calls and puts)
- All first-order Greeks: Delta, Gamma, Theta, Vega, Rho
- Implied Volatility solver (Brent's method)
"""

import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


def _d1(S, K, T, r, sigma):
    """Calculate d1 in the Black-Scholes formula."""
    if T <= 0 or sigma <= 0:
        return 0.0
    return (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))


def _d2(S, K, T, r, sigma):
    """Calculate d2 in the Black-Scholes formula."""
    if T <= 0 or sigma <= 0:
        return 0.0
    return _d1(S, K, T, r, sigma) - sigma * np.sqrt(T)


def black_scholes_price(S, K, T, r, sigma, option_type="call"):
    """
    Calculate European option price using Black-Scholes.

    Parameters:
        S: Current underlying price
        K: Strike price
        T: Time to expiration in years
        r: Risk-free interest rate (annualized)
        sigma: Volatility (annualized)
        option_type: 'call' or 'put'

    Returns:
        Option price (float)
    """
    if T <= 0:
        # At expiration
        if option_type == "call":
            return max(S - K, 0)
        else:
            return max(K - S, 0)

    d1 = _d1(S, K, T, r, sigma)
    d2 = _d2(S, K, T, r, sigma)

    if option_type == "call":
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return float(price)


def calc_delta(S, K, T, r, sigma, option_type="call"):
    """
    Calculate option Delta.
    Call delta: N(d1), range [0, 1]
    Put delta: N(d1) - 1, range [-1, 0]
    """
    if T <= 0:
        if option_type == "call":
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0

    d1 = _d1(S, K, T, r, sigma)
    if option_type == "call":
        return float(norm.cdf(d1))
    else:
        return float(norm.cdf(d1) - 1)


def calc_gamma(S, K, T, r, sigma):
    """
    Calculate option Gamma.
    Same for calls and puts.
    """
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma)
    return float(norm.pdf(d1) / (S * sigma * np.sqrt(T)))


def calc_theta(S, K, T, r, sigma, option_type="call"):
    """
    Calculate option Theta (per day).
    Returns the daily decay value (negative for long options).
    """
    if T <= 0:
        return 0.0

    d1 = _d1(S, K, T, r, sigma)
    d2 = _d2(S, K, T, r, sigma)

    common = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))

    if option_type == "call":
        theta = common - r * K * np.exp(-r * T) * norm.cdf(d2)
    else:
        theta = common + r * K * np.exp(-r * T) * norm.cdf(-d2)

    # Convert to per-day
    return float(theta / 365.0)


def calc_vega(S, K, T, r, sigma):
    """
    Calculate option Vega.
    Same for calls and puts. Returns change per 1% move in volatility.
    """
    if T <= 0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma)
    return float(S * norm.pdf(d1) * np.sqrt(T) / 100.0)


def calc_rho(S, K, T, r, sigma, option_type="call"):
    """
    Calculate option Rho.
    Returns change per 1% move in interest rate.
    """
    if T <= 0:
        return 0.0

    d2 = _d2(S, K, T, r, sigma)

    if option_type == "call":
        return float(K * T * np.exp(-r * T) * norm.cdf(d2) / 100.0)
    else:
        return float(-K * T * np.exp(-r * T) * norm.cdf(-d2) / 100.0)


def calc_all_greeks(S, K, T, r, sigma, option_type="call"):
    """
    Calculate all Greeks and the option price in a single call.

    Returns:
        dict with keys: price, delta, gamma, theta, vega, rho, iv
    """
    price = black_scholes_price(S, K, T, r, sigma, option_type)
    delta = calc_delta(S, K, T, r, sigma, option_type)
    gamma = calc_gamma(S, K, T, r, sigma)
    theta = calc_theta(S, K, T, r, sigma, option_type)
    vega = calc_vega(S, K, T, r, sigma)
    rho = calc_rho(S, K, T, r, sigma, option_type)

    return {
        "price": round(price, 4),
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "rho": round(rho, 4),
        "iv": round(sigma * 100, 2),  # As percentage
    }


def calc_implied_volatility(market_price, S, K, T, r, option_type="call",
                             lower=0.001, upper=5.0, tol=1e-6):
    """
    Solve for Implied Volatility using Brent's method.

    Parameters:
        market_price: Observed market price of the option
        S: Current underlying price
        K: Strike price
        T: Time to expiration in years
        r: Risk-free rate
        option_type: 'call' or 'put'
        lower: Lower bound for IV search
        upper: Upper bound for IV search
        tol: Tolerance for convergence

    Returns:
        Implied volatility (float) or None if no solution found
    """
    if T <= 0 or market_price <= 0:
        return None

    # Check intrinsic value bounds
    if option_type == "call":
        intrinsic = max(S - K * np.exp(-r * T), 0)
    else:
        intrinsic = max(K * np.exp(-r * T) - S, 0)

    if market_price < intrinsic:
        return None

    def objective(sigma):
        return black_scholes_price(S, K, T, r, sigma, option_type) - market_price

    try:
        iv = brentq(objective, lower, upper, xtol=tol)
        return float(iv)
    except (ValueError, RuntimeError):
        return None


def find_strike_by_delta(S, T, r, sigma, target_delta, option_type="call",
                          K_min=None, K_max=None):
    """
    Find the strike price that corresponds to a target delta.

    Parameters:
        S: Current underlying price
        T: Time to expiration
        r: Risk-free rate
        sigma: Volatility
        target_delta: Desired delta (e.g., 0.16 for a 16-delta call)
        option_type: 'call' or 'put'
        K_min: Minimum strike to search
        K_max: Maximum strike to search

    Returns:
        Strike price (float)
    """
    if K_min is None:
        K_min = S * 0.5
    if K_max is None:
        K_max = S * 1.5

    if option_type == "put":
        # Put deltas are negative; target should be negative
        if target_delta > 0:
            target_delta = -target_delta

    def objective(K):
        return calc_delta(S, K, T, r, sigma, option_type) - target_delta

    try:
        strike = brentq(objective, K_min, K_max)
        return float(round(strike, 2))
    except (ValueError, RuntimeError):
        return None


def option_payoff_at_expiry(S_range, K, option_type="call", position="long", premium=0):
    """
    Calculate option payoff at expiration for a range of underlying prices.

    Parameters:
        S_range: Array of underlying prices at expiry
        K: Strike price
        option_type: 'call' or 'put'
        position: 'long' or 'short'
        premium: Premium paid (long) or received (short)

    Returns:
        Array of payoffs
    """
    S_range = np.array(S_range)

    if option_type == "call":
        intrinsic = np.maximum(S_range - K, 0)
    else:
        intrinsic = np.maximum(K - S_range, 0)

    if position == "long":
        return intrinsic - premium
    else:
        return premium - intrinsic


def option_payoff_at_t(S_range, K, T, r, sigma, option_type="call", position="long", premium_paid=0):
    """
    Calculate option theoretical payoff at exactly T days to expiration for a range of underlying prices.
    Used for generating T+0 lines to show current projected moves.

    Parameters:
        S_range: Array of underlying prices
        K: Strike price
        T: Time to expiration in years
        r: Risk-free rate
        sigma: Volatility
        option_type: 'call' or 'put'
        position: 'long' or 'short'
        premium_paid: Original premium paid (long) or received (short)

    Returns:
        Array of payoffs
    """
    S_range = np.array(S_range)
    current_prices = np.zeros(len(S_range))
    
    for i, curr_S in enumerate(S_range):
        current_prices[i] = black_scholes_price(curr_S, K, T, r, sigma, option_type)
        
    if position == "long":
        return current_prices - premium_paid
    else:
        return premium_paid - current_prices
