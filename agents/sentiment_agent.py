import os
from typing import Dict, List, Any
import requests
from newsapi import NewsApiClient
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


def _score_articles_with_vader(articles: List[dict], analyzer: SentimentIntensityAnalyzer) -> float:
    if not articles:
        return 0.0

    scores = []
    for article in articles[:20]:
        text = (str(article.get('title') or '') + ' ' + str(article.get('description') or '')).strip()
        if not text:
            continue
        vs = analyzer.polarity_scores(text)
        scores.append(vs.get('compound', 0.0))

    if not scores:
        return 0.0
    # Scale compound score (-1..1) to same range
    avg = float(sum(scores) / len(scores))
    return round(avg, 3)


def run_sentiment(tickers: List[str]) -> Dict[str, float]:
    """
    Sentiment Agent
    Fetch news using NewsAPI (or newsdata.io) and compute sentiment using VADER for more robust scoring.
    Falls back to the previous simple approach when API keys or network fail.
    Returns a dict mapping ticker -> sentiment score (-1.0 .. 1.0)
    """
    news_key = os.getenv("NEWSAPI_KEY")
    if not news_key or news_key == "your_newsapi_key":
        print("Warning: NEWSAPI_KEY not found. Using mock sentiment.")
        return {ticker: 0.2 for ticker in tickers}

    analyzer = SentimentIntensityAnalyzer()

    try:
        sentiment_scores = {}

        # newsdata.io path
        if news_key.startswith("pub_"):
            for ticker in tickers:
                url = f"https://newsdata.io/api/1/news?apikey={news_key}&q={ticker}&language=en"
                response = requests.get(url, timeout=10).json()

                if response.get("status") == "success":
                    articles = response.get("results", [])
                    vader_score = _score_articles_with_vader(articles, analyzer)
                    llm_score = None
                    gemini_key = os.getenv('GEMINI_API_KEY')
                    if gemini_key and gemini_key != 'your_gemini_api_key':
                        try:
                            llm = ChatGoogleGenerativeAI(temperature=0.0, model="gemini-3-small", google_api_key=gemini_key)
                            texts = "\n".join([str(a.get('title','')) + ' ' + str(a.get('description','')) for a in articles[:8]])
                            template = "Provide a single numeric sentiment score between -1 (very negative) and 1 (very positive) for the following text:\n\n{context}\n\nRespond with only the number."
                            prompt = PromptTemplate(template=template, input_variables=["context"])
                            chain = prompt | llm | StrOutputParser()
                            llm_out = chain.invoke({"context": texts})
                            llm_score = float(llm_out.strip())
                        except Exception:
                            llm_score = None
                    sentiment_scores[ticker] = {"vader": vader_score, "llm": llm_score}
                else:
                    sentiment_scores[ticker] = {"vader": 0.0, "llm": None}
                    return sentiment_scores

        # NewsAPI path
        newsapi = NewsApiClient(api_key=news_key)
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        gemini_key = os.getenv('GEMINI_API_KEY')
        for ticker in tickers:
            res = newsapi.get_everything(q=ticker, from_param=from_date, language='en', sort_by='relevancy', page=1)
            articles = res.get('articles', [])
            vader_score = _score_articles_with_vader(articles, analyzer)
            llm_score = None
            if gemini_key and gemini_key != 'your_gemini_api_key':
                try:
                    llm = ChatGoogleGenerativeAI(temperature=0.0, model="gemini-3-small", google_api_key=gemini_key)
                    texts = "\n".join([str(a.get('title','')) + ' ' + str(a.get('description','')) for a in articles[:8]])
                    template = "Provide a single numeric sentiment score between -1 (very negative) and 1 (very positive) for the following text:\n\n{context}\n\nRespond with only the number."
                    prompt = PromptTemplate(template=template, input_variables=["context"])
                    chain = prompt | llm | StrOutputParser()
                    llm_out = chain.invoke({"context": texts})
                    llm_score = float(llm_out.strip())
                except Exception:
                    llm_score = None
            sentiment_scores[ticker] = {"vader": vader_score, "llm": llm_score}

        return sentiment_scores
    except Exception as e:
        print(f"Sentiment Agent Error: {e}")
        return {ticker: 0.0 for ticker in tickers}
