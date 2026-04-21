"""
Market Scenario Simulator (What-If).

Simulates price movements and determines recommended actions.
"""

import pandas as pd

class MarketSimulator:
    def __init__(self, ticker, current_price, volatility_score=0.02):
        self.ticker = ticker
        self.current_price = current_price
        self.volatility_score = volatility_score # Percentage e.g. 0.02 for 2%
        
    def run_scenarios(self):
        """
        Runs standard what-if scenarios based on current price and volatility.
        """
        scenarios = [
            {"name": "Standard Drop", "move": -max(0.05, self.volatility_score * 2)},
            {"name": "Correction", "move": -0.10},
            {"name": "Bear Market / Crash", "move": -0.20},
            {"name": "Standard Rally", "move": max(0.05, self.volatility_score * 2)},
            {"name": "Breakout", "move": 0.10}
        ]
        
        results = []
        for s in scenarios:
            target_price = self.current_price * (1 + s['move'])
            
            # Determine Action
            if s['move'] <= -0.20:
                action = "Deep Value Buy / Portfolio Hedge"
            elif s['move'] <= -0.10:
                action = "Aggressive Buy / Sell Puts"
            elif s['move'] < 0:
                action = "Scale In / Buy Dip"
            elif s['move'] >= 0.10:
                action = "Take Profit / Sell Calls"
            else:
                action = "Hold / Monitor"
                
            results.append({
                "scenario": s['name'],
                "percent_move": round(s['move'] * 100, 2),
                "target_price": round(target_price, 2),
                "recommended_action": action
            })
            
        return results
