import dotenv
from fastapi import APIRouter, status, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from pymongo import MongoClient

from api.users import get_current_user, is_admin
from models import Section, PyObjectId, User

router = APIRouter(prefix="/api/sections", tags=["Sections"])
mongo_host = dotenv.get_key(".env", "MONGO_HOST")
client = MongoClient(mongo_host)
db = client['lingua-tile']
section_collection = db['sections']
lesson_collection = db['lessons']


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_section(section: Section, current_user: User = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")
    new_section = jsonable_encoder(section)
    section_collection.insert_one(new_section)

    for lesson_id in new_section["lesson_ids"]:
        lesson_collection.find_one_and_update({"_id": lesson_id}, {"$set": {"section_id": new_section["_id"]}})
    return section


@router.get("/all")
async def get_all_sections():
    sections = section_collection.find()
    return [Section(**section) for section in sections]


@router.get("/{section_id}")
async def get_section(section_id: PyObjectId):
    section = section_collection.find_one({"_id": section_id})
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    return Section(**section)


@router.put("/update/{section_id}")
async def update_section(section_id: PyObjectId, updated_info: Section, current_user: User = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")
    section_info_to_update = {k: v for k, v in updated_info.dict().items() if v is not None}
    old_section = section_collection.find_one_and_update({"_id": section_id}, {"$set": section_info_to_update})
    if old_section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    updated_section = section_collection.find_one({"_id": section_id})

    for lesson_id in updated_section["lesson_ids"]:
        lesson_collection.find_one_and_update({"_id": lesson_id}, {"$set": {"section_id": updated_section["_id"]}})

    return Section(**updated_section)


@router.delete("/delete/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(section_id: PyObjectId, current_user: User = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")
    section_collection.delete_one({"_id": section_id})

    lesson_collection.update_many({"section_id": section_id}, {"$unset": {"section_id": ""}})
