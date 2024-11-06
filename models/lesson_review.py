from datetime import datetime, timezone, timedelta
from sched import scheduler

from fsrs import FSRS, Card, Rating
from pydantic import BaseModel, Field, validator
from typing_extensions import override

from .py_object_id import PyObjectId  # Assuming this is defined elsewhere


# OKAY, so the review setup works now, now I need to figure out storing it in the database and make
# sure it works with a predefined lesson's next_review field

fsrs_scheduler = FSRS()


class LessonReview(BaseModel):
    lesson_id: PyObjectId = Field(...)
    user_id: PyObjectId = Field(...)

    card_object: dict = Field(default_factory=Card().to_dict)
    next_review: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=1)
    )  # Set initial due date

    @validator("lesson_id")
    def validate_lesson_id(cls, v):
        # You can add validation logic here if needed
        return v

    def review(self, overall_performance: float):
        """Review the lesson card and update its schedule based on overall performance."""
        rating = Rating.Again  # Default rating
        if overall_performance > 0.8:  # Adjust threshold as needed
            rating = Rating.Easy
        elif overall_performance > 0.6:
            rating = Rating.Good
        elif overall_performance > 0.4:
            rating = Rating.Hard
        else:
            rating = Rating.Again

        # Convert the card dictionary from db to a Card object
        self.card_object: Card = Card.from_dict(self.card_object)
        self.card_object: Card = fsrs_scheduler.review_card(
            self.card_object, rating, datetime.now(timezone.utc)
        )[0]

        # Update the next review date
        self.next_review = self.card_object.due

        # Convert the card object back to a dictionary
        self.card_object: dict = self.card_object.to_dict()

        return self.next_review

    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "lesson_id": "5f9f1b9b9c9d1c0b8c8b9c9d",
                "rating": "Rating.Again",
                "next_review": datetime.now(timezone.utc),
            }
        }
