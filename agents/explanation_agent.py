from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

def run_explanation(
    risk_type: str, 
    portfolio_allocation: Dict[str, float], 
    expected_return: float, 
    market_data: Dict[str, Any], 
    sentiment_data: Dict[str, float]
) -> str:
    """
    Explanation Agent
    Generate natural language explanation using LLM prompt templates via LangChain.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key":
        # Fallback if no valid Gemini key is set
        print("Warning: valid GEMINI_API_KEY not found. Using fallback explanation generator.")
        stocks = ", ".join(portfolio_allocation.keys())
        return f"Based on your {risk_type} risk profile, we recommend a portfolio of {stocks} with an expected annual return of {expected_return*100:.2f}%. This balances momentum and risk according to current market metrics and news sentiment."

    try:
        llm = ChatGoogleGenerativeAI(temperature=0.7, model="gemini-3-flash-preview", google_api_key=api_key)
        
        template = """
        You are a seasoned personalized financial advisor AI in FinAgent Pro.
        
        The user has a '{risk_type}' risk profile.
        We have calculated the following optimal stock allocation: {portfolio_allocation}
        The expected annual return of this portfolio is {expected_return}%.
        
        Here is the current market context:
        - Technical Data (SMA, Volatility, RSI): {market_data}
        - Sentiment Scores (-1.0 to 1.0): {sentiment_data}
        
        Write a brief, professional, and convincing summary (2-3 short paragraphs) explaining WHY this specific allocation is recommended based on the user's risk type, the current market technicals, and the news sentiment. 
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["risk_type", "portfolio_allocation", "expected_return", "market_data", "sentiment_data"]
        )
        
        chain = prompt | llm | StrOutputParser()
        
        explanation = chain.invoke({
            "risk_type": risk_type,
            "portfolio_allocation": portfolio_allocation,
            "expected_return": round(expected_return * 100, 2),
            "market_data": market_data,
            "sentiment_data": sentiment_data
        })
        
        return explanation
    except Exception as e:
        print(f"Explanation Agent Error: {e}")
        return "Based on your risk profile and our multi-agent analysis, this portfolio optimizes your expected return while adhering to your risk tolerance boundaries."
