from bson.objectid import ObjectId
from passlib.context import CryptContext
from pydantic import BaseModel

from .py_object_id import PyObjectId

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UpdateUser(BaseModel):
    username: str | None = None
    password: str | None = None
    roles: list[str] | None = None
    completed_lessons: list[PyObjectId] | None = None
    timezone: str | None = None
    learning_mode: str | None = None

    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    def hash_password(self):
        self.password = pwd_context.hash(self.password) if self.password else None
