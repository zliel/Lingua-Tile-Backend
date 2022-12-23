import dotenv

from pymongo import MongoClient
from fastapi import APIRouter
from models.lessons import Lesson

router = APIRouter(prefix="/api/lessons", tags=["Lessons"])
mongo_host = dotenv.get_key(".env", "MONGO_HOST")
client = MongoClient(mongo_host)
db = client['lingua-tile']
lesson_collection = db['lessons']
card_collection = db['cards']


@router.get("/all", tags=["Lessons"])
async def get_all_lessons():
    """Retrieve all lessons from the database"""
    lessons = lesson_collection.find()
    return [Lesson(**lesson) for lesson in lessons]


@router.post("/create/{name}", tags=["Lessons"])
async def create_lesson(name):
    """Create a new lesson in the database"""
    new_lesson = Lesson(name)
    lesson_collection.insert_one(new_lesson.__dict__)
    return new_lesson


@router.get("/{lesson_id}", tags=["Lessons"])
async def get_lesson(lesson_id):
    """Retrieve a lesson from the database by id"""
    lesson = lesson_collection.find_one({"_id": lesson_id})
    return lesson


@router.put("/update/{lesson_id}", tags=["Lessons"])
async def update_lesson(lesson_id, updated_lesson_info: dict):
    """Update a lesson in the database by id"""
    updated_lesson = lesson_collection.find_one_and_update({"_id": lesson_id}, {"$set": updated_lesson_info})

    # Update all cards associated with the lesson to reflect the new lesson id if it was changed
    if "_id" in updated_lesson_info:
        card_collection.update_many({"lesson_id": lesson_id}, {"$set": {"lesson_id": updated_lesson_info["_id"]}})
    if updated_lesson is None:
        return {"message": "Lesson not found"}
    return updated_lesson


@router.delete("/delete/{lesson_id}", tags=["Lessons"])
async def delete_lesson(lesson_id):
    """Delete a lesson from the database by id"""
    lesson_collection.delete_one({"_id": lesson_id})

    # Delete all cards associated with the lesson
    card_collection.delete_many({"lesson_id": lesson_id})

    return {"message": "Lesson deleted"}
