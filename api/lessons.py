import random
import re
from datetime import datetime, timezone

from aiocache import SimpleMemoryCache, cached, caches
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.dependencies import (
    RoleChecker,
    get_current_user,
    get_current_user_optional,
    get_db,
)
from app.limiter import limiter
from models.lesson_review import LessonReview
from models.lessons import Lesson
from models.py_object_id import PyObjectId
from models.review_log import ReviewLog
from models.sentences import Sentence
from models.update_lesson import UpdateLesson
from models.users import User
from utils.streaks import update_user_streak
from utils.xp import add_xp_to_user

load_dotenv(".env")
router = APIRouter(prefix="/api/lessons", tags=["Lessons"])


@router.get("/all", response_model=list[Lesson], status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
@cached(ttl=600, key="all_lessons", alias="default")
async def get_all_lessons(request: Request, db=Depends(get_db)):
    """Retrieve all lessons from the database"""
    lessons = await db["lessons"].find().sort("order_index", 1).to_list()
    # return [Lesson(**lesson) for lesson in lessons]
    return lessons


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("5/minute")
async def create_lesson(request: Request, lesson: Lesson, db=Depends(get_db)):
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

    # Invalidate cache
    cache: SimpleMemoryCache = caches.get("default")
    await cache.delete(key="all_lessons")
    await cache.delete(key=f"category_{lesson.category.lower()}")

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


@router.get("/total", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_total_lesson_count(request: Request, db=Depends(get_db)):
    """Retrieve the total number of lessons in the database"""
    total_lessons = await db["lessons"].count_documents({})
    return {"total": total_lessons}


@router.get("/by-category/{category}")
@limiter.limit("10/minute")
@cached(
    ttl=600,
    key_builder=lambda f, *args, **kwargs: f"category_{kwargs['category'].lower()}",
    alias="default",
)
async def get_lessons_by_category(request: Request, category: str, db=Depends(get_db)):
    """Retrieve all lessons from the database by category"""
    if category.lower() not in ["grammar", "flashcards", "practice"]:
        raise HTTPException(
            status_code=400,
            detail="Category must be one of 'grammar', 'flashcards', or 'practice'",
        )
    lessons = (
        await db["lessons"]
        .find({"category": {"$regex": f"^{category}", "$options": "i"}})
        .sort("order_index", 1)
        .to_list()
    )

    return [Lesson(**lesson) for lesson in lessons]


@router.get("/review/{lesson_id}", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_lesson_review(
    request: Request,
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
@limiter.limit("10/minute")
async def get_lesson_reviews(
    request: Request, current_user: User = Depends(get_current_user), db=Depends(get_db)
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
@limiter.limit("10/minute")
async def get_lesson(
    request: Request,
    lesson_id: PyObjectId,
    current_user: User | None = Depends(get_current_user_optional),
    db=Depends(get_db),
):
    """Retrieve a lesson from the database by id"""
    lesson = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
    if not lesson:
        raise HTTPException(
            status_code=404, detail=f"Lesson with id {lesson_id} not found"
        )

    # Scramble and Reverse Logic if user has already reviewed the lesson
    if current_user:
        user_id = current_user.id
        lesson_review = await db["lesson_reviews"].find_one(
            {"lesson_id": lesson_id, "user_id": user_id}
        )

        if lesson_review:
            random.shuffle(lesson["sentences"])

            processed_sentences = []
            for sentence_dict in lesson["sentences"]:
                if (
                    random.random() > 0.5
                    and sentence_dict.get("possible_answers")
                    and len(sentence_dict["possible_answers"]) > 0
                ):
                    # Create reversed sentence structure
                    original_japanese = sentence_dict["full_sentence"]
                    english_prompt = sentence_dict["possible_answers"][0]
                    words = sentence_dict.get("words", [])

                    # Clean words by removing furigana (e.g. "学生(がくせい)" -> "学生")
                    clean_words = [re.sub(r"\(.*?\)", "", w) for w in words]

                    # Spaced with Furigana (for Word Bank display)
                    # Unspaced (for Validation/Keyboard)
                    spaced_japanese = " ".join(words) if words else original_japanese
                    unspaced_japanese = (
                        "".join(clean_words)
                        if clean_words
                        else original_japanese.replace(" ", "")
                    )

                    # Ensure we have at least one spaced version for Word Bank splitting and one clean version for checking
                    new_answers = [spaced_japanese, unspaced_japanese]
                    sentence_dict["full_sentence"] = english_prompt
                    sentence_dict["possible_answers"] = new_answers

                processed_sentences.append(sentence_dict)

            lesson["sentences"] = processed_sentences

    return Lesson(**lesson)


@router.put("/update/{lesson_id}", dependencies=[Depends(RoleChecker(["admin"]))])
@limiter.limit("10/minute")
async def update_lesson(
    request: Request,
    lesson_id: PyObjectId,
    updated_info: UpdateLesson,
    db=Depends(get_db),
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

    # Invalidate cache
    cache: SimpleMemoryCache = caches.get("default")
    await cache.delete(key="all_lessons")
    if old_lesson.get("category"):
        await cache.delete(key=f"category_{old_lesson['category'].lower()}")

    # update a lesson in the database by id
    updated_lesson = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
    if updated_lesson is None:
        raise HTTPException(
            status_code=404, detail=f"Lesson with id {lesson_id} failed to update"
        )

    # Invalidate new category cache if changed
    if updated_lesson.get("category") and updated_lesson.get(
        "category"
    ) != old_lesson.get("category"):
        await cache.delete(key=f"category_{updated_lesson['category'].lower()}")

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


@router.delete(
    "/delete/{lesson_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("5/minute")
async def delete_lesson(request: Request, lesson_id: PyObjectId, db=Depends(get_db)):
    """Delete a lesson from the database by id"""

    # Fetch lesson first to get category for cache invalidation
    lesson = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})

    await db["lessons"].delete_one({"_id": ObjectId(lesson_id)})

    # Invalidate cache
    cache: SimpleMemoryCache = caches.get("default")
    await cache.delete(key="all_lessons")
    if lesson and lesson.get("category"):
        await cache.delete(key=f"category_{lesson['category'].lower()}")

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
@limiter.limit("5/minute")
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

    review_log = ReviewLog(
        lesson_id=lesson_id,
        user_id=user_id,
        review_date=datetime.now(timezone.utc),
        rating=overall_performance,
    )
    await db["review_logs"].insert_one(
        review_log.model_dump(by_alias=True, exclude={"id"})
    )

    update_user_streak(current_user)

    xp_to_add = 10
    is_first_completion = False

    # Check if lesson is already completed
    if lesson_id in current_user.completed_lessons:
        # Already completed, repeat review awards 5 XP
        xp_to_add = 5
    else:
        # First time completion
        is_first_completion = True
        if lesson:
            category = lesson.get("category", "").lower()
            if category == "grammar":
                xp_to_add = 20
            elif category == "practice":
                xp_to_add = 15
            elif category == "flashcards":
                xp_to_add = 10

    new_xp, new_level, leveled_up = add_xp_to_user(
        current_user.xp, current_user.level, xp_to_add
    )

    update_fields = {
        "current_streak": current_user.current_streak,
        "last_activity_date": current_user.last_activity_date,
        "xp": new_xp,
        "level": new_level,
    }

    # If first completion, add to completed_lessons
    if is_first_completion:
        update_operation = {
            "$set": update_fields,
            "$addToSet": {"completed_lessons": lesson_id},
        }
    else:
        update_operation = {"$set": update_fields}

    await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        update_operation,
    )

    return {
        "message": "Review submitted successfully",
        "xp_gained": xp_to_add,
        "new_level": new_level,
        "new_xp": new_xp,
        "leveled_up": leveled_up,
    }


@router.get("/reviews/history/all", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_review_history(
    request: Request, current_user: User = Depends(get_current_user), db=Depends(get_db)
):
    """Retrieve all review logs for the current user to show history"""
    user_id = current_user.id
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    logs = (
        await db["review_logs"]
        .find({"user_id": user_id})
        .sort("review_date", -1)
        .to_list()
    )

    return [ReviewLog(**log) for log in logs]
