import dotenv
import jwt

from models import User
from api.users import is_admin
from api.dependencies import get_current_user, SECRET_KEY, ALGORITHM, pwd_context, get_db

from fastapi import APIRouter, status, HTTPException, Depends
from pymongo import MongoClient
from passlib.context import CryptContext
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/auth", tags=["Auth"])
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7



def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_user(user: User, db=Depends(get_db)):
    """Login a user"""
    user_collection = db['users']
    found_user = user_collection.find_one({"username": user.username})

    if found_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    elif not pwd_context.verify(user.password, found_user['password']):
        raise HTTPException(status_code=401, detail="Incorrect password")

    # Convert found_user to User model and remove its password from the response
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"token": access_token, "token_type": "bearer", "isAdmin": "admin" in found_user.get("roles", []), "username": found_user.get("username", "")}


@router.get("/check-admin", status_code=status.HTTP_200_OK)
async def check_admin(current_user: User = Depends(get_current_user)):
    """Check if the current user is an admin"""
    if is_admin(current_user):
        return {"isAdmin": True}
    else:
        return {"isAdmin": False}