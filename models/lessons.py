from typing import List, Optional

from bson.objectid import ObjectId
from pydantic import BaseModel, Field, validator

from .py_object_id import PyObjectId
from .sentences import Sentence


class Lesson(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    title: str = Field(...)
    section_id: Optional[PyObjectId] = Field(default=None)
    card_ids: Optional[List[PyObjectId]] = Field(default=[])
    content: Optional[str] = Field(default="")  # This will be markdown content
    sentences: Optional[List[Sentence]] = Field(default=[])
    category: str = Field(...)

    @validator("section_id", pre=True, always=True)
    def validate_section_id(cls, v):
        if v == "":
            return None
        return v

    @validator("category", pre=True, always=True)
    def validate_category(cls, v):
        if v.lower() not in ["grammar", "practice", "flashcards"]:
            raise ValueError(
                "Category must be one of 'grammar', 'practice', or 'flashcards'"
            )
        return v.lower()

    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
        json_encoders = {ObjectId: lambda oid: str(oid)}
        schema_extra = {
            "example": {
                "title": "Basic Grammar",
                "section_id": "5f9f1b9b9c9d1c0b8c8b9c9d",
                "card_ids": ["5f9f1b9b9c9d1c0b8c8b9c9d"],
                "content": "#This is some markdown content for a lesson on basic grammar in Japanese #"
                "##This is a subheading"
                "This is some more content",
                "category": "grammar",  # This could be grammar, vocabulary, or kanji
                "sentences": [
                    {
                        "full_sentence": "これはペンです",
                        "possible_answers": ["This is a pen"],
                        "words": ["これ", "は", "ペン", "です"],
                    }
                ],
            }
        }
