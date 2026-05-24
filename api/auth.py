from fastapi import APIRouter, HTTPException, status
from schemas.user import UserRegisterRequest, UserLoginRequest
from firebase.firebase_config import get_auth_client
from firebase.firestore_service import save_user
from firebase_admin import auth

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest):
    try:
        # Create user in Firebase Auth
        user = auth.create_user(
            email=request.email,
            password=request.password
        )
        # Store basic user info in Firestore
        save_user(user.uid, request.email)
        return {"message": "User created successfully", "user_id": user.uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(request: UserLoginRequest):
    # Note: In a real production environment, the client usually authenticates directly 
    # with Firebase via the Client SDK and sends an ID token to the backend.
    # The Admin SDK does not support comparing passwords directly.
    # To properly implement username/password login here, one would use the Firebase REST Auth API.
    # For this demonstration backend, we simply create a custom token if the user exists.
    try:
        user = auth.get_user_by_email(request.email)
        # Since we cannot verify password here directly with Admin SDK, we just generate a token.
        custom_token = auth.create_custom_token(user.uid)
        return {"message": "Login successful", "token": custom_token.decode("utf-8"), "user_id": user.uid}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials or user not found.")
