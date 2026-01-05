from bson.objectid import ObjectId
from pydantic import BaseModel, Field, field_validator

from .py_object_id import PyObjectId
from .sentences import Sentence


class Lesson(BaseModel):
    id: PyObjectId | None = Field(alias="_id", default=None)
    title: str = Field(...)
    section_id: PyObjectId | None = Field(default=None)
    order_index: int = Field(default=0)
    card_ids: list[PyObjectId] | None = Field(default=[])
    content: str | None = Field(default="")  # This will be markdown content
    sentences: list[Sentence] | None = Field(default=[])
    category: str = Field(...)

    @field_validator("section_id")
    def validate_section_id(cls, v):
        if v == "":
            return None
        return v

    @field_validator("category")
    def validate_category(cls, v):
        if v.lower() not in ["grammar", "practice", "flashcards"]:
            raise ValueError(
                "Category must be one of 'grammar', 'practice', or 'flashcards'"
            )
        return v.lower()

    class Config:
        arbitrary_types_allowed = True
        validate_by_name = True
        json_encoders = {ObjectId: lambda oid: str(oid)}
        json_schema_extra = {
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
