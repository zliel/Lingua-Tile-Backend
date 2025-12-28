from models.users import PushUnsubscribe
import os

from bson import ObjectId
from fastapi import APIRouter, Request, Depends, status, HTTPException

from api.dependencies import get_current_user, get_db
from app.limiter import limiter
from app.config import get_settings
from models import User
from models.users import PushSubscription


router = APIRouter(prefix="/api/notifications", tags=["Notifications"])
settings = get_settings()


@router.get("/vapid-public-key")
@limiter.limit("10/minute")
async def get_vapid_public_key(request: Request):
    key = settings.VAPID_PUBLIC_KEY
    return {"publicKey": key}


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def subscribe(
    request: Request,
    subscription: PushSubscription,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Subscribe a user to push notifications.
    """
    user_id = current_user.id
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    # Add subscription to user's list if it doesn't exist
    # We match by endpoint to ensure uniqueness
    # Note: user_id is a string from Pydantic, but MongoDB uses ObjectId for _id
    await db["users"].update_one(
        {
            "_id": ObjectId(user_id),
            "push_subscriptions.endpoint": {"$ne": subscription.endpoint},
        },
        {"$push": {"push_subscriptions": subscription.model_dump()}},
    )

    # If the subscription endpoint already exists, we might want to update keys,
    # but for now we assume endpoint is unique enough or we just didn't add it again.
    # To be safe/correct, if it exists we should probably update it.
    # But $ne check prevents duplicates.

    return {"message": "Subscribed successfully"}


@router.post("/unsubscribe", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def unsubscribe(
    request: Request,
    subscription: PushUnsubscribe,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Unsubscribe a user from push notifications.
    """
    user_id = current_user.id
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"push_subscriptions": {"endpoint": subscription.endpoint}}},
    )

    return {"message": "Unsubscribed successfully"}
