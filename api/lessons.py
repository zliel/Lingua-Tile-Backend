from typing import List

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import Depends, APIRouter, status, HTTPException, Request

from api.dependencies import get_current_user, get_db
from models import PyObjectId, User
from models.lesson_review import LessonReview
from models.lessons import Lesson
from models.sentences import Sentence
from models.update_lesson import UpdateLesson

load_dotenv(".env")
router = APIRouter(prefix="/api/lessons", tags=["Lessons"])


@router.get("/all", response_model=List[Lesson], status_code=status.HTTP_200_OK)
async def get_all_lessons(db=Depends(get_db)):
    """Retrieve all lessons from the database"""
    lessons = await db["lessons"].find().sort("order_index", 1).to_list()
    return [Lesson(**lesson) for lesson in lessons]


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_lesson(lesson: Lesson, db=Depends(get_db)):
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

    result = await db["lessons"].insert_one(
        lesson.model_dump(by_alias=True, exclude={"id"})
    )
    new_lesson = await db["lessons"].find_one({"_id": ObjectId(result.inserted_id)})
    # Update the cards that are in the lesson
    if new_lesson and new_lesson["card_ids"]:
        card_object_ids = [ObjectId(card_id) for card_id in new_lesson["card_ids"]]
        await db["cards"].update_many(
            {"_id": {"$in": card_object_ids}},
            {"$addToSet": {"lesson_ids": new_lesson["_id"]}},
        )

    if new_lesson and new_lesson["section_id"]:
        await db["sections"].update_one(
            {"_id": ObjectId(new_lesson["section_id"])},
            {"$addToSet": {"lesson_ids": new_lesson["_id"]}},
        )
    return lesson


@router.get("/by-category/{category}")
async def get_lessons_by_category(category: str, db=Depends(get_db)):
    """Retrieve all lessons from the database by category"""
    if category.lower() not in ["grammar", "vocabulary", "kanji"]:
        raise HTTPException(
            status_code=400,
            detail="Category must be one of 'grammar', 'vocabulary', or 'kanji'",
        )
    lessons = (
        (
            await db["lessons"].find(
                {"category": {"$regex": f"^{category}", "$options": "i"}}
            )
        )
        .sort("order_index", 1)
        .to_list()
    )

    return [Lesson(**lesson) for lesson in lessons]


