from typing import List, Optional

from bson.objectid import ObjectId
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from .py_object_id import PyObjectId

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    username: str = Field(...)
    password: str = Field(...)
    roles: List[str] = Field(default=["user"])
    completed_lessons: List[PyObjectId] = Field(default=[])

    class Config:
        arbitrary_types_allowed = True
        validate_by_name = True
        json_encoders = {ObjectId: lambda oid: str(oid)}
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "password": "password",
                "roles": ["user"],
                "completed_lessons": ["5f9f1b9b9c9d1c0b8c8b9c9d"],
            },
            "example2": {
                "username": "admindoe",
                "password": "password",
                "roles": ["admin"],
                "completed_lessons": [],
            },
        }

    def hash_password(self):
        self.password = pwd_context.hash(self.password)
