"""
Machine Learning Forecaster.

Uses Random Forest to predict price direction based on technical indicators.
"""

import pandas as pd
import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class MLForecaster:
    def __init__(self, df):
        self.df = df.copy()
        if SKLEARN_AVAILABLE:
            self.classifier = RandomForestClassifier(n_estimators=100, random_state=42, min_samples_leaf=5)
            self.regressor = RandomForestRegressor(n_estimators=100, random_state=42, min_samples_leaf=5)
        else:
            self.classifier = None
            self.regressor = None
        
        # Features to use for prediction
        self.feature_columns = ['RSI', 'MACD', 'MACD_Signal', 'BB_Width', 'Stoch_K', 'ATR', 'OBV', 'ADX']

    def prepare_data(self, forecast_days=30):
        """
        Prepares features (X) and target (y) for training.
        Target: 1 if Price(t + forecast_days) > Price(t), else 0.
        """
        if not SKLEARN_AVAILABLE or self.df is None or len(self.df) < 50:
            return None, None, None
            
        data = self.df.copy()
        
        # Ensure 'BB_Width' existence if not already there
        if 'BB_Width' not in data.columns and 'BB_High' in data.columns and 'BB_Low' in data.columns:
            data['BB_Width'] = (data['BB_High'] - data['BB_Low']) / data['BB_Mid']
            
        # Target: Price appreciation over 'forecast_days'
        data['Future_Close'] = data['Close'].shift(-forecast_days)
        data['Target'] = (data['Future_Close'] > data['Close']).astype(int)
        
        # Drop rows with NaNs in features or target
        available_features = [f for f in self.feature_columns if f in data.columns]
        data.dropna(subset=available_features + ['Target'], inplace=True)
        
        if len(data) < 20:
            return None, None, None
            
        X = data[available_features]
        y = data['Target']
        
        return X, y, available_features

    def train_and_predict(self, forecast_days=30):
        """
        Trains both classifier and regressor to predict direction and target price.
        """
        if not SKLEARN_AVAILABLE:
            return {"error": "Machine learning dependencies (scikit-learn) not available."}
            
        X, y_class, features = self.prepare_data(forecast_days)
        
        if X is None or len(X) < 60:
            return None # Not error, just skip this horizon

        # Prepare regression target (percent return)
        data = self.df.copy()
        data['Return'] = (data['Close'].shift(-forecast_days) / data['Close']) - 1
        data.dropna(subset=features + ['Return'], inplace=True)
        X_reg = data[features]
        y_reg = data['Return']

        # Fit models
        self.classifier.fit(X, y_class)
        self.regressor.fit(X_reg, y_reg)
        
        # Get latest data point for prediction
        latest_row = self.df.iloc[[-1]]
        latest_X = latest_row[features]
        
        if latest_X.isnull().values.any():
            latest_row = self.df.iloc[[-2]]
            latest_X = latest_row[features]
            if latest_X.isnull().values.any():
                return None

        # Predict Direction
        prediction = self.classifier.predict(latest_X)[0]
        probs = self.classifier.predict_proba(latest_X)[0]
        prob_up = float(probs[1])
        prob_down = float(probs[0])
        direction = "UP" if prediction == 1 else "DOWN"
        confidence = prob_up if prediction == 1 else prob_down
        
        # Predict Price Target
        current_price = float(latest_row['Close'].iloc[0])
        predicted_return = float(self.regressor.predict(latest_X)[0])
        target_price = current_price * (1 + predicted_return)
        
        # Expected Range based on ATR (1 Std Dev approx)
        atr = float(latest_row['ATR'].iloc[0]) if 'ATR' in latest_row.columns else (current_price * 0.02)
        expected_move = atr * np.sqrt(forecast_days)
        
        return {
            "forecast_period": f"{forecast_days}d",
            "direction": direction,
            "probability": round(confidence * 100, 1),
            "target_price": round(target_price, 2),
            "lower_bound": round(current_price - expected_move, 2),
            "upper_bound": round(current_price + expected_move, 2),
            "accuracy_score": round(self.classifier.score(X, y_class) * 100, 1),
            "samples_trained": len(X)
        }

    def predict_multi_horizon(self, periods=[7, 14, 30]):
        """
        Runs predictions for multiple time horizons.
        """
        results = {}
        for p in periods:
            res = self.train_and_predict(forecast_days=p)
            if res:
                results[f"horizon_{p}d"] = res
        return results
