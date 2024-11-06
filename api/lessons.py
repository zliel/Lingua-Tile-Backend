import os
from typing import List

from dotenv import load_dotenv
from fastapi import APIRouter, status, HTTPException, Request
from pymongo import MongoClient

from models import PyObjectId
from models.lesson_review import LessonReview
from models.lessons import Lesson
from models.sentences import Sentence
from models.update_lesson import UpdateLesson

load_dotenv(".env")
router = APIRouter(prefix="/api/lessons", tags=["Lessons"])
mongo_host = os.getenv("MONGO_HOST")
client = MongoClient(mongo_host)
db = client["lingua-tile"]
lesson_collection = db["lessons"]
card_collection = db["cards"]
section_collection = db["sections"]
user_collection = db["users"]
lesson_review_collection = db["lesson_reviews"]


@router.get("/all", response_model=List[Lesson], status_code=status.HTTP_200_OK)
async def get_all_lessons():
    """Retrieve all lessons from the database"""
    lessons = lesson_collection.find()

    return [Lesson(**lesson) for lesson in lessons]


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_lesson(lesson: Lesson):
    """Create a new lesson in the database"""
    # Ensure the category is title case
    lesson.category = lesson.category.title()

    # Convert the JSON sentences to Sentence objects
    if lesson.sentences is not None:
        lesson.sentences = [
            Sentence.create(
                full_sentence=sentence.full_sentence,
                possible_answers=sentence.possible_answers,
            )
            for sentence in lesson.sentences
        ]

    lesson_collection.insert_one(lesson.dict(by_alias=True))
    new_lesson = lesson_collection.find_one({"_id": lesson.id})
    # Update the cards that are in the lesson
    if new_lesson["card_ids"] is not None:
        for card_id in new_lesson["card_ids"]:
            card_collection.find_one_and_update(
                {"_id": card_id}, {"$addToSet": {"lesson_id": new_lesson["_id"]}}
            )

    if new_lesson["section_id"] is not None:
        section_collection.find_one_and_update(
            {"_id": new_lesson["section_id"]},
            {"$addToSet": {"lesson_ids": new_lesson["_id"]}},
        )
    return lesson


@router.get("/by-category/{category}")
async def get_lessons_by_category(category: str):
    """Retrieve all lessons from the database by category"""
    if category.lower() not in ["grammar", "vocabulary", "kanji"]:
        raise HTTPException(
            status_code=400,
            detail="Category must be one of 'grammar', 'vocabulary', or 'kanji'",
        )
    lessons = lesson_collection.find(
        {"category": {"$regex": f"^{category}", "$options": "i"}}
    )

    return [Lesson(**lesson) for lesson in lessons] or HTTPException(
        status_code=404, detail=f"No lessons found for category {category}"
    )


@router.get("/{lesson_id}")
async def get_lesson(lesson_id: PyObjectId):
    """Retrieve a lesson from the database by id"""
    lesson = lesson_collection.find_one({"_id": lesson_id})
    return Lesson(**lesson)


@router.put("/update/{lesson_id}")
async def update_lesson(lesson_id: PyObjectId, updated_info: UpdateLesson):
    """Update a lesson in the database by id"""
    lesson_info_to_update = {
        k: v for k, v in updated_info.dict().items() if v is not None
    }
    if not updated_info.section_id:
        lesson_info_to_update["section_id"] = None

    # update a lesson in the database by id and return the old lesson to help with updating the cards
    old_lesson = lesson_collection.find_one_and_update(
        {"_id": lesson_id}, {"$set": lesson_info_to_update}
    )
    if old_lesson is None:
        raise HTTPException(
            status_code=404, detail=f"Lesson wih id {lesson_id} not found"
        )

    # update a lesson in the database by id
    updated_lesson = lesson_collection.find_one({"_id": lesson_id})

    # if a card was in the old lesson but not the new lesson, remove the lesson id from the card
    if old_lesson["card_ids"]:
        for card_id in old_lesson["card_ids"]:
            if card_id not in updated_lesson["card_ids"]:
                card_collection.find_one_and_update(
                    {"_id": card_id}, {"$pull": {"lesson_ids": lesson_id}}
                )

    # If the lesson contains cards, update the cards to reflect the new lesson
    if updated_lesson["card_ids"]:
        for card_id in updated_lesson["card_ids"]:
            # add the lesson id to the list of lessons the card is associated with
            card_collection.find_one_and_update(
                {"_id": card_id}, {"$addToSet": {"lesson_ids": lesson_id}}
            )

    # handle updates to the section_id fields
    if old_lesson["section_id"] != updated_lesson["section_id"]:
        # remove the lesson id from the old section
        section_collection.find_one_and_update(
            {"_id": old_lesson["section_id"]}, {"$pull": {"lesson_ids": lesson_id}}
        )
        # add the lesson id to the new section
        section_collection.find_one_and_update(
            {"_id": updated_lesson["section_id"]},
            {"$addToSet": {"lesson_ids": lesson_id}},
        )

    return Lesson(**updated_lesson)


@router.delete("/delete/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(lesson_id: PyObjectId):
    """Delete a lesson from the database by id"""
    lesson_collection.delete_one({"_id": lesson_id})

    # update all cards associated with the lesson to reflect the deletion of the lesson
    card_collection.update_many(
        {"lesson_ids": lesson_id}, {"$pull": {"lesson_ids": lesson_id}}
    )

    section_collection.update_one(
        {"lesson_ids": lesson_id}, {"$pull": {"lesson_ids": lesson_id}}
    )


# Lesson Review Routes
@router.post("/review", status_code=status.HTTP_200_OK)
async def review_lesson(request: Request):
    # Access the "lesson_id" and "user_id" from the request body
    body = await request.json()
    lesson_id = body["lesson_id"]
    user_id = body["user_id"]
    overall_performance = body["overall_performance"]

    lesson = lesson_collection.find_one({"_id": PyObjectId(lesson_id)})
    if not lesson:
        raise HTTPException(
            status_code=404, detail=f"Lesson with id {lesson_id} not found"
        )

    user = user_collection.find_one({"_id": PyObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
    lesson_review = lesson_review_collection.find_one(
        {"lesson_id": lesson["_id"], "user_id": user["_id"]}
    )

    # If the lesson review does not exist, create a new one
    if not lesson_review:
        lesson_review = LessonReview(lesson_id=lesson["_id"], user_id=user["_id"])
        lesson_review.review(overall_performance)
        lesson_review_collection.insert_one(lesson_review.dict(by_alias=True))

    else:  # Otherwise update the existing one
        lesson_review = LessonReview(**lesson_review)
        lesson_review.review(overall_performance)
        lesson_review_collection.find_one_and_update(
            {
                "lesson_id": lesson["_id"],
                "user_id": user["_id"],
            },
            {"$set": lesson_review.dict(by_alias=True)},
        )
