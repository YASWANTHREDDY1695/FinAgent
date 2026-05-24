from fastapi import APIRouter, HTTPException, status
from schemas.user import ProfileCreateRequest
from firebase.firestore_service import save_profile, get_profile
import uuid

router = APIRouter(prefix="/profile", tags=["Profile"])

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_profile(request: ProfileCreateRequest):
    try:
        profile_id = str(uuid.uuid4())
        
        # Simple local risk_type estimation based on duration & income.
        # Note: In the full pipeline, the 'profiling_agent.py' might refine this.
        # Standardize duration into years for risk logic
        duration_in_years = request.duration
        if request.duration_unit == 'months':
            duration_in_years = request.duration / 12.0
        elif request.duration_unit == 'days':
            duration_in_years = request.duration / 365.0
            
        risk_type = "moderate"
        if duration_in_years > 10 and request.investment_amount > 10000:
            risk_type = "aggressive"
        elif duration_in_years < 3:
            risk_type = "conservative"

        data = save_profile(
            profile_id=profile_id,
            user_id=request.user_id,
            income=request.income,
            investment_amount=request.investment_amount,
            duration=request.duration,
            duration_unit=request.duration_unit,
            stated_risk=request.stated_risk,
            risk_type=risk_type
        )
        return {"message": "Profile created successfully", "profile_id": profile_id, "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{profile_id}", status_code=status.HTTP_200_OK)
async def get_user_profile(profile_id: str):
    try:
        data = get_profile(profile_id)
        if not data:
            raise HTTPException(status_code=404, detail="Profile not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
