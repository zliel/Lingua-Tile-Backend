import bson
import dotenv
from fastapi.encoders import jsonable_encoder

from models import User

from fastapi import APIRouter, status, HTTPException
from pymongo import MongoClient

router = APIRouter(prefix="/api/auth", tags=["Auth"])
mongo_host = dotenv.get_key(".env", "MONGO_HOST")
client = MongoClient(mongo_host)
db = client['lingua-tile']
user_collection = db['users']

@router.post("/login", status_code=status.HTTP_200_OK)
async def login_user(user: User):
    """Login a user"""
    user = user_collection.find_one({"username": user.username, "password": user.password})
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
