from typing import Optional, List

from pydantic import BaseModel


class UpdateCard(BaseModel):
    front_text: Optional[str] = None
    back_text: Optional[str] = None
    lesson_id: Optional[List[str]] = None

    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "front_text": "Hello",
                "back_text": "こんにちは",
                "lesson_id": ["5f9f1b9b9c9d1c0b8c8b9c9d"]
            }
        }
