import dotenv
from bson import ObjectId
from fastapi.encoders import jsonable_encoder

from models import User

from fastapi import APIRouter, status, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
import jwt
from pymongo import MongoClient

router = APIRouter(prefix="/api/users", tags=["Users"])
mongo_host = dotenv.get_key(".env", "MONGO_HOST")
client = MongoClient(mongo_host)
db = client['lingua-tile']
user_collection = db['users']
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = dotenv.get_key(".env", "SECRET_KEY")
ALGORITHM = "HS256"


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Decode the token to get the username
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        # Find the user in the database by username
        user = user_collection.find_one({"username": username})
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        return User(**user)

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


def is_admin(user: User):
    return "admin" in user.roles


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user(user: User):
    """Create a new user in the database"""
    user.hash_password()
    user_collection.insert_one(user.dict(by_alias=True))

    return user

@router.get("/", response_model=User, response_model_exclude={"password"})
async def get_current_user(current_user: User = Depends(get_current_user)):
    """Retrieve the current user"""
    return current_user

@router.get("/{user_id}", response_model=User, response_model_exclude={"password"})
async def get_user(user_id: str):
    """Retrieve a user from the database by id"""
    user = user_collection.find_one({"_id": user_id})
    return User(**user)

@router.get("/all", response_model=User, response_model_exclude={"password"})
async def get_all_users():
    """Retrieve all users from the database"""
    users = user_collection.find()
    return [User(**user) for user in users]
@router.delete("/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Delete a user from the database by id"""
    print(f"User: {current_user}")
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")

    user_id = ObjectId(user_id)
    user = user_collection.find_one_and_delete({"_id": user_id})
    print(f"User deleted: {user}")
    if user is None:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
