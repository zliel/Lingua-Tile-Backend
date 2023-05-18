import dotenv
from fastapi.encoders import jsonable_encoder

from pymongo import MongoClient
from fastapi import APIRouter, status, HTTPException

from models import PyObjectId
from models.lessons import Lesson
from models.update_lesson import UpdateLesson

router = APIRouter(prefix="/api/lessons", tags=["Lessons"])
mongo_host = dotenv.get_key(".env", "MONGO_HOST")
client = MongoClient(mongo_host)
db = client['lingua-tile']
lesson_collection = db['lessons']
card_collection = db['cards']


@router.get("/all")
async def get_all_lessons():
    """Retrieve all lessons from the database"""
    lessons = lesson_collection.find()
    return [Lesson(**lesson) for lesson in lessons]


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_lesson(lesson: Lesson):
    """Create a new lesson in the database"""
    new_lesson = jsonable_encoder(lesson)

    lesson_collection.insert_one(new_lesson)

    # Update the cards that are in the lesson
    if new_lesson["cards"] is not None:
        for card_id in new_lesson["cards"]:
            card_collection.find_one_and_update({"_id": card_id}, {"$addToSet": {"lesson_id": new_lesson["_id"]}})
    return lesson


@router.get("/{lesson_id}")
async def get_lesson(lesson_id: PyObjectId):
    """Retrieve a lesson from the database by id"""
    lesson = lesson_collection.find_one({"_id": lesson_id})
    return Lesson(**lesson)


@router.put("/update/{lesson_id}")
async def update_lesson(lesson_id: PyObjectId, updated_info: UpdateLesson):
    """Update a lesson in the database by id"""
    lesson_info_to_update = {k: v for k, v in updated_info.dict().items() if v is not None}

    # update a lesson in the database by id and return the old lesson to help with updating the cards
    old_lesson = lesson_collection.find_one_and_update({"_id": lesson_id}, {"$set": lesson_info_to_update})
    if old_lesson is None:
        raise HTTPException(status_code=404, detail=f"Lesson wih id {lesson_id} not found")

    # update a lesson in the database by id
    updated_lesson = lesson_collection.find_one({"_id": lesson_id})

    # if a card was in the old lesson but not the new lesson, remove the lesson id from the card
    if old_lesson["cards"]:
        for card_id in old_lesson["cards"]:
            if card_id not in updated_lesson["cards"]:
                card_collection.find_one_and_update({"_id": card_id}, {"$pull": {"lesson_id": lesson_id}})

    # If the lesson contains cards, update the cards to reflect the new lesson
    if updated_lesson["cards"]:
        for card_id in updated_lesson["cards"]:
            # add the lesson id to the list of lessons the card is associated with
            card_collection.find_one_and_update({"_id": card_id}, {"$addToSet": {"lesson_id": lesson_id}})

    return Lesson(**updated_lesson)


@router.delete("/delete/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(lesson_id: PyObjectId):
    """Delete a lesson from the database by id"""
    lesson_collection.delete_one({"_id": lesson_id})

    # update all cards associated with the lesson to reflect the deletion of the lesson
    card_collection.update_many({"lesson_id": lesson_id}, {"$pull": {"lesson_id": lesson_id}})
