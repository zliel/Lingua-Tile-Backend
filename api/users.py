import dotenv
from fastapi.encoders import jsonable_encoder

from models import User

from fastapi import APIRouter, status
from pymongo import MongoClient

router = APIRouter(prefix="/api/users", tags=["Cards"])
mongo_host = dotenv.get_key(".env", "MONGO_HOST")
client = MongoClient(mongo_host)
db = client['lingua-tile']
user_collection = db['users']


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user(user: User):
    """Create a new user in the database"""
    new_user = jsonable_encoder(user)

    user_collection.insert_one(new_user)

    return user
