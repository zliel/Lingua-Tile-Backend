from bson import ObjectId
from fastapi import HTTPException
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.results import InsertOneResult

from models.cards import Card
from models.update_card import UpdateCard
from services.base import BaseService


class CardService(BaseService):
    @property
    def collection(self) -> AsyncCollection:
        return self.db["cards"]

    @property
    def lesson_collection(self) -> AsyncCollection:
        return self.db["lessons"]

    async def get_all_cards(self) -> list[Card]:
        cards = await self.collection.find().to_list(length=None)
        return [Card(**card) for card in cards]

    async def create_card(self, card: Card) -> Card:
        result: InsertOneResult = await self.collection.insert_one(
            card.model_dump(by_alias=True, exclude={"id"})
        )
        new_card = await self.collection.find_one({"_id": result.inserted_id})

        if new_card is None:
            raise HTTPException(
                status_code=500, detail="Card was not created successfully"
            )

        # Update the lessons that the card is in
        if new_card.get("lesson_ids"):
            lesson_object_ids = [
                ObjectId(lesson_id) for lesson_id in new_card["lesson_ids"]
            ]
            await self.lesson_collection.update_many(
                {"_id": {"$in": lesson_object_ids}},
                {"$addToSet": {"card_ids": str(new_card["_id"])}},
            )

        return Card(**new_card)

    async def get_card_by_id(self, card_id: str) -> Card:
        card = await self.collection.find_one({"_id": ObjectId(card_id)})
        if card is None:
            raise HTTPException(
                status_code=404, detail=f"Card with id {card_id} not found"
            )
        return Card(**card)

    async def get_cards_by_lesson(self, lesson_id: str) -> list[Card]:
        cards = await self.collection.find({"lesson_ids": lesson_id}).to_list(
            length=None
        )
        return [Card(**card) for card in cards]

    async def update_card(self, card_id: str, updated_info: UpdateCard) -> Card:
        card_info_to_update = {
            k: v for k, v in updated_info.model_dump().items() if v is not None
        }

        old_card = await self.collection.find_one_and_update(
            {"_id": ObjectId(card_id)}, {"$set": card_info_to_update}
        )
        if old_card is None:
            raise HTTPException(
                status_code=404, detail=f"Card with id {card_id} was not found"
            )

        updated_card_doc = await self.collection.find_one({"_id": ObjectId(card_id)})
        if updated_card_doc is None:
            raise HTTPException(
                status_code=404,
                detail=f"Card with id {card_id} was not found after update",
            )

        if "lesson_ids" in card_info_to_update:
            new_lesson_ids = [
                ObjectId(lesson_id) for lesson_id in card_info_to_update["lesson_ids"]
            ]

            if new_lesson_ids:
                await self.lesson_collection.update_many(
                    {"_id": {"$in": new_lesson_ids}},
                    {"$addToSet": {"card_ids": card_id}},
                )

            # Remove card from lessons it's no longer in
            if old_card.get("lesson_ids"):
                removed_lesson_ids = set(old_card["lesson_ids"]) - set(
                    card_info_to_update["lesson_ids"]
                )
                if removed_lesson_ids:
                    await self.lesson_collection.update_many(
                        {
                            "_id": {
                                "$in": [
                                    ObjectId(lesson_id)
                                    for lesson_id in removed_lesson_ids
                                ]
                            }
                        },
                        {"$pull": {"card_ids": card_id}},
                    )

        return Card(**updated_card_doc)

    async def delete_card(self, card_id: str) -> None:
        await self.collection.delete_one({"_id": ObjectId(card_id)})
        await self.lesson_collection.update_many({}, {"$pull": {"card_ids": card_id}})

    async def get_cards_by_ids(self, card_ids: list[str]) -> list[Card]:
        object_ids = [ObjectId(card_id) for card_id in card_ids]

        # Fetch all cards that match the IDs
        cards_cursor = self.collection.find({"_id": {"$in": object_ids}})
        cards_list = await cards_cursor.to_list(length=len(card_ids))

        # Using a map for faster lookups
        cards_map = {str(card["_id"]): card for card in cards_list}

        # Reconstruct the list in the order of the input card_ids
        ordered_cards = []
        for card_id in card_ids:
            if card_id in cards_map:
                ordered_cards.append(Card(**cards_map[card_id]))

        return ordered_cards

    async def create_cards_bulk(self, cards: list[Card]) -> list[Card]:
        """Create multiple cards in a single batch operation."""
        if not cards:
            return []

        # Prepare documents for insertion
        card_docs = [card.model_dump(by_alias=True, exclude={"id"}) for card in cards]

        # Bulk insert all cards
        result = await self.collection.insert_many(card_docs)

        # Fetch all newly created cards
        new_cards = await self.collection.find(
            {"_id": {"$in": result.inserted_ids}}
        ).to_list(length=len(result.inserted_ids))

        # Collect all lesson_id -> card_id mappings for batch update
        lesson_to_cards: dict[str, list[str]] = {}
        for card in new_cards:
            card_id = str(card["_id"])
            for lesson_id in card.get("lesson_ids", []):
                if lesson_id not in lesson_to_cards:
                    lesson_to_cards[lesson_id] = []
                lesson_to_cards[lesson_id].append(card_id)

        # Batch update lessons with new card associations
        for lesson_id, card_ids in lesson_to_cards.items():
            await self.lesson_collection.update_one(
                {"_id": ObjectId(lesson_id)},
                {"$addToSet": {"card_ids": {"$each": card_ids}}},
            )

        return [Card(**card) for card in new_cards]
