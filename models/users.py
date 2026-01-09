from datetime import datetime

from bson.objectid import ObjectId
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from .py_object_id import PyObjectId

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict
    expirationTime: float | None = None
    user_id: PyObjectId | None = Field(alias="user_id", default=None)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: lambda oid: str(oid)}


class PushUnsubscribe(BaseModel):
    endpoint: str


class User(BaseModel):
    id: PyObjectId | None = Field(alias="_id", default=None)
    username: str = Field(...)
    email: str = Field(...)
    password: str | None = Field(default=None)
    reset_token: str | None = Field(default=None)
    reset_token_expires: datetime | None = Field(default=None)
    auth_provider: str | None = Field(default=None)
    roles: list[str] = Field(default=["user"])
    completed_lessons: list[PyObjectId] = Field(default=[])
    push_subscriptions: list[PushSubscription] = Field(default=[])
    current_streak: int = Field(default=0)
    last_activity_date: datetime | None = Field(default=None)
    timezone: str = Field(default="UTC")
    level: int = Field(default=1)
    xp: int = Field(default=0)
    learning_mode: str = Field(default="map")  # "map" or "list"

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
        self.password = pwd_context.hash(self.password if self.password else "")
