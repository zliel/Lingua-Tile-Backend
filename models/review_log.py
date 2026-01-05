from datetime import datetime, timezone

from bson import ObjectId
from pydantic import BaseModel, Field

from .py_object_id import PyObjectId


class ReviewLog(BaseModel):
    id: PyObjectId | None = Field(alias="_id", default=None)
    lesson_id: PyObjectId = Field(...)
    user_id: PyObjectId = Field(...)
    review_date: datetime = Field(...)
    rating: int = Field(...)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: lambda oid: str(oid),
            datetime: lambda dt: dt.replace(tzinfo=timezone.utc).isoformat()
            if dt.tzinfo is None
            else dt.isoformat(),
        }
        json_schema_extra = {
            "example": {
                "lesson_id": "5f9f1b9b9c9d1c0b8c8b9c9d",
                "user_id": "5f9f1b9b9c9d1c0b8c8b9c9d",
                "review_date": "2023-10-27T10:00:00Z",
                "rating": 4,
            }
        }
