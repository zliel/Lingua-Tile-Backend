from typing import List
from bson.objectid import ObjectId
from pydantic import BaseModel, Field
from models.py_object_id import PyObjectId


class Lesson(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(...)
    cards: List[str] = Field(default_factory=list)
    title: str = Field(...)
    card_ids: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
        json_encoders = {ObjectId: lambda oid: str(oid)}
        schema_extra = {
            "example": {
                "name": "Greetings in Japanese",
                "cards": ["5f9f1b9b9c9d1c0b8c8b9c9d"]
                "title": "Basic Grammar",
                "card_ids": ["5f9f1b9b9c9d1c0b8c8b9c9d"]
            }
        }
