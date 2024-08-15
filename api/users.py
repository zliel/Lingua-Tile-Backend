import dotenv
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from passlib.context import CryptContext

from models import User, PyObjectId, UpdateUser

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
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
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
    if user_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already exists")

    user.hash_password()
    user_collection.insert_one(user.dict(by_alias=True))

    return user


@router.get("/", response_model=User, response_model_exclude={"password"})
async def get_current_user(current_user: User = Depends(get_current_user)):
    """Retrieve the current user"""
    if current_user is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return current_user


@router.get("/{user_id}", response_model=User, response_model_exclude={"password"})
async def get_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Retrieve a user from the database by id"""
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user")

    user = user_collection.find_one({"_id": user_id})
    return User(**user)


@router.get("/admin/all", response_model=list[User], response_model_exclude={"password"})
async def get_all_users(current_user: User = Depends(get_current_user)):
    """Retrieve all users from the database"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to view all users")

    users = user_collection.find()
    return [User(**user) for user in users]


@router.put("/update/{user_id}", response_model=User, response_model_exclude={"password"})
async def update_user(user_id: str, updated_info: UpdateUser, current_user: User = Depends(get_current_user)):
    """Update a user in the database by id"""
    user_info_to_update = {k: v for k, v in updated_info.dict().items() if v is not None}

    if "password" in user_info_to_update:
        if user_info_to_update["password"].strip() != "":
            user_info_to_update["password"] = pwd_context.hash(user_info_to_update["password"])
        else:
            del user_info_to_update["password"]
    # update a user in the database by id
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    user_id = ObjectId(user_id)
    old_user = user_collection.find_one_and_update({"_id": user_id}, {"$set": user_info_to_update})
    if old_user is None:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

    updated_user = user_collection.find_one({"_id": user_id})
    return User(**updated_user)


@router.delete("/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Delete a user from the database by id"""
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")

    user_id = ObjectId(user_id)
    user = user_collection.find_one_and_delete({"_id": user_id})

    if user is None:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
