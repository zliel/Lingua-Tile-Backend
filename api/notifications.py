import os

from fastapi import APIRouter, Depends, status, HTTPException

from api.dependencies import get_current_user
from models import User
from models.users import PushSubscription
from pymongo import AsyncMongoClient

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

mongo_host = os.getenv("MONGO_HOST")
client = AsyncMongoClient(mongo_host)
db = client["lingua-tile"]
user_collection = db["users"]


@router.get("/vapid-public-key")
async def get_vapid_public_key():
    key = os.getenv("VAPID_PUBLIC_KEY", "")
    print(
        f"DEBUG: Serving VAPID Public Key: {key[:10]}... (len={len(key) if key else 0})"
    )
    return {"publicKey": key}


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe(
    subscription: PushSubscription, current_user: User = Depends(get_current_user)
):
    """
    Subscribe a user to push notifications.
    """
    user_id = current_user.id
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    # Add subscription to user's list if it doesn't exist
    await user_collection.update_one(
        {"_id": user_id, "push_subscriptions.endpoint": {"$ne": subscription.endpoint}},
        {"$push": {"push_subscriptions": subscription.model_dump()}},
    )

    return {"message": "Subscribed successfully"}


@router.post("/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe(
    subscription: PushSubscription, current_user: User = Depends(get_current_user)
):
    """
    Unsubscribe a user from push notifications.
    """
    user_id = current_user.id
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    await user_collection.update_one(
        {"_id": user_id},
        {"$pull": {"push_subscriptions": {"endpoint": subscription.endpoint}}},
    )

    return {"message": "Unsubscribed successfully"}
