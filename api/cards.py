import dotenv

from models import Card

from fastapi import APIRouter
from pymongo import MongoClient

router = APIRouter(prefix="/api/cards", tags=["cards"])
mongo_host = dotenv.get_key(".env", "MONGO_HOST")
client = MongoClient(mongo_host)
db = client['lingua-tile']
card_collection = db['cards']
lesson_collection = db['lessons']


@router.get("/all")
async def get_all_cards():
    """Retrieve all cards from the database"""
    cards = card_collection.find()
    return [Card(**card) for card in cards]


@router.post("/create/{front_text}/{back_text}/{lesson_id}")
async def create_card(front_text, back_text, lesson_id):
    """Create a new card in the database"""
    new_card = Card(front_text, back_text, lesson_id)
    card_collection.insert_one(new_card.__dict__)

    # Add the card to its corresponding lesson
    lesson_collection.find_one_and_update({"_id": lesson_id}, {"$addToSet": {"cards": new_card.__dict__}})
    return new_card


@router.get("/{card_id}")
async def get_card(card_id):
    """Retrieve a card from the database by id"""
    card = card_collection.find_one({"_id": card_id})
    return card


@router.delete("/delete/{card_id}")
async def delete_card(card_id):
    """Delete a card from the database by id"""
    card_collection.delete_one({"_id": card_id})

    # Delete the card from its corresponding lesson
    lesson_collection.update_many({}, {"$pull": {"cards": {"_id": card_id}}})

    return {"message": "Card deleted"}


@router.put("/update/{card_id}")
async def update_card(card_id, updated_card_info: dict):
    """Update a card in the database by id"""
    updated_card = card_collection.find_one_and_update({"_id": card_id}, {"$set": updated_card_info})

    # If the lesson id was changed, update the lesson to reflect the new card
    if "lesson_id" in updated_card_info:
        lesson_collection.find_one_and_update({"_id": updated_card_info["lesson_id"]}, {"$addToSet": {"cards": updated_card}})
        lesson_collection.find_one_and_update({"_id": updated_card["lesson_id"]}, {"$pull": {"cards": updated_card}})
    if updated_card is None:
        return {"message": "Card not found"}
    return updated_card
