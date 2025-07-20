from fastapi import HTTPException
from app.models.user_model import UserSignup, UserLogin
from app.utils.auth_utils import hash_password, verify_password, create_access_token
from app.database.connection import get_async_collections
from datetime import datetime

async def signup_user(user: UserSignup):
    try:
        collections = get_async_collections()
        users_collection = collections["users"]

        existing = await users_collection.find_one({"email": user.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = hash_password(user.password)
        user_data = {
            "name": user.name,
            "email": user.email,
            "role": user.role, 
            "password": hashed,
            "created_at": datetime.now(),
            "is_active": True
        }

        result = await users_collection.insert_one(user_data)
        if result.inserted_id:
            return {
                "message": "User registered successfully",
                "user_id": str(result.inserted_id)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create user")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


async def login_user(user: UserLogin):
    try:
        collections = get_async_collections()
        users_collection = collections["users"]

        found = await users_collection.find_one({"email": user.email})
        if not found:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(user.password, found["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not found.get("is_active", True):
            raise HTTPException(status_code=401, detail="Account is deactivated")

        token_data = {
            "sub": str(found["_id"]),
            "email": user.email,
            "name": found["name"],
            "role": found["role"],
        }
        token = create_access_token(token_data)

        return {
            "success": True,
            "message": "Login successful",
            "access_token": token,
            "user": {
                "id": str(found["_id"]),
                "name": found["name"],
                "email": found["email"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
