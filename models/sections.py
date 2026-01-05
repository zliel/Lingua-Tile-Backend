from bson.objectid import ObjectId
from pydantic import BaseModel, Field

from .py_object_id import PyObjectId


class Section(BaseModel):
    id: PyObjectId | None = Field(alias="_id", default=None)
    name: str = Field(...)
    lesson_ids: list[PyObjectId] = Field(default_factory=list)
    order_index: int = Field(default=0)

    class Config:
        arbitrary_types_allowed = True
        validate_by_name = True
        json_encoders = {ObjectId: lambda oid: str(oid)}
        json_schema_extra = {
            "example": {"name": "Kana", "lesson_ids": ["5f9f1b9b9c9d1c0b8c8b9c9d"]}
        }
