from typing import Dict, Any

def run_profiling(profile_data: Dict[str, Any]) -> str:
    """
    User Profiling Agent
    Input:
    - income
    - investment amount
    - duration
    - risk answers
    Output: risk_type (conservative, moderate, aggressive)
    """
    income = profile_data.get('income', 0)
    duration = profile_data.get('duration', 0)
    investment = profile_data.get('investment_amount', 0)
    answers = profile_data.get('risk_answers', [])
    
    # Basic logic: High income & duration > high risk capacity
    score = 0
    if income > 100000:
        score += 2
    elif income > 50000:
        score += 1
        
    if duration > 10:
        score += 2
    elif duration > 5:
        score += 1
        
    if "high" in [a.lower() for a in answers]:
        score += 2
        
    if score >= 4:
        return "aggressive"
    elif score >= 2:
        return "moderate"
    else:
        return "conservative"
