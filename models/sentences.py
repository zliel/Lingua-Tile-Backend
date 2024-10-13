from typing import List

from bson import ObjectId
from pydantic import BaseModel, Field

from .py_object_id import PyObjectId


class Sentence(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    sentence: str = Field(...)
    possible_answers: List[str] = Field(...)
    words: List[str] = Field(...)

    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
        json_encoders = {ObjectId: lambda oid: str(oid)}
        schema_extra = {
            "example": {
                "sentence": "私は学生です",
                "possible_answers": [
                    "I am a student",
                    "I'm a student",
                    "I am a pupil",
                    "I'm a pupil",
                ],
                "words": ["私", "は", "がくせい", "です"],
            }
        }
