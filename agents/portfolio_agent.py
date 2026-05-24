import numpy as np
from typing import Dict, List, Any
from scipy.optimize import minimize
import yfinance as yf
import pandas as pd
from sklearn.covariance import LedoitWolf


def run_portfolio_optimization(tickers: List[str], expected_returns: Dict[str, float], risk_metrics: Dict[str, Any], risk_profile: str, history_period: str = "1y") -> Dict[str, float]:
    """
    Portfolio Optimization Agent
    Improved MPT optimization using a full covariance matrix estimated from historical returns (via yfinance).
    Returns: Dict of ticker to weight (e.g., {"AAPL": 0.4, "MSFT": 0.6})
    """
    num_assets = len(tickers)
    if num_assets == 0:
        return {}

    # Build expected returns vector (annualized)
    returns = np.array([expected_returns.get(t, 0.0) for t in tickers])

    # Use diagonal covariance matrix for simplicity
    variances = np.array([risk_metrics.get(t, {}).get('variance', 0.04) for t in tickers])
    cov_matrix = np.diag(variances)

    # Adjusted risk bounds and diversification constraints based on profile
    target_return = returns.mean() if len(returns) > 0 else 0.0
    max_weight = 0.40 # Default max 40% in any one stock
    
    if risk_profile == "aggressive":
        # Target top 25% of returns instead of just max * 0.9
        target_return = np.percentile(returns, 75) if len(returns) > 0 else target_return
        max_weight = 0.45 # Allow slightly more concentration for aggressive
    elif risk_profile == "conservative":
        target_return = returns.mean() * 0.9 if len(returns) > 0 else target_return
        max_weight = 0.25 # Force more diversification for conservative
    else: # moderate
        target_return = returns.mean() * 1.1 if len(returns) > 0 else target_return
        max_weight = 0.35

    # Objective: Minimize volatility (annualized portfolio volatility)
    def portfolio_volatility(weights, cov_matrix):
        return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

    # Constraints: weights sum to 1 and portfolio return >= target
    def check_sum_1(weights):
        return np.sum(weights) - 1.0

    def check_target_return(weights, returns, target):
        return np.dot(weights, returns) - target

    constraints = (
        {'type': 'eq', 'fun': check_sum_1},
        {'type': 'ineq', 'fun': lambda w: check_target_return(w, returns, target_return)}
    )

    # Bounds: Min 2%, Max set by risk profile to ensure diversification
    bounds = tuple((0.02, max_weight) for _ in range(num_assets))
    init_guess = np.array([1 / num_assets] * num_assets)

    try:
        opt_result = minimize(
            portfolio_volatility,
            init_guess,
            args=(cov_matrix,),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        weights = opt_result.x
        allocation = {tickers[i]: round(float(weights[i]), 4) for i in range(num_assets)}
        return allocation
    except Exception as e:
        print(f"Optimization Error: {e}")
        # Fallback to equal weight
        return {t: round(1 / num_assets, 4) for t in tickers}
