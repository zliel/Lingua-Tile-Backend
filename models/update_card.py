from typing import Optional, List

from pydantic import BaseModel

from .py_object_id import PyObjectId


class UpdateCard(BaseModel):
    front_text: Optional[str] = None
    back_text: Optional[str] = None
    lesson_ids: Optional[List[PyObjectId]] = None

    class Config:
        arbitrary_types_allowed = True
        validate_by_name = True
        json_schema_extra = {
            "example": {
                "front_text": "Hello",
                "back_text": "こんにちは",
                "lesson_ids": ["5f9f1b9b9c9d1c0b8c8b9c9d"],
            }
        }
