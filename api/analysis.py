from fastapi import APIRouter, HTTPException, status
from schemas.portfolio import AnalysisRunRequest, PortfolioResponse
from typing import List
from firebase.firestore_service import save_portfolio, get_portfolio, get_profile, get_all_portfolios, update_analysis_status, get_analysis_status
import pandas as pd
import uuid
import asyncio

# Import Agents
from agents.market_agent import run_market_data
from agents.sentiment_agent import run_sentiment
from agents.risk_agent import run_risk_analysis
from agents.prediction_agent import run_prediction
from agents.portfolio_agent import run_portfolio_optimization
from agents.explanation_agent import run_explanation

router = APIRouter(prefix="/analysis", tags=["Analysis"])

@router.post("/run", response_model=PortfolioResponse)
async def run_analysis(request: AnalysisRunRequest):
    """
    WORKFLOW PIPELINE:
    Retrieve profile -> Run Agent Pipeline -> Save Results -> Return Recommendation
    """
    try:
        portfolio_id = str(uuid.uuid4())
        
        # 1. Retrieve user profile
        profile_data = get_profile(request.profile_id)
        if not profile_data:
            raise HTTPException(status_code=404, detail="Profile not found")

        # 2a. Use stated risk from profile
        stated_risk = profile_data.get('stated_risk', 'med')
        risk_mapping = {'low': 'conservative', 'med': 'moderate', 'high': 'aggressive'}
        risk_type = risk_mapping.get(stated_risk.lower(), 'moderate')
        print(f"Risk: {risk_type}")
        import random
        all_tickers = [
            # Tech & Comm
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX", "ADBE", "CRM", "AMD", "INTC", "CSCO", "ORCL", "IBM", "QCOM", "TXN", "AVGO", "NOW", "INTU", 
            # Financials
            "JPM", "V", "MA", "BAC", "WFC", "C", "GS", "MS", "AXP", "BLK", "SCHW", "SPGI", "CB", "PGR", "CME", 
            # Healthcare
            "JNJ", "UNH", "PFE", "ABBV", "LLY", "MRK", "TMO", "DHR", "ABT", "BMY", "AMGN", "CVS", "ISRG", "SYK", "ZTS",  
            # Consumer Discretionary & Staples
            "PG", "KO", "PEP", "WMT", "COST", "MCD", "HD", "NKE", "SBUX", "TGT", "LOW", "PM", "MO", "EL", "CL",
            # Industrials & Energy
            "XOM", "CVX", "COP", "SLB", "EOG", "RTX", "HON", "UPS", "UNP", "BA", "LMT", "CAT", "GE", "MMM", "DE",
            # REITs / Utilities
            "AMT", "PLD", "CCI", "NEE", "DUK", "SO", "D"
        ]
        # Randomly select 15 stocks for the AI to analyze this run to improve diversity while keeping response times reasonable
        target_tickers = random.sample(all_tickers, 10)

        # 3. Update status: Starting Agent Pipeline
        update_analysis_status(request.user_id, "Initializing Multi-Agent Pipeline...")

        # Run massive data-gathering agents concurrently
        # We use asyncio.to_thread to run these blocking synchronous functions in parallel background threads!
        update_analysis_status(request.user_id, f"Gathering Market & Sentiment Data for {len(target_tickers)} stocks...")
        market_data, sentiment_data, risk_metrics, prediction_data = await asyncio.gather(
            asyncio.to_thread(run_market_data, target_tickers),
            asyncio.to_thread(run_sentiment, target_tickers),
            asyncio.to_thread(run_risk_analysis, target_tickers),
            asyncio.to_thread(run_prediction, target_tickers, user_id=request.user_id) # Pass user_id for granular updates
        )
        expected_returns = {ticker: data["expected_return"] for ticker, data in prediction_data.items()}
        
        # filter out stocks with missing data to prevent optimization failure
        valid_tickers = [t for t in target_tickers if t in expected_returns and t in risk_metrics]
        
        # 7. Portfolio Optimization Agent
        update_analysis_status(request.user_id, "Optimizing Portfolio Allocation...")
        allocation = run_portfolio_optimization(valid_tickers, expected_returns, risk_metrics, risk_type)
        
        # Filter allocation to only include stocks > 1% weight
        filtered_allocation = {k: v for k, v in allocation.items() if v >= 0.01}
        recommended_stocks = list(filtered_allocation.keys())
        
        # Calculate overall portfolio annualized expected return
        annual_expected_return = sum(expected_returns.get(ticker, 0) * weight for ticker, weight in filtered_allocation.items())
        
        # Calculate compounded total return over the investment period
        duration_val = profile_data.get('duration', 1)
        duration_unit = profile_data.get('duration_unit', 'years')
        duration_years = duration_val
        if duration_unit == 'months':
            duration_years = duration_val / 12.0
        elif duration_unit == 'days':
            duration_years = duration_val / 365.0
            
        total_period_return = ((1 + annual_expected_return) ** duration_years) - 1
        expected_return_str = f"{total_period_return * 100:.2f}% (Over {duration_val} {duration_unit})"

        # 8. Explanation Agent
        explanation = run_explanation(
            risk_type=risk_type,
            portfolio_allocation=filtered_allocation,
            expected_return=total_period_return,
            market_data=market_data,
            sentiment_data=sentiment_data
        )
        # Collect model versions and per-ticker backtest MSE from prediction_data
        model_versions = {t: (prediction_data.get(t, {}).get('model_path') if isinstance(prediction_data.get(t, {}), dict) else None) for t in recommended_stocks}
        per_ticker_mse = {t: (prediction_data.get(t, {}).get('backtest_mse') if isinstance(prediction_data.get(t, {}), dict) else None) for t in recommended_stocks}

        # Compute portfolio backtest metrics over recent period (1y)
        def compute_portfolio_backtest(tickers, allocation, period='1y'):
            import yfinance as yf
            import pandas as pd
            try:
                df = pd.DataFrame()
                for t in tickers:
                    data = yf.download(t, period=period, progress=False)
                    if data.empty or 'Close' not in data:
                        continue
                    if isinstance(data['Close'], pd.DataFrame):
                        s = data['Close'].iloc[:, 0].dropna()
                    else:
                        s = data['Close'].dropna()
                    s = s.rename(t)
                    df = pd.concat([df, s], axis=1)
                df = df.dropna()
                if df.empty:
                    return None
                returns = df.pct_change().dropna()
                weights = pd.Series({t: allocation.get(t, 0) for t in returns.columns})
                # Normalize weights to available columns
                weights = weights.reindex(returns.columns).fillna(0)
                weights = pd.to_numeric(weights, errors='coerce').fillna(0)
                weights = weights / weights.sum() if weights.sum() != 0 else weights
                port_daily = returns.dot(weights)
                cumulative = (1 + port_daily).cumprod()
                total_return = cumulative.iloc[-1] - 1
                annual_return = port_daily.mean() * 252
                annual_vol = port_daily.std() * (252 ** 0.5)
                sharpe = (annual_return - 0.05) / annual_vol if annual_vol != 0 else None
                # Max drawdown
                roll_max = cumulative.cummax()
                drawdown = (cumulative / roll_max) - 1
                max_dd = drawdown.min()
                return {
                    'total_return': float(total_return),
                    'annual_return': float(annual_return),
                    'annual_volatility': float(annual_vol),
                    'sharpe': float(sharpe) if sharpe is not None else None,
                    'max_drawdown': float(max_dd)
                }
            except Exception as e:
                print(f"Backtest computation failed: {e}")
                return None

        portfolio_backtest = compute_portfolio_backtest(recommended_stocks, filtered_allocation, period='1y')

        backtest_metrics = {
            'per_ticker_mse': per_ticker_mse,
            'portfolio': portfolio_backtest
        }

        # Save to Firestore (include backtest and model info)
        save_portfolio(
            portfolio_id=portfolio_id,
            user_id=request.user_id,
            recommended_stocks=recommended_stocks,
            allocation=filtered_allocation,
            expected_return=expected_return_str,
            risk_score=risk_type,
            explanation=explanation,
            backtest_metrics=backtest_metrics,
            model_versions=model_versions
        )

        return PortfolioResponse(
            user_id=request.user_id,
            risk_type=risk_type,
            recommended_stocks=recommended_stocks,
            allocation=filtered_allocation,
            expected_return=expected_return_str,
            risk_score=risk_type,
            explanation=explanation,
            backtest_metrics=backtest_metrics,
            model_versions=model_versions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/portfolio/{user_id}", response_model=PortfolioResponse)
async def get_user_portfolio(user_id: str):
    try:
        data = get_portfolio(user_id)
        if not data:
            raise HTTPException(status_code=404, detail="Portfolio not found for user")
        
        return PortfolioResponse(
            user_id=data["user_id"],
            risk_type=data.get("risk_score", "Unknown"),
            recommended_stocks=data.get("recommended_stocks", []),
            allocation=data.get("allocation", {}),
            expected_return=data.get("expected_return", ""),
            risk_score=data.get("risk_score", ""),
            explanation=data.get("explanation", ""),
            backtest_metrics=data.get("backtest_metrics", None),
            model_versions=data.get("model_versions", None)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolios/{user_id}", response_model=List[PortfolioResponse])
async def get_user_portfolios(user_id: str):
    from firebase.firestore_service import get_all_portfolios
    try:
        portfolios = get_all_portfolios(user_id, limit=20)
        return [
            PortfolioResponse(
                user_id=data["user_id"],
                risk_type=data.get("risk_score", "Unknown"),
                recommended_stocks=data.get("recommended_stocks", []),
                allocation=data.get("allocation", {}),
                expected_return=data.get("expected_return", ""),
                risk_score=data.get("risk_score", ""),
                explanation=data.get("explanation", ""),
                backtest_metrics=data.get("backtest_metrics", None),
                model_versions=data.get("model_versions", None)
            ) for data in portfolios
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{user_id}")
async def get_status(user_id: str):
    from firebase.firestore_service import get_analysis_status
    status = get_analysis_status(user_id)
    return {"status": status or "Idle"}
