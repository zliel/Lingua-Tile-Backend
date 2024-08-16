import bson
import dotenv
from fastapi.encoders import jsonable_encoder

from models import Card, UpdateCard, PyObjectId, User
from api.users import get_current_user, is_admin

from fastapi import APIRouter, status, HTTPException, Depends
from pymongo import MongoClient

router = APIRouter(prefix="/api/cards", tags=["Cards"])
mongo_host = dotenv.get_key(".env", "MONGO_HOST")
client = MongoClient(mongo_host)
db = client['lingua-tile']
card_collection = db['cards']
lesson_collection = db['lessons']


@router.get("/all")
async def get_all_cards(current_user: User = Depends(get_current_user)):
    """Retrieve all cards from the database"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")
    cards = card_collection.find()
    return [Card(**card) for card in cards]


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_card(card: Card, current_user: User = Depends(get_current_user)):
    """Create a new card in the database"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # If we don't encode the card, we run into a problem where the card id is not a string
    new_card = jsonable_encoder(card)

    card_collection.insert_one(new_card)

    # Update the lessons that the card is in
    if new_card["lesson_ids"]:
        for lesson_id in new_card["lesson_ids"]:
            lesson_collection.find_one_and_update({"_id": lesson_id}, {"$addToSet": {"cards": new_card["_id"]}})

    return card


@router.get("/{card_id}")
async def get_card(card_id: PyObjectId):
    """Retrieve a card from the database by id"""
    card = card_collection.find_one({"_id": card_id})
    return card


@router.get("/lesson/{lesson_id}")
async def get_cards_by_lesson(lesson_id: PyObjectId):
    """Retrieve all cards associated with a lesson from the database by lesson id"""
    cards = card_collection.find({"lesson_ids": lesson_id})
    return [Card(**card) for card in cards]


@router.put("/update/{card_id}")
async def update_card(card_id: PyObjectId, updated_info: UpdateCard, current_user: User = Depends(get_current_user)):
    """Update a card in the database by id"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    card_info_to_update = {k: v for k, v in updated_info.dict().items() if v is not None}

    # update a card in the database by id
    old_card = card_collection.find_one_and_update({"_id": card_id}, {"$set": card_info_to_update})
    if old_card is None:
        raise HTTPException(status_code=404, detail=f"Card with id {card_id} was not found")

    updated_card = card_collection.find_one({"_id": card_id})
    if updated_card is None:
        raise HTTPException(status_code=404, detail=f"Card with id {card_id} was not found after update")

    # If the card_info_to_update contains lesson IDs, we need to add the card to the lessons
    if card_info_to_update.__contains__("lesson_id"):
        for lesson_id in card_info_to_update["lesson_id"]:
            lesson_collection.find_one_and_update({"_id": lesson_id}, {"$addToSet": {"cards": card_id}})

    # If the card was in a lesson before, but not after updating, remove it from that lesson
    if old_card["lesson_id"]:
        for lesson_id in old_card["lesson_id"]:
            if lesson_id not in card_info_to_update["lesson_id"]:
                lesson_collection.find_one_and_update({"_id": lesson_id}, {"$pull": {"cards": card_id}})

    return updated_card


@router.delete("/delete/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(card_id: PyObjectId, current_user: User = Depends(get_current_user)):
    """Delete a card from the database by id"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    card_collection.delete_one({"_id": card_id})

    lesson_collection.update_many({}, {"$pull": {"card_ids": card_id}})
