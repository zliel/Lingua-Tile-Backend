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
    user.hash_password()
    user_collection.insert_one(user.dict(by_alias=True))

    return user

@router.get("/{user_id}", response_model=User, response_model_exclude={"password"})
async def get_user(user_id: str):
    """Retrieve a user from the database by id"""
    user = user_collection.find_one({"_id": user_id})
    return User(**user)