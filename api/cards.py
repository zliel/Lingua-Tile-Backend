import dotenv

from models import Card

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


@router.get("/lesson/{lesson_id}")
async def get_cards_by_lesson(lesson_id):
    """Retrieve all cards associated with a lesson from the database by lesson id"""
    cards = card_collection.find({"lesson_id": lesson_id})
    return [Card(**card) for card in cards]


@router.put("/update/{card_id}")
async def update_card(card_id, updated_card_info: dict):
    """Update a card in the database by id"""
    updated_card = card_collection.find_one_and_update({"_id": card_id}, {"$set": updated_card_info})

    # If the lesson id was changed, update the lesson to reflect the new card
    if "lesson_id" in card_info_to_update:
        lesson_collection.find_one_and_update({"_id": card_info_to_update["lesson_id"]},
                                              {"$addToSet": {"cards": updated_card}})

        lesson_collection.find_one_and_update({"_id": old_card["lesson_id"]},
                                              {"$pull": {"cards": updated_card}})

    # TODO: Consider changing the Lesson model to have a list of card ids instead of a list of cards, so that we
    #  don't have to update the lesson every time a card is updated . If so, change the old_card query to return the document
    # TODO: Also check if the Optional[str] = None is necessary for the update_card model
    if updated_card is None:
        return {"message": "Card not found"}
    return updated_card


@router.delete("/delete/{card_id}")
async def delete_card(card_id):
    """Delete a card from the database by id"""
    card_collection.delete_one({"_id": card_id})

    # Delete the card from its corresponding lesson
    lesson_collection.update_many({}, {"$pull": {"cards": {"_id": card_id}}})

    return {"message": "Card deleted"}
