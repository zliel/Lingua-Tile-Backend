from typing import List, Optional

from bson.objectid import ObjectId
from pydantic import BaseModel, Field, validator

from .py_object_id import PyObjectId


class Lesson(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    title: str = Field(...)
    section_id: Optional[PyObjectId] = Field(default=None)
    card_ids: List[PyObjectId] = Field(default=[])

    @validator("section_id", pre=True, always=True)
    def validate_section_id(cls, v):
        if v == "":
            return None
        return v

    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
        json_encoders = {ObjectId: lambda oid: str(oid)}
        schema_extra = {
            "example": {
                "title": "Basic Grammar",
                "section_id": "5f9f1b9b9c9d1c0b8c8b9c9d",
                "card_ids": ["5f9f1b9b9c9d1c0b8c8b9c9d"],
            }
        }
