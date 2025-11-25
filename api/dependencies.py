import os

import jose
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext
from pymongo import AsyncMongoClient, MongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from models import User

load_dotenv(".env")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"


def get_db():
    mongo_host = os.getenv("MONGO_HOST")
    client = AsyncMongoClient(mongo_host)
    db: AsyncDatabase = client["lingua-tile"]
    return db


async def get_current_user(
    token: str = Depends(oauth2_scheme), db=Depends(get_db)
) -> User:
    try:
        # Decode the token to get the username
        if not SECRET_KEY:
            raise HTTPException(status_code=500, detail="Server configuration error")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )

        user_collection: AsyncCollection = db["users"]

        # Find the user in the database by username
        user = await user_collection.find_one({"username": username})
        print(f"Found user: {user}")
        if user is None:
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )

        return User(**user)

    except jose.exceptions.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )
    except jose.exceptions.JWTError:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )
