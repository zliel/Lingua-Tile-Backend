from aiocache import caches
from bson import ObjectId
from fastapi import HTTPException
from pymongo.asynchronous.collection import AsyncCollection

from models.cards import Card
from models.lessons import Lesson
from models.sections import Section
from models.update_section import UpdateSection
from services.base import BaseService


class SectionService(BaseService):
    @property
    def collection(self) -> AsyncCollection:
        return self.db["sections"]

    @property
    def lesson_collection(self) -> AsyncCollection:
        return self.db["lessons"]

    @property
    def card_collection(self) -> AsyncCollection:
        return self.db["cards"]

    async def _invalidate_cache(self, keys: list[str] | None = None):
        cache = caches.get("default")
        await cache.delete(key="all_sections")
        if keys:
            for key in keys:
                await cache.delete(key=key)

    async def create_section(self, section: Section) -> Section:
        inserted_section = await self.collection.insert_one(
            section.model_dump(by_alias=True, exclude={"id"})
        )
        new_section = await self.collection.find_one(
            {"_id": inserted_section.inserted_id}
        )

        if new_section is None:
            raise HTTPException(status_code=500, detail="Section creation failed")

        await self._invalidate_cache()

        if new_section.get("lesson_ids"):
            lesson_object_ids = [
                ObjectId(lesson_id) for lesson_id in new_section["lesson_ids"]
            ]

            await self.lesson_collection.update_many(
                {"_id": {"$in": lesson_object_ids}},
                {"$set": {"section_id": str(new_section["_id"])}},
            )

            # Logic from original endpoint: remove these lessons from other sections
            await self.collection.update_many(
                {
                    "_id": {"$ne": new_section["_id"]},
                    "lesson_ids": {"$in": new_section["lesson_ids"]},
                },
                {"$pull": {"lesson_ids": {"$in": new_section["lesson_ids"]}}},
            )

        return Section(**new_section)

    async def get_all_sections(self) -> list[Section]:
        sections = (
            await self.collection.find().sort("order_index", 1).to_list(length=None)
        )
        return [Section(**section) for section in sections]

    async def get_section_for_download(self, section_id: str) -> dict:
        section = await self.collection.find_one({"_id": ObjectId(section_id)})
        if section is None:
            raise HTTPException(status_code=404, detail="Section not found")

        lessons = (
            await self.lesson_collection.find({"section_id": section["_id"]})
            .sort("order_index", 1)
            .to_list(length=None)
        )

        card_ids = []
        for lesson in lessons:
            if "card_ids" in lesson and lesson["card_ids"]:
                card_ids.extend([ObjectId(cid) for cid in lesson["card_ids"]])

        cards = []
        if card_ids:
            cards = await self.card_collection.find({"_id": {"$in": card_ids}}).to_list(
                length=None
            )

        return {
            "section": Section(**section),
            "lessons": [Lesson(**lesson) for lesson in lessons],
            "cards": [Card(**card) for card in cards],
        }

    async def get_section(self, section_id: str) -> Section:
        section = await self.collection.find_one({"_id": ObjectId(section_id)})
        if section is None:
            raise HTTPException(status_code=404, detail="Section not found")
        return Section(**section)

    async def update_section(
        self, section_id: str, updated_info: UpdateSection
    ) -> Section:
        section_info_to_update = {
            k: v for k, v in updated_info.model_dump().items() if v is not None
        }
        old_section = await self.collection.find_one_and_update(
            {"_id": ObjectId(section_id)}, {"$set": section_info_to_update}
        )

        if old_section is None:
            raise HTTPException(status_code=404, detail="Section not found")

        await self._invalidate_cache(keys=[f"download_{section_id}"])

        updated_section = await self.collection.find_one({"_id": ObjectId(section_id)})

        # Handle removing lessons
        if old_section.get("lesson_ids"):
            removed_lesson_ids = set(old_section["lesson_ids"]) - set(
                updated_section.get("lesson_ids", [])
            )
            if removed_lesson_ids:
                await self.lesson_collection.update_many(
                    {
                        "_id": {
                            "$in": [
                                ObjectId(lesson_id) for lesson_id in removed_lesson_ids
                            ]
                        }
                    },
                    {"$unset": {"section_id": ""}},
                )

        # Handle adding lessons
        if updated_section.get("lesson_ids"):
            current_lesson_ids = [
                ObjectId(lesson_id) for lesson_id in updated_section["lesson_ids"]
            ]

            if current_lesson_ids:
                await self.lesson_collection.update_many(
                    {"_id": {"$in": current_lesson_ids}},
                    {"$set": {"section_id": updated_section["_id"]}},
                )

                # Remove from other sections
                await self.collection.update_many(
                    {
                        "_id": {"$ne": ObjectId(section_id)},
                        "lesson_ids": {"$in": updated_section["lesson_ids"]},
                    },
                    {"$pull": {"lesson_ids": {"$in": updated_section["lesson_ids"]}}},
                )

        return Section(**updated_section)

    async def delete_section(self, section_id: str) -> None:
        await self.collection.delete_one({"_id": ObjectId(section_id)})
        await self.lesson_collection.update_many(
            {"section_id": section_id}, {"$unset": {"section_id": ""}}
        )
        await self._invalidate_cache(keys=[f"download_{section_id}"])
