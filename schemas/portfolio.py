from pydantic import BaseModel
from typing import Dict, List, Any, Optional


class AnalysisRunRequest(BaseModel):
    user_id: str
    profile_id: str


class PortfolioResponse(BaseModel):
    user_id: str
    risk_type: str
    recommended_stocks: List[str]
    allocation: Dict[str, float]
    expected_return: str
    risk_score: str
    explanation: str
    backtest_metrics: Optional[Dict[str, Any]] = None
    model_versions: Optional[Dict[str, str]] = None
