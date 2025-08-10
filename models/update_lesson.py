from typing import Optional, List

from pydantic import BaseModel, field_validator

from .py_object_id import PyObjectId


# define a pydantic model to update a lesson
class UpdateLesson(BaseModel):
    title: Optional[str] = None
    section_id: Optional[PyObjectId] = None
    category: Optional[str] = None
    content: Optional[str] = None
    sentences: Optional[List[dict]] = None
    card_ids: Optional[List[PyObjectId]] = None

    @field_validator("section_id")
    def validate_section_id(cls, v):
        if v == "":
            return None
        return v

    class Config:
        arbitrary_types_allowed = True
        validate_by_name = True
        json_schema_extra = {
            "example": {
                "title": "Hello",
                "section_id": "5f9f1b9b9c9d1c0b8c8b9c9d",
                "category": "grammar",
                "content": "# This is a lesson on basic grammar in Japanese in markdown format",
                "card_ids": [],
                "sentences": [],
            }
        }
