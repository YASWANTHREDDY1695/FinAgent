import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Any, List

def run_market_data(tickers: List[str], period: str = "1y") -> Dict[str, Any]:
    """
    Market Data Agent
    Fetch stock history via yfinance
    Compute SMA, RSI, volatility
    """
    results = {}
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            
            if hist.empty:
                continue
                
            close_prices = hist['Close']
            
            # SMA 50
            sma_50 = close_prices.rolling(window=50).mean().iloc[-1]
            
            # Daily Returns & Volatility
            daily_returns = close_prices.pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252)
            
            # RSI (Relative Strength Index) 14-day
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            results[ticker] = {
                "current_price": close_prices.iloc[-1],
                "sma_50": sma_50 if not np.isnan(sma_50) else None,
                "volatility": volatility,
                "rsi": rsi if not np.isnan(rsi) else None
            }
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            
    return results
