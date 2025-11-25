from typing import List, Optional

from bson.objectid import ObjectId
from pydantic import BaseModel, Field

from .py_object_id import PyObjectId


class Card(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=str(ObjectId()))
    front_text: str = Field(...)
    back_text: str = Field(...)
    lesson_ids: List[PyObjectId] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
        validate_by_name = True
        json_encoders = {ObjectId: lambda oid: str(oid)}
        json_schema_extra = {
            "example": {
                "front_text": "Hello",
                "back_text": "こんにちは",
                "lesson_ids": ["5f9f1b9b9c9d1c0b8c8b9c9d"],
            }
        }
