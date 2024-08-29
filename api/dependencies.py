import jwt
from pymongo import MongoClient
import dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = dotenv.get_key(".env", "SECRET_KEY")
ALGORITHM = "HS256"

def get_db():
    mongo_host = dotenv.get_key(".env", "MONGO_HOST")
    client = MongoClient(mongo_host)
    db = client['lingua-tile']
    return db


def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    try:
        # Decode the token to get the username
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        user_collection = db['users']

        # Find the user in the database by username
        user = user_collection.find_one({"username": username})
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        return User(**user)

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
