from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.dependencies import RoleChecker, get_card_service, get_current_user
from api.users import is_admin
from app.limiter import limiter
from models.cards import Card
from models.py_object_id import PyObjectId
from models.update_card import UpdateCard
from models.users import User
from services.cards import CardService

router = APIRouter(prefix="/api/cards", tags=["Cards"])


@router.get("/all", response_model=list[Card])
@limiter.limit("5/minute")
@router.get("/all", response_model=list[Card])
@limiter.limit("5/minute")
async def get_all_cards(
    request: Request,
    current_user: User = Depends(get_current_user),
    card_service: CardService = Depends(get_card_service),
):
    """Retrieve all cards from the database"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await card_service.get_all_cards()


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
    card_service: CardService = Depends(get_card_service),
):
    """Create a new card in the database"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await card_service.create_card(card)


@router.post(
    "/create-bulk",
    response_model=list[Card],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("5/minute")
async def create_cards_bulk(
    request: Request,
    cards: list[Card],
    current_user: User = Depends(get_current_user),
    card_service: CardService = Depends(get_card_service),
):
    """Create multiple cards in a single request"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await card_service.create_cards_bulk(cards)


@router.get("/{card_id}", response_model=Card)
@limiter.limit("10/minute")
async def get_card(
    request: Request,
    card_id: PyObjectId,
    card_service: CardService = Depends(get_card_service),
):
    """Retrieve a card from the database by id"""
    return await card_service.get_card_by_id(str(card_id))


@router.get("/lesson/{lesson_id}", response_model=list[Card])
@limiter.limit("10/minute")
async def get_cards_by_lesson(
    request: Request,
    lesson_id: PyObjectId,
    card_service: CardService = Depends(get_card_service),
):
    """Retrieve all cards associated with a lesson from the database by lesson id"""
    return await card_service.get_cards_by_lesson(str(lesson_id))


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
    card_service: CardService = Depends(get_card_service),
):
    """Update a card in the database by id"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await card_service.update_card(str(card_id), updated_info)


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
    card_service: CardService = Depends(get_card_service),
):
    """Delete a card from the database by id"""
    if not is_admin(current_user):
        raise HTTPException(status_code=401, detail="Unauthorized")

    await card_service.delete_card(str(card_id))


@router.post("/by-ids", response_model=list[Card])
@limiter.limit("10/minute")
async def get_cards_by_ids(
    request: Request,
    card_ids: list[PyObjectId],
    card_service: CardService = Depends(get_card_service),
):
    """Retrieve cards by a list of IDs, preserving the order of the input list"""
    return await card_service.get_cards_by_ids([str(cid) for cid in card_ids])
