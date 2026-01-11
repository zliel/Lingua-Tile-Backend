from bson import ObjectId
from fastapi import HTTPException
from pymongo.asynchronous.collection import AsyncCollection

from app.security import pwd_context
from models.update_user import UpdateUser
from models.users import User
from services.base import BaseService


class UserService(BaseService):
    @property
    def collection(self) -> AsyncCollection:
        return self.db["users"]

    async def create_user(self, user: User) -> User:
        if await self.collection.find_one({"username": user.username}):
            raise HTTPException(status_code=400, detail="Username already exists")

        if not user.email:
            raise HTTPException(status_code=400, detail="Email is required")

        if await self.collection.find_one({"email": user.email}):
            raise HTTPException(status_code=400, detail="Email already exists")

        if not user.password:
            raise HTTPException(status_code=400, detail="Password is required")

        user.hash_password()
        await self.collection.insert_one(user.model_dump(by_alias=True, exclude={"id"}))

        if hasattr(user, "password"):
            del user.password

        return user

    async def get_user_by_id(self, user_id: str) -> User:
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise HTTPException(
                status_code=404, detail=f"User with id {user_id} not found"
            )
        return User(**user)

    async def get_all_users(self) -> list[User]:
        users = await self.collection.find().to_list(length=None)
        return [User(**user) for user in users]

    async def update_user(self, user_id: str, updated_info: UpdateUser) -> User:
        user_info_to_update = {
            k: v for k, v in updated_info.model_dump().items() if v is not None
        }

        if "password" in user_info_to_update:
            if user_info_to_update["password"].strip() != "":
                user_info_to_update["password"] = pwd_context.hash(
                    user_info_to_update["password"]
                )
            else:
                del user_info_to_update["password"]

        old_user = await self.collection.find_one_and_update(
            {"_id": ObjectId(user_id)}, {"$set": user_info_to_update}
        )
        if old_user is None:
            raise HTTPException(
                status_code=404, detail=f"User with id {user_id} not found"
            )

        updated_user = await self.collection.find_one({"_id": ObjectId(user_id)})
        return User(**updated_user)

    async def delete_user(self, user_id: str) -> None:
        result = await self.collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404, detail=f"User with id {user_id} not found"
            )

    async def reset_progress(self, user_id: str) -> None:
        lesson_review_collection = self.db["lesson_reviews"]
        review_logs_collection = self.db["review_logs"]

        await lesson_review_collection.delete_many({"user_id": user_id})
        await review_logs_collection.delete_many({"user_id": user_id})

        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"xp": 0, "completed_lessons": [], "level": 1}},
        )

    async def get_user_activity(self, user_id: str) -> list[dict]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$review_date"}
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        review_collection: AsyncCollection = self.db["review_logs"]
        agg_result = await review_collection.aggregate(pipeline)
        activity_data = await agg_result.to_list(length=None)

        return [{"date": item["_id"], "count": item["count"]} for item in activity_data]
