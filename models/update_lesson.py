from typing import Optional, List

from pydantic import BaseModel


# define a pydantic model to update a lesson
class UpdateLesson(BaseModel):
    name: Optional[str] = None
    cards: Optional[List[str]] = None

    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "name": "Hello",
                "cards": ["5f9f1b9b9c9d1c0b8c8b9c9d"]
            }
        }