from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fsrs import Card, Rating, Scheduler
from pydantic import BaseModel, Field, field_validator, field_serializer

from .py_object_id import PyObjectId  # Assuming this is defined elsewhere

# Initialize the scheduler
fsrs_scheduler = Scheduler()


class LessonReview(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    lesson_id: PyObjectId = Field(...)
    user_id: PyObjectId = Field(...)

    card_object: dict = Field(default_factory=Card().to_dict)
    next_review: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=1)
    )  # Set initial due date

    # @field_validator("lesson_id", "user_id", mode="before")
    # def validate_lesson_id(cls, v):
    #     if isinstance(v, str):
    #         if not ObjectId.is_valid(v):
    #             raise ValueError("Invalid lesson_id or user_id ObjectId")
    #         return ObjectId(v)
    #     return v
    #
    # @field_serializer("id", "lesson_id", "user_id")
    # def field_serializer(self, v):
    #     return str(v) if v is not None else None

    def review(self, overall_performance: float):
        """Review the lesson card and update its schedule based on overall performance."""
        rating = Rating.Again  # Default rating
        # TODO: Switch to a switch statement
        if overall_performance > 0.8:  # Adjust threshold as needed
            rating = Rating.Easy
        elif overall_performance > 0.6:
            rating = Rating.Good
        elif overall_performance > 0.4:
            rating = Rating.Hard
        else:
            rating = Rating.Again

        # Convert the card dictionary from db to a Card object
        card = Card.from_dict(self.card_object)
        reviewed_card: Card = fsrs_scheduler.review_card(
            card, rating, datetime.now(timezone.utc)
        )[0]

        # Update the next review date
        self.next_review = reviewed_card.due

        # Convert the card object back to a dictionary
        self.card_object: dict = reviewed_card.to_dict()

        return self.next_review

    class Config:
        arbitrary_types_allowed = True
        validate_by_name = True
        json_encoders = {ObjectId: lambda oid: str(oid)}
        json_schema_extra = {
            "example": {
                "lesson_id": "5f9f1b9b9c9d1c0b8c8b9c9d",
                "rating": "Rating.Again",
                "card_object": Card().to_dict(),
                "next_review": datetime.now(timezone.utc),
            }
        }
