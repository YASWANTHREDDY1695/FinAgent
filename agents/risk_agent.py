import yfinance as yf
import numpy as np
from typing import Dict, Any, List

def run_risk_analysis(tickers: List[str], period: str = "1y", risk_free_rate: float = 0.05) -> Dict[str, Any]:
    """
    Risk Agent
    Calculate Sharpe ratio, Beta, and Variance for a list of stocks
    """
    results = {}
    
    # Typically beta is calculated against a market benchmark like SPY
    benchmark = yf.Ticker("SPY").history(period=period)['Close'].pct_change().dropna()
    benchmark_variance = benchmark.var()
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            
            if hist.empty:
                continue
                
            close_prices = hist['Close']
            daily_returns = close_prices.pct_change().dropna()
            
            # Variance
            variance = daily_returns.var()
            
            # Annualized Return & Risk
            annual_return = daily_returns.mean() * 252
            annual_volatility = daily_returns.std() * np.sqrt(252)
            
            # Sharpe Ratio
            sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility != 0 else 0
            
            # Beta
            covariance = daily_returns.cov(benchmark)
            beta = covariance / benchmark_variance if benchmark_variance != 0 else 1.0
            
            results[ticker] = {
                "sharpe_ratio": round(sharpe_ratio, 2),
                "beta": round(beta, 2),
                "variance": float(variance)
            }
        except Exception as e:
            print(f"Error in Risk Agent for {ticker}: {e}")
            
    return results
