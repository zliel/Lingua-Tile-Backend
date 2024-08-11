from typing import List

from bson.objectid import ObjectId
from pydantic import BaseModel, Field

from models.py_object_id import PyObjectId


class User(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    username: str = Field(...)
    password: str = Field(...)
    roles: List[str] = Field(...)
    completed_lessons: List[str] = Field(...)

    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
        json_encoders = {ObjectId: lambda oid: str(oid)}
        schema_extra = {
            "example": {
                "username": "johndoe",
                "password": "password",
                "roles": ["student"],
                "completed_lessons": ["5f9f1b9b9c9d1c0b8c8b9c9d"]
            },
            "example2": {
                "username": "admindoe",
                "password": "password",
                "roles": ["admin"],
                "completed_lessons": []
            }
        }
