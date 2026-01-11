import jose
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.config import get_settings
from models.users import User
from services.cards import CardService
from services.lessons import LessonService
from services.sections import SectionService
from services.users import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
settings = get_settings()
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM


db_client = None


async def get_db(request: Request):
    """
    Get the database connection from the application state.
    Use request.app.state.mongo_client which is initialized in the lifespan.
    """
    if hasattr(request.app.state, "mongo_client"):
        client = request.app.state.mongo_client
        db: AsyncDatabase = client["lingua-tile"]
        yield db
    else:
        # Fallback for testing or if state is not set
        global db_client
        if db_client is None:
            mongo_host = settings.MONGO_HOST
            db_client = AsyncMongoClient(mongo_host)
        yield db_client["lingua-tile"]


def get_user_service(db=Depends(get_db)) -> UserService:
    return UserService(db)


def get_card_service(db=Depends(get_db)) -> CardService:
    return CardService(db)


def get_section_service(db=Depends(get_db)) -> SectionService:
    return SectionService(db)


def get_lesson_service(db=Depends(get_db)) -> LessonService:
    return LessonService(db)


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
        if user is None:
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )

        return User(**user)

    except jose.exceptions.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        ) from None

    except jose.exceptions.JWTError:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        ) from None


async def get_current_user_optional(
    token: str = Depends(oauth2_scheme_optional), db=Depends(get_db)
) -> User | None:
    if not token:
        return None
    try:
        # Decode the token to get the username
        if not SECRET_KEY:
            return None

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            return None

        user_collection: AsyncCollection = db["users"]
        user = await user_collection.find_one({"username": username})
        if user is None:
            return None

        return User(**user)

    except (jose.exceptions.ExpiredSignatureError, jose.exceptions.JWTError):
        return None


class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)):
        if any(role in user.roles for role in self.allowed_roles):
            return user
        raise HTTPException(status_code=403, detail="Operation not permitted")
