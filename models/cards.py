from bson.objectid import ObjectId
from pydantic import BaseModel, Field

from models.PyObjectId import PyObjectId


class Card(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    front_text: str = Field(...)
    back_text: str = Field(...)
    lesson_id: str = Field(...)

    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
        json_encoders = {ObjectId: lambda oid: str(oid)}
        schema_extra = {
            "example": {
                "front_text": "Hello",
                "back_text": "こんにちは",
                "lesson_id": "5f9f1b9b9c9d1c0b8c8b9c9d"
            }
        }
