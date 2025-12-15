from bson import ObjectId
from fastapi import APIRouter, status, HTTPException, Depends
from pymongo.asynchronous.collection import AsyncCollection

from api.dependencies import get_current_user, get_db
from api.users import is_admin
from models import Section, PyObjectId, User
from models.update_section import UpdateSection

router = APIRouter(prefix="/api/sections", tags=["Sections"])


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_section(
    section: Section, current_user: User = Depends(get_current_user), db=Depends(get_db)
):
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

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
async def get_all_sections(db=Depends(get_db)):
    section_collection = db.get_collection("sections")
    sections = await section_collection.find().sort("order_index", 1).to_list()

    return [Section(**section) for section in sections]


@router.get("/{section_id}")
async def get_section(section_id: PyObjectId, db=Depends(get_db)):
    section_collection = db["sections"]

    section = await section_collection.find_one({"_id": ObjectId(section_id)})
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    return Section(**section)


@router.put("/update/{section_id}")
async def update_section(
    section_id: PyObjectId,
    updated_info: UpdateSection,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

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


@router.delete("/delete/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section_id: PyObjectId,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    section_collection = db["sections"]
    lesson_collection = db["lessons"]

    await section_collection.delete_one({"_id": ObjectId(section_id)})
    await lesson_collection.update_many(
        {"section_id": section_id}, {"$unset": {"section_id": ""}}
    )
