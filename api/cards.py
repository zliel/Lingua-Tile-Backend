from fastapi import APIRouter, status, HTTPException, Depends

from api.dependencies import get_db, get_current_user
from api.users import is_admin
from models import Card, UpdateCard, PyObjectId, User

router = APIRouter(prefix="/api/cards", tags=["Cards"])


@router.get("/all")
async def get_all_cards(
    current_user: User = Depends(get_current_user), db=Depends(get_db)
):
    """Retrieve all cards from the database"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")
    cards = db["cards"].find()
    return [Card(**card) for card in cards]


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_card(
    card: Card, current_user: User = Depends(get_current_user), db=Depends(get_db)
):
    """Create a new card in the database"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    card_collection = db["cards"]
    lesson_collection = db["lessons"]

    # If we don't encode the card, we run into a problem where the card id is not a string
    card_collection.insert_one(card.model_dump(by_alias=True))
    new_card = card_collection.find_one({"_id": card.id})

    # Update the lessons that the card is in
    if new_card["lesson_ids"]:
        for lesson_id in new_card["lesson_ids"]:
            lesson_collection.find_one_and_update(
                {"_id": lesson_id}, {"$addToSet": {"cards": new_card["_id"]}}
            )

    return card


@router.get("/{card_id}")
async def get_card(card_id: PyObjectId, db=Depends(get_db)):
    """Retrieve a card from the database by id"""
    card_collection = db["cards"]
    card = card_collection.find_one({"_id": card_id})
    return card


@router.get("/lesson/{lesson_id}")
async def get_cards_by_lesson(lesson_id: PyObjectId, db=Depends(get_db)):
    """Retrieve all cards associated with a lesson from the database by lesson id"""
    card_collection = db["cards"]
    cards = card_collection.find({"lesson_ids": lesson_id})
    return [Card(**card) for card in cards]


@router.put("/update/{card_id}", response_model=Card)
async def update_card(
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

    card_collection = db["cards"]
    lesson_collection = db["lessons"]

    # update a card in the database by id
    old_card = card_collection.find_one_and_update(
        {"_id": card_id}, {"$set": card_info_to_update}
    )
    if old_card is None:
        raise HTTPException(
            status_code=404, detail=f"Card with id {card_id} was not found"
        )

    updated_card = card_collection.find_one({"_id": card_id})
    if updated_card is None:
        raise HTTPException(
            status_code=404, detail=f"Card with id {card_id} was not found after update"
        )

    # If the card_info_to_update contains lesson IDs, we need to add the card to the lessons
    if card_info_to_update.__contains__("lesson_ids"):
        for lesson_id in card_info_to_update["lesson_ids"]:
            lesson_collection.find_one_and_update(
                {"_id": lesson_id}, {"$addToSet": {"card_ids": card_id}}
            )

    # If the card was in a lesson before, but not after updating, remove it from that lesson
    if old_card["lesson_ids"]:
        for lesson_id in old_card["lesson_ids"]:
            if lesson_id not in card_info_to_update["lesson_ids"]:
                lesson_collection.find_one_and_update(
                    {"_id": lesson_id}, {"$pull": {"card_ids": card_id}}
                )

    return updated_card


@router.delete("/delete/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    card_id: PyObjectId,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete a card from the database by id"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    card_collection = db["cards"]
    lesson_collection = db["lessons"]

    card_collection.delete_one({"_id": card_id})

    lesson_collection.update_many({}, {"$pull": {"card_ids": card_id}})
