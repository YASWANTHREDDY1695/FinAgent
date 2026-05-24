from pydantic import BaseModel, EmailStr
from typing import Optional

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class ProfileCreateRequest(BaseModel):
    user_id: str
    income: float
    investment_amount: float
    duration: int
    duration_unit: str = "years"
    stated_risk: str = "med"
    risk_answers: list[str] = [] # Example format for questionnaire answers
