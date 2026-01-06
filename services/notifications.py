import json
import logging
from datetime import datetime, timezone

from pymongo import AsyncMongoClient
from pywebpush import WebPushException, webpush

from app.config import get_settings

settings = get_settings()


async def check_overdue_reviews():
    """
    Background job to check for overdue reviews and send push notifications.
    """
    mongo_host = settings.MONGO_HOST
    client = AsyncMongoClient(mongo_host)
    try:
        db = client["lingua-tile"]
        user_collection = db["users"]
        lesson_review_collection = db["lesson_reviews"]

        vapid_private_key = settings.VAPID_PRIVATE_KEY
        vapid_claims = settings.VAPID_CLAIMS_SUB

        if not vapid_private_key:
            logging.warning("VAPID_PRIVATE_KEY not set, skipping push notifications.")
            return

        logging.info("Starting overdue review check...")

        # Find users with subscriptions
        async for user in user_collection.find(
            {"push_subscriptions": {"$exists": True, "$not": {"$size": 0}}}
        ):
            user_id = user["_id"]
            username = user.get("username", "Unknown")

            # Count overdue reviews
            # user_id from mongo is ObjectId.
            # Convert to string if your lesson_reviews collection uses string user_ids.
            # If it uses ObjectId, use user_id directly.
            # Based on existing code comment, assuming string.
            # We check both to be safe during migration/uncertainty, or just string if confident.
            # Let's try to match string first as per previous code.

            # Note: Previously it was str(user_id).
            overdue_count = await lesson_review_collection.count_documents(
                {
                    "user_id": str(user_id),
                    "next_review": {"$lte": datetime.now(timezone.utc)},
                }
            )

            if overdue_count > 0:
                logging.info(
                    f"User {username} has {overdue_count} overdue reviews. Sending notification."
                )
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
                            logging.info(f"Subscription expired for user {username}")
                            subs_changed = True
                        else:
                            # Keep it and log error
                            logging.error(f"WebPush Error for user {username}: {e}")
                            new_subs.append(sub)
                    except Exception as e:
                        logging.error(f"Error sending push to {username}: {e}")
                        new_subs.append(sub)

                if subs_changed:
                    await user_collection.update_one(
                        {"_id": user_id}, {"$set": {"push_subscriptions": new_subs}}
                    )
            else:
                logging.debug(f"User {username} has no overdue reviews.")

    except Exception as e:
        logging.error(f"Error in check_overdue_reviews: {e}")
    finally:
        await client.close()
