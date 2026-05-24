from google.cloud.firestore_v1.client import Client
from typing import Dict, Any, Optional
from datetime import datetime
from .firebase_config import get_firestore_client

db: Client = get_firestore_client()

def save_user(user_id: str, email: str) -> Dict[str, Any]:
    doc_ref = db.collection('users').document(user_id)
    data = {
        'email': email,
        'created_at': datetime.utcnow()
    }
    doc_ref.set(data)
    return data

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    doc_ref = db.collection('users').document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

def save_profile(profile_id: str, user_id: str, income: float, investment_amount: float, duration: int, duration_unit: str, stated_risk: str, risk_type: str) -> Dict[str, Any]:
    doc_ref = db.collection('profiles').document(profile_id)
    data = {
        'user_id': user_id,
        'income': income,
        'investment_amount': investment_amount,
        'duration': duration,
        'duration_unit': duration_unit,
        'stated_risk': stated_risk,
        'risk_type': risk_type,
        'created_at': datetime.utcnow()
    }
    doc_ref.set(data)
    return data

def save_portfolio(
    portfolio_id: str,
    user_id: str,
    recommended_stocks: list,
    allocation: dict,
    expected_return: str,
    risk_score: str,
    explanation: str,
    backtest_metrics: dict | None = None,
    model_versions: dict | None = None,
) -> Dict[str, Any]:
    doc_ref = db.collection('portfolios').document(portfolio_id)
    data = {
        'user_id': user_id,
        'recommended_stocks': recommended_stocks,
        'allocation': allocation,
        'expected_return': expected_return,
        'risk_score': risk_score,
        'explanation': explanation,
        'created_at': datetime.utcnow()
    }
    if backtest_metrics is not None:
        data['backtest_metrics'] = backtest_metrics
    if model_versions is not None:
        data['model_versions'] = model_versions

    doc_ref.set(data)
    return data

def get_portfolio(user_id: str) -> Optional[Dict[str, Any]]:
    # Using FieldFilter to clear warning, sorting in memory to avoid Firestore composite index requirement
    from google.cloud.firestore_v1.base_query import FieldFilter
    query = db.collection('portfolios').where(filter=FieldFilter('user_id', '==', user_id))
    results = list(query.stream())
    if not results:
        return None
        
    # Sort in memory to get the latest portfolio
    sorted_results = sorted(results, key=lambda doc: doc.to_dict().get('created_at', str(datetime.min)), reverse=True)
    return sorted_results[0].to_dict()

def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    doc_ref = db.collection('profiles').document(profile_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

def get_all_portfolios(user_id: str, limit: int = 5) -> list[Dict[str, Any]]:
    from google.cloud.firestore_v1.base_query import FieldFilter
    query = db.collection('portfolios').where(filter=FieldFilter('user_id', '==', user_id))
    results = list(query.stream())
    
    sorted_results = sorted(results, key=lambda doc: doc.to_dict().get('created_at', str(datetime.min)), reverse=True)
    return [doc.to_dict() for doc in sorted_results[:limit]]

def save_analysis_history(analysis_id: str, user_id: str, data: Dict[str, Any]) -> None:
    doc_ref = db.collection('analysis_history').document(analysis_id)
    data['created_at'] = datetime.utcnow()
    doc_ref.set(data)

def update_analysis_status(user_id: str, status: str) -> None:
    doc_ref = db.collection('analysis_status').document(user_id)
    doc_ref.set({
        'status': status,
        'updated_at': datetime.utcnow()
    })

def get_analysis_status(user_id: str) -> Optional[str]:
    doc_ref = db.collection('analysis_status').document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('status')
    return None