@router.get("/review/{lesson_id}", status_code=status.HTTP_200_OK)
async def get_lesson_review(
    lesson_id: PyObjectId,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Retrieve a lesson review from the database by lesson id for the current user"""
    user_id = current_user.id
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    lesson_review = await db["lesson_reviews"].find_one(
        {"lesson_id": lesson_id, "user_id": user_id}
    )

    if not lesson_review:
        return None

    return LessonReview(**lesson_review)


@router.get("/reviews", status_code=status.HTTP_200_OK)
async def get_lesson_reviews(
    current_user: User = Depends(get_current_user), db=Depends(get_db)
):
    """Retrieve all lesson reviews from the database"""
    user_id = current_user.id
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    lesson_reviews = await db["lesson_reviews"].find({"user_id": user_id}).to_list()
    if not lesson_reviews:
        return []
    return [LessonReview(**review) for review in lesson_reviews]


@router.get("/{lesson_id}")
async def get_lesson(lesson_id: PyObjectId, db=Depends(get_db)):
    """Retrieve a lesson from the database by id"""
    lesson = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
    return (
        Lesson(**lesson)
        if lesson
        else HTTPException(
            status_code=404, detail=f"Lesson with id {lesson_id} not found"
        )
    )


@router.put("/update/{lesson_id}")
async def update_lesson(
    lesson_id: PyObjectId, updated_info: UpdateLesson, db=Depends(get_db)
):
    """Update a lesson in the database by id"""
    lesson_info_to_update = {
        k: v for k, v in updated_info.model_dump().items() if v is not None
    }
    if not updated_info.section_id:
        lesson_info_to_update["section_id"] = None

    # update a lesson in the database by id and return the old lesson to help with updating the cards
    old_lesson = await db["lessons"].find_one_and_update(
        {"_id": ObjectId(lesson_id)}, {"$set": lesson_info_to_update}
    )
    if old_lesson is None:
        raise HTTPException(
            status_code=404, detail=f"Lesson wih id {lesson_id} not found"
        )

    # update a lesson in the database by id
    updated_lesson = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
    if updated_lesson is None:
        raise HTTPException(
            status_code=404, detail=f"Lesson with id {lesson_id} failed to update"
        )

    # if cards were in the old lesson but not the new lesson, remove the lesson id from them
    if old_lesson["card_ids"]:
        cards_to_remove = set(old_lesson["card_ids"]) - set(updated_lesson["card_ids"])
        if cards_to_remove:
            await db["cards"].update_many(
                {"_id": {"$in": [ObjectId(card_id) for card_id in cards_to_remove]}},
                {"$pull": {"lesson_ids": lesson_id}},
            )

    # If the lesson contains cards, update the cards to reflect the new lesson
    if updated_lesson["card_ids"]:
        current_card_ids = [ObjectId(card_id) for card_id in updated_lesson["card_ids"]]
        await db["cards"].update_many(
            {"_id": {"$in": current_card_ids}},
            {"$addToSet": {"lesson_ids": lesson_id}},
        )

    # handle updates to the section_id fields
    if (
        old_lesson.__contains__("section_id")
        and old_lesson["section_id"] != updated_lesson["section_id"]
    ):
        # remove the lesson id from the old section
        await db["sections"].update_one(
            {"_id": ObjectId(old_lesson["section_id"])},
            {"$pull": {"lesson_ids": lesson_id}},
        )
        # add the lesson id to the new section
        await db["sections"].update_one(
            {"_id": ObjectId(updated_lesson["section_id"])},
            {"$addToSet": {"lesson_ids": lesson_id}},
        )
    elif not old_lesson.__contains__("section_id"):
        await db["sections"].update_one(
            {"_id": ObjectId(updated_lesson["section_id"])},
            {"$addToSet": {"lesson_ids": lesson_id}},
        )

    return Lesson(**updated_lesson)


@router.delete("/delete/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(lesson_id: PyObjectId, db=Depends(get_db)):
    """Delete a lesson from the database by id"""
    await db["lessons"].delete_one({"_id": ObjectId(lesson_id)})

    # update all cards associated with the lesson to reflect the deletion of the lesson
    await db["cards"].update_many(
        {"lesson_ids": ObjectId(lesson_id)},
        {"$pull": {"lesson_ids": lesson_id}},
    )

    await db["sections"].update_one(
        {"lesson_ids": ObjectId(lesson_id)},
        {"$pull": {"lesson_ids": lesson_id}},
    )


# Lesson Review Routes
@router.post("/review", status_code=status.HTTP_200_OK)
async def review_lesson(
    request: Request, current_user: User = Depends(get_current_user), db=Depends(get_db)
):
    # Access the "lesson_id" and "user_id" from the request body
    body = await request.json()
    lesson_id = body["lesson_id"]
    user_id = current_user.id or ""
    overall_performance = body["overall_performance"]

    lesson: Lesson | None = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
    if not lesson:
        raise HTTPException(
            status_code=404, detail=f"Lesson with id {lesson_id} not found"
        )

    user: User | None = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

    lesson_review = await db["lesson_reviews"].find_one(
        {"lesson_id": lesson_id, "user_id": user_id}
    )

    # If the lesson review does not exist, create a new one
    if not lesson_review:
        lesson_review = LessonReview(lesson_id=lesson_id, user_id=user_id)
        lesson_review.review(overall_performance)
        await db["lesson_reviews"].insert_one(
            lesson_review.model_dump(by_alias=True, exclude={"id"})
        )

    else:  # Otherwise update the existing one
        lesson_review = LessonReview(**lesson_review)
        lesson_review.review(overall_performance)
        await db["lesson_reviews"].find_one_and_update(
            {
                "lesson_id": lesson_id,
                "user_id": user_id,
            },
            {
                "$set": {
                    k: v for k, v in lesson_review.model_dump().items() if k != "_id"
                }
            },
        )
