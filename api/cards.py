from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.results import InsertOneResult

from api.dependencies import RoleChecker, get_current_user, get_db
from api.users import is_admin
from app.limiter import limiter
from models.cards import Card
from models.py_object_id import PyObjectId
from models.update_card import UpdateCard
from models.users import User

router = APIRouter(prefix="/api/cards", tags=["Cards"])


@router.get("/all", response_model=list[Card])
@limiter.limit("5/minute")
async def get_all_cards(
    request: Request, current_user: User = Depends(get_current_user), db=Depends(get_db)
):
    """Retrieve all cards from the database"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")
    cards = await db["cards"].find().to_list()
    return [Card(**card) for card in cards]


@router.post(
    "/create",
    response_model=Card,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("10/minute")
async def create_card(
    request: Request,
    card: Card,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Create a new card in the database"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    card_collection: AsyncCollection = db["cards"]
    lesson_collection: AsyncCollection = db["lessons"]

    # If we don't encode the card, we run into a problem where the card id is not a string
    result: InsertOneResult = await card_collection.insert_one(
        card.model_dump(by_alias=True, exclude={"id"})
    )
    new_card: Card | None = await card_collection.find_one({"_id": result.inserted_id})

    if new_card is None:
        raise HTTPException(status_code=500, detail="Card was not created successfully")

    # Update the lessons that the card is in
    if new_card["lesson_ids"]:
        lesson_object_ids = [
            ObjectId(lesson_id) for lesson_id in new_card["lesson_ids"]
        ]
        await lesson_collection.update_many(
            {"_id": {"$in": lesson_object_ids}},
            {"$addToSet": {"card_ids": str(new_card["_id"])}},
        )

    return card


@router.get("/{card_id}", response_model=Card)
@limiter.limit("10/minute")
async def get_card(request: Request, card_id: PyObjectId, db=Depends(get_db)):
    """Retrieve a card from the database by id"""
    card_collection = db["cards"]
    card = await card_collection.find_one({"_id": ObjectId(card_id)})
    return card


@router.get("/lesson/{lesson_id}", response_model=list[Card])
@limiter.limit("10/minute")
async def get_cards_by_lesson(
    request: Request, lesson_id: PyObjectId, db=Depends(get_db)
):
    """Retrieve all cards associated with a lesson from the database by lesson id"""
    card_collection = db["cards"]
    cards = await card_collection.find({"lesson_ids": lesson_id}).to_list()
    return [Card(**card) for card in cards]


@router.put(
    "/update/{card_id}",
    response_model=Card,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("10/minute")
async def update_card(
    request: Request,
    card_id: PyObjectId,
    updated_info: UpdateCard,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Update a card in the database by id"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    card_info_to_update = {
        k: v for k, v in updated_info.model_dump().items() if v is not None
    }

    card_collection: AsyncCollection = db["cards"]
    lesson_collection = db["lessons"]

    # update a card in the database by id
    old_card = await card_collection.find_one_and_update(
        {"_id": ObjectId(card_id)}, {"$set": card_info_to_update}
    )
    if old_card is None:
        raise HTTPException(
            status_code=404, detail=f"Card with id {card_id} was not found"
        )

    updated_card = await card_collection.find_one({"_id": ObjectId(card_id)})
    if updated_card is None:
        raise HTTPException(
            status_code=404, detail=f"Card with id {card_id} was not found after update"
        )

    if "lesson_ids" in card_info_to_update:
        new_lesson_ids = [
            ObjectId(lesson_id) for lesson_id in card_info_to_update["lesson_ids"]
        ]

        if new_lesson_ids:
            await lesson_collection.update_many(
                {"_id": {"$in": new_lesson_ids}},
                {"$addToSet": {"card_ids": card_id}},
            )

        # Remove card from lessons it's no longer in
        if old_card["lesson_ids"]:
            removed_lesson_ids = set(old_card["lesson_ids"]) - set(
                card_info_to_update["lesson_ids"]
            )
            if removed_lesson_ids:
                await lesson_collection.update_many(
                    {
                        "_id": {
                            "$in": [
                                ObjectId(lesson_id) for lesson_id in removed_lesson_ids
                            ]
                        }
                    },
                    {"$pull": {"card_ids": card_id}},
                )

    return updated_card


@router.delete(
    "/delete/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("10/minute")
async def delete_card(
    request: Request,
    card_id: PyObjectId,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete a card from the database by id"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    card_collection = db["cards"]
    lesson_collection = db["lessons"]

    await card_collection.delete_one({"_id": ObjectId(card_id)})

    await lesson_collection.update_many({}, {"$pull": {"card_ids": card_id}})


@router.post("/by-ids", response_model=list[Card])
@limiter.limit("10/minute")
async def get_cards_by_ids(
    request: Request, card_ids: list[PyObjectId], db=Depends(get_db)
):
    """Retrieve cards by a list of IDs, preserving the order of the input list"""
    card_collection = db["cards"]

    object_ids = [ObjectId(card_id) for card_id in card_ids]

    # Fetch all cards that match the IDs
    cards_cursor = card_collection.find({"_id": {"$in": object_ids}})
    cards_list = await cards_cursor.to_list(length=len(card_ids))

    # Using a map for faster lookups
    cards_map = {str(card["_id"]): card for card in cards_list}

    # Reconstruct the list in the order of the input card_ids
    ordered_cards = []
    for card_id in card_ids:
        if card_id in cards_map:
            ordered_cards.append(Card(**cards_map[card_id]))

    return ordered_cards
