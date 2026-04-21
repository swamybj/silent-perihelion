import sys
import subprocess

packages = ["ta", "sklearn", "statsmodels", "scipy", "flask", "yfinance"]

print("Verifying packages...")
for pkg in packages:
    try:
        __import__(pkg if pkg != "sklearn" else "sklearn")
        print(f"[OK] {pkg}")
    except ImportError:
        print(f"[MISSING] {pkg}")

# Try to run a quick test of the logic
try:
    import pandas as pd
    import numpy as np
    from technical_analysis import run_technical_analysis, get_augmented_df
    from forecaster import MLForecaster
    from risk_engine import RiskEngine
    from simulator import MarketSimulator

    # Dummy data
    dates = pd.date_range(start='2020-01-01', periods=500)
    df = pd.DataFrame({
        'Open': np.random.randn(500) + 100,
        'High': np.random.randn(500) + 101,
        'Low': np.random.randn(500) + 99,
        'Close': np.random.randn(500) + 100,
        'Volume': np.random.randint(1000, 5000, 500)
    }, index=dates)

    print("\nRunning Technical Analysis...")
    ta_res = run_technical_analysis(df)
    print(f"Signal: {ta_res['composite_signal']['signal']}, Score: {ta_res['composite_signal']['score']}")

    # Augment DF for ML and Risk
    df_aug = get_augmented_df(df)

    print("\nRunning ML Forecast...")
    forecaster = MLForecaster(df_aug)
    f_res = forecaster.train_and_predict()
    print(f"Direction: {f_res.get('direction')}, Prob: {f_res.get('probability')}%")

    print("\nRunning Risk Analysis...")
    engine = RiskEngine(df_aug)
    r_res = engine.calculate_hybrid_var()
    print(f"Hybrid VaR: {r_res.get('hybrid_var_pct')}%")

    print("\n[SUCCESS] Integration test passed.")
except Exception as e:
    print(f"\n[FAILURE] Integration test failed: {e}")
    import traceback
    traceback.print_exc()
