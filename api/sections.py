from bson import ObjectId
from fastapi import APIRouter, Request, status, HTTPException, Depends
from pymongo.asynchronous.collection import AsyncCollection
from aiocache import cached, caches

from api.dependencies import get_db, RoleChecker
from app.limiter import limiter
from models import Section, PyObjectId, Lesson, Card
from models.update_section import UpdateSection

router = APIRouter(prefix="/api/sections", tags=["Sections"])


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("5/minute")
async def create_section(request: Request, section: Section, db=Depends(get_db)):
    section_collection: AsyncCollection = db["sections"]
    lesson_collection = db["lessons"]

    inserted_section = await section_collection.insert_one(
        section.model_dump(by_alias=True, exclude={"id"})
    )
    new_section = await section_collection.find_one(
        {"_id": inserted_section.inserted_id}
    )

    if new_section is None:
        raise HTTPException(status_code=500, detail="Section creation failed")

    # Invalidate cache
    cache = caches.get("default")
    await cache.delete(key="all_sections")

    if new_section["lesson_ids"]:
        lesson_object_ids = [
            ObjectId(lesson_id) for lesson_id in new_section["lesson_ids"]
        ]

        await lesson_collection.update_many(
            {"_id": {"$in": lesson_object_ids}},
            {"$set": {"section_id": str(new_section["_id"])}},
        )

        await section_collection.update_many(
            {
                "_id": {"$ne": new_section["_id"]},
                "lesson_ids": {"$in": new_section["lesson_ids"]},
            },
            {"$pull": {"lesson_ids": {"$in": new_section["lesson_ids"]}}},
        )

        await section_collection.update_many(
            {
                "_id": {"$ne": new_section["_id"]},
                "lesson_ids": {"$in": new_section["lesson_ids"]},
            },
            {"$pull": {"lesson_ids": {"$in": new_section["lesson_ids"]}}},
        )

    return section


@router.get("/all")
@limiter.limit("10/minute")
@cached(
    ttl=3600,
    key="all_sections",
    alias="default",
)
async def get_all_sections(request: Request, db=Depends(get_db)):
    section_collection = db.get_collection("sections")
    sections = await section_collection.find().sort("order_index", 1).to_list()

    return [Section(**section) for section in sections]


@router.get("/{section_id}/download")
@limiter.limit("5/minute")
@cached(
    ttl=600,
    key_builder=lambda f, *args, **kwargs: f"download_{kwargs['section_id']}",
    alias="default",
)
async def download_section(
    request: Request, section_id: PyObjectId, db=Depends(get_db)
):
    section_collection = db["sections"]
    lesson_collection = db["lessons"]
    card_collection = db["cards"]

    section = await section_collection.find_one({"_id": ObjectId(section_id)})
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    lessons = (
        await lesson_collection.find({"section_id": section["_id"]})
        .sort("order_index", 1)
        .to_list()
    )

    card_ids = []
    for lesson in lessons:
        if "card_ids" in lesson and lesson["card_ids"]:
            card_ids.extend([ObjectId(cid) for cid in lesson["card_ids"]])

    cards = []
    if card_ids:
        cards = await card_collection.find({"_id": {"$in": card_ids}}).to_list()

    return {
        "section": Section(**section),
        "lessons": [Lesson(**lesson) for lesson in lessons],
        "cards": [Card(**card) for card in cards],
    }


@router.get("/{section_id}")
@limiter.limit("10/minute")
async def get_section(request: Request, section_id: PyObjectId, db=Depends(get_db)):
    section_collection = db["sections"]

    section = await section_collection.find_one({"_id": ObjectId(section_id)})
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    return Section(**section)


@router.put("/update/{section_id}", dependencies=[Depends(RoleChecker(["admin"]))])
@limiter.limit("10/minute")
async def update_section(
    request: Request,
    section_id: PyObjectId,
    updated_info: UpdateSection,
    db=Depends(get_db),
):
    section_collection = db["sections"]
    lesson_collection = db["lessons"]

    section_info_to_update = {
        k: v for k, v in updated_info.model_dump().items() if v is not None
    }
    old_section = await section_collection.find_one_and_update(
        {"_id": ObjectId(section_id)}, {"$set": section_info_to_update}
    )

    if old_section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    # Invalidate cache
    cache = caches.get("default")
    await cache.delete(key="all_sections")
    await cache.delete(key=f"download_{section_id}")

    updated_section = await section_collection.find_one({"_id": ObjectId(section_id)})

    if old_section["lesson_ids"]:
        removed_lesson_ids = set(old_section["lesson_ids"]) - set(
            updated_section["lesson_ids"]
        )
        if removed_lesson_ids:
            # Unset section_id for these lessons
            await lesson_collection.update_many(
                {
                    "_id": {
                        "$in": [ObjectId(lesson_id) for lesson_id in removed_lesson_ids]
                    }
                },
                {"$unset": {"section_id": ""}},
            )

    if updated_section["lesson_ids"]:
        current_lesson_ids = [
            ObjectId(lesson_id) for lesson_id in updated_section["lesson_ids"]
        ]

        if current_lesson_ids:
            await lesson_collection.update_many(
                {"_id": {"$in": current_lesson_ids}},
                {"$set": {"section_id": updated_section["_id"]}},
            )

            await section_collection.update_many(
                {
                    "_id": {"$ne": ObjectId(section_id)},
                    "lesson_ids": {"$in": updated_section["lesson_ids"]},
                },
                {"$pull": {"lesson_ids": {"$in": updated_section["lesson_ids"]}}},
            )

    return Section(**updated_section)


@router.delete(
    "/delete/{section_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("10/minute")
async def delete_section(
    request: Request,
    section_id: PyObjectId,
    db=Depends(get_db),
):
    section_collection = db["sections"]
    lesson_collection = db["lessons"]

    await section_collection.delete_one({"_id": ObjectId(section_id)})
    await lesson_collection.update_many(
        {"section_id": section_id}, {"$unset": {"section_id": ""}}
    )

    # Invalidate cache
    cache = caches.get("default")
    await cache.delete(key="all_sections")
    await cache.delete(key=f"download_{section_id}")
