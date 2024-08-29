from typing import Optional, List

from pydantic import BaseModel, validator

from .py_object_id import PyObjectId


# define a pydantic model to update a lesson
class UpdateLesson(BaseModel):
    title: Optional[str] = None
    section_id: Optional[PyObjectId] = None
    card_ids: Optional[List[PyObjectId]] = None

    @validator("section_id", pre=True, always=True)
    def validate_section_id(cls, v):
        if v == "":
            return None
        return v

    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "title": "Hello",
                "section_id": "5f9f1b9b9c9d1c0b8c8b9c9d",
                "card_ids": ["5f9f1b9b9c9d1c0b8c8b9c9d"],
            }
        }
