import dotenv

from models import User

from fastapi import APIRouter, status, HTTPException
from pymongo import MongoClient
from passlib.context import CryptContext

router = APIRouter(prefix="/api/auth", tags=["Auth"])
mongo_host = dotenv.get_key(".env", "MONGO_HOST")
client = MongoClient(mongo_host)
db = client['lingua-tile']
user_collection = db['users']
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_user(user: User):
    """Login a user"""
    found_user = user_collection.find_one({"username": user.username})

    if found_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    elif not pwd_context.verify(user.password, found_user['password']):
        raise HTTPException(status_code=401, detail="Incorrect password")

    # Convert found_user to User model and remove its password from the response
    found_user = User(**found_user)
    del found_user.password

    return found_user
