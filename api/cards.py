import dotenv
from fastapi.encoders import jsonable_encoder

from models import Card, UpdateCard

from fastapi import APIRouter
from pymongo import MongoClient

router = APIRouter(prefix="/api/cards", tags=["Cards"])
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


@router.post("/create")
async def create_card(card: Card):
    """Create a new card in the database"""

    # If we don't encode the card, we run into a problem where the card id is not a string
    new_card = jsonable_encoder(card)

    card_collection.insert_one(new_card)

    # Update the lessons that the card is in
    if new_card["lesson_id"]:
        for lesson_id in new_card["lesson_id"]:
            lesson_collection.find_one_and_update({"_id": lesson_id}, {"$addToSet": {"cards": new_card["_id"]}})

    return card


@router.get("/{card_id}")
async def get_card(card_id):
    """Retrieve a card from the database by id"""
    card = card_collection.find_one({"_id": card_id})
    return card


@router.get("/lesson/{lesson_id}")
async def get_cards_by_lesson(lesson_id):
    """Retrieve all cards associated with a lesson from the database by lesson id"""
    cards = card_collection.find({"lesson_id": lesson_id})
    return [Card(**card) for card in cards]


@router.put("/update/{card_id}")
async def update_card(card_id, updated_info: UpdateCard):
    """Update a card in the database by id"""
    card_info_to_update = {k: v for k, v in updated_info.dict().items() if v is not None}

    # update a card in the database by id
    old_card = card_collection.find_one_and_update({"_id": card_id}, {"$set": card_info_to_update})
    if old_card is None:
        return {"error": "Card not found"}

    updated_card = card_collection.find_one({"_id": card_id})
    if updated_card is None:
        return {"error": "Card not found"}

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


@router.delete("/delete/{card_id}")
async def delete_card(card_id):
    """Delete a card from the database by id"""
    card_collection.delete_one({"_id": card_id})

    # Delete the card from all lessons that it is in
    lesson_collection.update_many({}, {"$pull": {"cards": card_id}})

    return {"message": "Card deleted successfully"}
