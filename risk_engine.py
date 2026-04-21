"""
Risk Management Engine.

Calculates Hybrid VaR and performs risk backtesting.
"""

import pandas as pd
import numpy as np
from scipy.stats import norm

class RiskEngine:
    def __init__(self, df):
        self.df = df.copy()
        
    def calculate_hybrid_var(self, period_days=21, confidence=0.95):
        """
        Calculates Hybrid Parametric VaR adjusted for current market indicators.
        """
        if self.df is None or len(self.df) < period_days:
            return None

        # 1. Base Parametric VaR
        recent = self.df.tail(period_days)
        returns = recent['Close'].pct_change().dropna()
        
        if returns.empty:
            return 0.0
            
        mean = returns.mean()
        std_dev = returns.std()
        z_score = norm.ppf(1 - confidence) # -1.645 for 95%
        
        base_var_pct = mean + (z_score * std_dev)
        
        # 2. Risk Multiplier derived from technical state
        latest = self.df.iloc[-1]
        multiplier = 1.0
        
        # Adjust for Overbought/Oversold (Mean reversion risk or volatility expansion)
        if 'RSI' in latest:
            if latest['RSI'] > 70: multiplier += 0.2
            elif latest['RSI'] < 30: multiplier += 0.1
            
        # Adjust for Trend (Downtrend increases downside tail risk)
        if 'EMA_200' in latest:
            if latest['Close'] < latest['EMA_200']: multiplier += 0.2
            
        # Adjust for Volatility (Bollinger Band Width)
        if 'BB_Width' in latest:
            # Compare current width to 20-day avg width
            avg_width = self.df['BB_Width'].rolling(20).mean().iloc[-1] if len(self.df) >= 20 else latest['BB_Width']
            if latest['BB_Width'] > avg_width * 1.2:
                multiplier += 0.15
                
        # Adjust for VWAP
        if 'VWAP' in latest and latest['Close'] < latest['VWAP']:
            multiplier += 0.1
            
        hybrid_var_pct = base_var_pct * multiplier
        
        return {
            "base_var_pct": round(float(base_var_pct) * 100, 2),
            "hybrid_var_pct": round(float(hybrid_var_pct) * 100, 2),
            "risk_multiplier": round(multiplier, 2),
            "confidence": confidence,
            "horizon_days": 1
        }

    def backtest_risk_model(self, lookback_days=252, confidence=0.95):
        """
        Backtests Standard vs Hybrid VaR models.
        """
        if len(self.df) < lookback_days + 30:
            return {"error": "Not enough data for backtest."}
            
        data = self.df.copy()
        data['Returns'] = data['Close'].pct_change()
        data['Next_Return'] = data['Returns'].shift(-1)
        
        # Simple Parametric VaR (Rolling 20-day)
        data['Roll_Mean'] = data['Returns'].rolling(20).mean()
        data['Roll_Std'] = data['Returns'].rolling(20).std()
        z_score = norm.ppf(1 - confidence)
        data['Base_VaR'] = data['Roll_Mean'] + (z_score * data['Roll_Std'])
        
        # Hybrid Components (Vectorized)
        rsi_mult = np.zeros(len(data))
        if 'RSI' in data.columns:
            rsi_mult = np.where(data['RSI'] > 70, 0.2, np.where(data['RSI'] < 30, 0.1, 0.0))
            
        trend_mult = np.zeros(len(data))
        if 'EMA_200' in data.columns:
            trend_mult = np.where(data['Close'] < data['EMA_200'], 0.2, 0.0)
            
        bb_mult = np.zeros(len(data))
        if 'BB_Width' in data.columns:
            avg_w = data['BB_Width'].rolling(20).mean()
            bb_mult = np.where(data['BB_Width'] > avg_w * 1.2, 0.15, 0.0)
            
        vwap_mult = np.zeros(len(data))
        if 'VWAP' in data.columns:
            vwap_mult = np.where(data['Close'] < data['VWAP'], 0.1, 0.0)
            
        data['Risk_Mult'] = 1.0 + rsi_mult + trend_mult + bb_mult + vwap_mult
        data['Hybrid_VaR'] = data['Base_VaR'] * data['Risk_Mult']
        
        # Analyze breaches
        test_range = data.iloc[-lookback_days-1:-1] # Last year, excluding today (no Next_Return)
        
        std_breaches = test_range[test_range['Next_Return'] < test_range['Base_VaR']]
        hybrid_breaches = test_range[test_range['Next_Return'] < test_range['Hybrid_VaR']]
        
        return {
            "days_tested": len(test_range),
            "standard_breaches": len(std_breaches),
            "standard_breach_rate": round(len(std_breaches)/len(test_range) * 100, 2),
            "hybrid_breaches": len(hybrid_breaches),
            "hybrid_breach_rate": round(len(hybrid_breaches)/len(test_range) * 100, 2),
            "improvement_breaches": len(std_breaches) - len(hybrid_breaches),
            "confidence": confidence
        }
