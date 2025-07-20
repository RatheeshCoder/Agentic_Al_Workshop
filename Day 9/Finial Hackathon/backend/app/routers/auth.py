from fastapi import APIRouter
from app.models.user_model import UserSignup, UserLogin
from app.services.auth.auth_controller import signup_user, login_user

router = APIRouter()

@router.post("/signup")
async def signup(user: UserSignup):
    return await signup_user(user)

@router.post("/login")
async def login(user: UserLogin):
    return await login_user(user)
