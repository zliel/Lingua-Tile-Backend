from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pywebpush import webpush, WebPushException

from api.auth import router as auth_router
from api.cards import router as cards_router
from api.lessons import router as lessons_router
from api.sections import router as section_router
from api.translations import router as translations_router
from api.users import router as users_router
from api.notifications import router as notifications_router

import logging
import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(".env")

title = "LinguaTile API"
description = "An API used by LinguaTile to aid in studying Japanese"
app = FastAPI(title=title, description=description, version="0.8.0")
app.include_router(cards_router)
app.include_router(lessons_router)
app.include_router(translations_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(section_router)
app.include_router(notifications_router)

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Hello World!"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    logging.error(f"{request}: {exc_str}")
    content = {"status_code": 422, "message": exc_str, "data": None}
    return JSONResponse(
        content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


scheduler = AsyncIOScheduler()


async def check_overdue_reviews():
    """
    Background job to check for overdue reviews and send push notifications.
    """
    from pymongo import AsyncMongoClient

    mongo_host = os.getenv("MONGO_HOST")
    client = AsyncMongoClient(mongo_host)
    db = client["lingua-tile"]
    user_collection = db["users"]
    lesson_review_collection = db["lesson_reviews"]

    vapid_private_key = os.getenv("VAPID_PRIVATE_KEY")
    vapid_claims = {"sub": os.getenv("VAPID_MAILTO", "mailto:zpliel@gmail.com")}

    if not vapid_private_key:
        print("VAPID_PRIVATE_KEY not set, skipping push notifications.")
        return

    # Find users with subscriptions
    async for user in user_collection.find(
        {"push_subscriptions": {"$exists": True, "$not": {"$size": 0}}}
    ):
        user_id = user["_id"]

        # Count overdue reviews
        overdue_count = await lesson_review_collection.count_documents(
            {
                "user_id": str(user_id),
                "next_review": {"$lte": datetime.now(timezone.utc)},
            }
        )

        if overdue_count > 0:
            payload = json.dumps({"count": overdue_count})

            # Send to all subscriptions
            new_subs = []
            param_subs = user.get("push_subscriptions", [])
            subs_changed = False

            for sub in param_subs:
                try:
                    webpush(
                        subscription_info=sub,
                        data=payload,
                        vapid_private_key=vapid_private_key,
                        vapid_claims=vapid_claims.copy(),
                    )
                    new_subs.append(sub)
                except WebPushException as e:
                    if e.response and e.response.status_code == 410:
                        # Subscription expired/gone
                        subs_changed = True
                    else:
                        # Keep it and log error
                        print(f"WebPush Error for user {user['username']}: {e}")
                        new_subs.append(sub)
                except Exception as e:
                    print(f"Error sending push to {user['username']}: {e}")
                    new_subs.append(sub)

            if subs_changed:
                await user_collection.update_one(
                    {"_id": user_id}, {"$set": {"push_subscriptions": new_subs}}
                )


@app.on_event("startup")
async def start_scheduler():
    scheduler.add_job(
        check_overdue_reviews,
        IntervalTrigger(hours=4),  # Check every 4 hours
        id="check_reviews",
        replace_existing=True,
    )
    scheduler.start()
