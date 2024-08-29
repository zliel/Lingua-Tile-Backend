from typing import List, Optional

from bson.objectid import ObjectId
from passlib.context import CryptContext
from pydantic import BaseModel

from .py_object_id import PyObjectId

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UpdateUser(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    roles: Optional[List[str]] = None
    completed_lessons: Optional[List[PyObjectId]] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    def hash_password(self):
        self.password = pwd_context.hash(self.password)
