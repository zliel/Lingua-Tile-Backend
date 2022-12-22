import json

import dotenv

from models import Card

from fastapi import APIRouter
from pymongo import MongoClient

router = APIRouter(prefix="/api/cards", tags=["cards"])
mongo_host = dotenv.get_key(".env", "MONGO_HOST")
client = MongoClient(mongo_host)
db = client['lingua-tile']
card_collection = db['cards']


@router.get("/all")
async def get_all_cards():
    """Retrieve all cards from the database"""
    cards = card_collection.find()
    return [Card(**card) for card in cards]


@router.get("/create/{front_text}/{back_text}/{lesson_id}")
async def create_card(front_text, back_text, lesson_id):
    """Create a new card in the database"""
    new_card = Card(front_text, back_text, lesson_id)
    card_collection.insert_one(new_card.__dict__)
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
    return {"message": "Card deleted"}


@router.put("/update/{card_id}")
async def update_card(card_id, updated_card_info: dict):
    """Update a card in the database by id"""
    updated_card = card_collection.find_one_and_update({"_id": card_id}, {"$set": updated_card_info})
    if updated_card is None:
        return {"message": "Card not found"}
    return updated_card
