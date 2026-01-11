import random
import re
from datetime import datetime, timezone

from aiocache import caches
from bson import ObjectId
from fastapi import HTTPException
from pymongo.asynchronous.collection import AsyncCollection

from models.lesson_review import LessonReview
from models.lessons import Lesson
from models.review_log import ReviewLog
from models.sentences import Sentence
from models.update_lesson import UpdateLesson
from models.users import User
from services.base import BaseService
from utils.streaks import update_user_streak
from utils.xp import add_xp_to_user


class LessonService(BaseService):
    @property
    def collection(self) -> AsyncCollection:
        return self.db["lessons"]

    @property
    def review_collection(self) -> AsyncCollection:
        return self.db["lesson_reviews"]

    @property
    def log_collection(self) -> AsyncCollection:
        return self.db["review_logs"]

    @property
    def user_collection(self) -> AsyncCollection:
        return self.db["users"]

    @property
    def card_collection(self) -> AsyncCollection:
        return self.db["cards"]

    @property
    def section_collection(self) -> AsyncCollection:
        return self.db["sections"]

    async def _invalidate_cache(self, keys: list[str] | None = None):
        cache = caches.get("default")
        await cache.delete(key="all_lessons")
        if keys:
            for key in keys:
                await cache.delete(key=key)

    async def get_all_lessons(self) -> list[Lesson]:
        lessons = (
            await self.collection.find().sort("order_index", 1).to_list(length=None)
        )
        return [Lesson(**lesson) for lesson in lessons]

    async def create_lesson(self, lesson: Lesson) -> Lesson:
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

        result = await self.collection.insert_one(
            lesson.model_dump(by_alias=True, exclude={"id"})
        )
        new_lesson = await self.collection.find_one(
            {"_id": ObjectId(result.inserted_id)}
        )

        await self._invalidate_cache(keys=[f"category_{lesson.category.lower()}"])

        if new_lesson and new_lesson.get("card_ids"):
            card_object_ids = [ObjectId(card_id) for card_id in new_lesson["card_ids"]]
            await self.card_collection.update_many(
                {"_id": {"$in": card_object_ids}},
                {"$addToSet": {"lesson_ids": new_lesson["_id"]}},
            )

        if new_lesson and new_lesson.get("section_id"):
            await self.section_collection.update_one(
                {"_id": ObjectId(new_lesson["section_id"])},
                {"$addToSet": {"lesson_ids": new_lesson["_id"]}},
            )

        return Lesson(**new_lesson)

    async def get_total_lesson_count(self) -> dict:
        total_lessons = await self.collection.count_documents({})
        return {"total": total_lessons}

    async def get_lessons_by_category(self, category: str) -> list[Lesson]:
        if category.lower() not in ["grammar", "flashcards", "practice"]:
            raise HTTPException(
                status_code=400,
                detail="Category must be one of 'grammar', 'flashcards', or 'practice'",
            )
        lessons = (
            await self.collection.find(
                {"category": {"$regex": f"^{category}", "$options": "i"}}
            )
            .sort("order_index", 1)
            .to_list(length=None)
        )

        return [Lesson(**lesson) for lesson in lessons]

    async def get_lesson_review(
        self, lesson_id: str, user_id: str
    ) -> LessonReview | None:
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        lesson_review = await self.review_collection.find_one(
            {"lesson_id": lesson_id, "user_id": user_id}
        )

        if not lesson_review:
            return None

        return LessonReview(**lesson_review)

    async def get_all_reviews_for_user(self, user_id: str) -> list[LessonReview]:
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        lesson_reviews = await self.review_collection.find(
            {"user_id": user_id}
        ).to_list(length=None)
        return [LessonReview(**review) for review in lesson_reviews]

    async def get_lesson(
        self, lesson_id: str, current_user: User | None = None
    ) -> Lesson:
        lesson = await self.collection.find_one({"_id": ObjectId(lesson_id)})
        if not lesson:
            raise HTTPException(
                status_code=404, detail=f"Lesson with id {lesson_id} not found"
            )

        # Scramble and Reverse Logic if user has already reviewed the lesson
        if current_user:
            user_id = str(current_user.id)
            lesson_review = await self.review_collection.find_one(
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
                        spaced_japanese = (
                            " ".join(words) if words else original_japanese
                        )
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

    async def update_lesson(self, lesson_id: str, updated_info: UpdateLesson) -> Lesson:
        lesson_info_to_update = {
            k: v for k, v in updated_info.model_dump().items() if v is not None
        }
        if not updated_info.section_id:
            lesson_info_to_update["section_id"] = None

        old_lesson = await self.collection.find_one_and_update(
            {"_id": ObjectId(lesson_id)}, {"$set": lesson_info_to_update}
        )
        if old_lesson is None:
            raise HTTPException(
                status_code=404, detail=f"Lesson wih id {lesson_id} not found"
            )

        keys_to_invalidate = []
        if old_lesson.get("category"):
            keys_to_invalidate.append(f"category_{old_lesson['category'].lower()}")

        updated_lesson = await self.collection.find_one({"_id": ObjectId(lesson_id)})
        if updated_lesson is None:
            raise HTTPException(
                status_code=404, detail=f"Lesson with id {lesson_id} failed to update"
            )

        if updated_lesson.get("category") and updated_lesson.get(
            "category"
        ) != old_lesson.get("category"):
            keys_to_invalidate.append(f"category_{updated_lesson['category'].lower()}")

        await self._invalidate_cache(keys=keys_to_invalidate)

        # If cards were in the old lesson but not the new lesson, remove the lesson id from them
        if old_lesson.get("card_ids"):
            cards_to_remove = set(old_lesson["card_ids"]) - set(
                updated_lesson.get("card_ids", [])
            )
            if cards_to_remove:
                await self.card_collection.update_many(
                    {
                        "_id": {
                            "$in": [ObjectId(card_id) for card_id in cards_to_remove]
                        }
                    },
                    {"$pull": {"lesson_ids": lesson_id}},
                )

        # If the lesson contains cards, update the cards to reflect the new lesson
        if updated_lesson.get("card_ids"):
            current_card_ids = [
                ObjectId(card_id) for card_id in updated_lesson["card_ids"]
            ]
            await self.card_collection.update_many(
                {"_id": {"$in": current_card_ids}},
                {"$addToSet": {"lesson_ids": lesson_id}},
            )

        # Handle updates to the section_id fields
        old_section_id = old_lesson.get("section_id")
        new_section_id = updated_lesson.get("section_id")

        if old_section_id and old_section_id != new_section_id:
            await self.section_collection.update_one(
                {"_id": ObjectId(old_section_id)},
                {"$pull": {"lesson_ids": lesson_id}},
            )

        if new_section_id and new_section_id != old_section_id:
            await self.section_collection.update_one(
                {"_id": ObjectId(new_section_id)},
                {"$addToSet": {"lesson_ids": lesson_id}},
            )

        return Lesson(**updated_lesson)

    async def delete_lesson(self, lesson_id: str) -> None:
        lesson = await self.collection.find_one({"_id": ObjectId(lesson_id)})

        await self.collection.delete_one({"_id": ObjectId(lesson_id)})

        keys = []
        if lesson and lesson.get("category"):
            keys.append(f"category_{lesson['category'].lower()}")
        await self._invalidate_cache(keys=keys)

        await self.card_collection.update_many(
            {"lesson_ids": ObjectId(lesson_id)},
            {"$pull": {"lesson_ids": lesson_id}},
        )

        await self.section_collection.update_one(
            {"lesson_ids": ObjectId(lesson_id)},
            {"$pull": {"lesson_ids": lesson_id}},
        )

    async def submit_review(
        self, lesson_id: str, user_id: str, overall_performance: int, current_user: User
    ) -> dict:
        lesson: Lesson | None = await self.collection.find_one(
            {"_id": ObjectId(lesson_id)}
        )
        if not lesson:
            raise HTTPException(
                status_code=404, detail=f"Lesson with id {lesson_id} not found"
            )

        lesson_review = await self.review_collection.find_one(
            {"lesson_id": lesson_id, "user_id": user_id}
        )

        # If the lesson review does not exist, create a new one
        if not lesson_review:
            lesson_review_obj = LessonReview(lesson_id=lesson_id, user_id=user_id)
            lesson_review_obj.review(overall_performance)
            await self.review_collection.insert_one(
                lesson_review_obj.model_dump(by_alias=True, exclude={"id"})
            )

        else:  # Otherwise update the existing one
            lesson_review_obj = LessonReview(**lesson_review)
            lesson_review_obj.review(overall_performance)
            await self.review_collection.find_one_and_update(
                {
                    "lesson_id": lesson_id,
                    "user_id": user_id,
                },
                {
                    "$set": {
                        k: v
                        for k, v in lesson_review_obj.model_dump().items()
                        if k != "_id"
                    }
                },
            )

        review_log = ReviewLog(
            lesson_id=lesson_id,
            user_id=user_id,
            review_date=datetime.now(timezone.utc),
            rating=overall_performance,
        )
        await self.log_collection.insert_one(
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

        await self.user_collection.update_one(
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

    async def get_review_history(self, user_id: str) -> list[ReviewLog]:
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        logs = (
            await self.log_collection.find({"user_id": user_id})
            .sort("review_date", -1)
            .to_list(length=None)
        )
        return [ReviewLog(**log) for log in logs]
