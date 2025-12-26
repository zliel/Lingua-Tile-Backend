from bson import ObjectId
from fastapi import APIRouter, status, HTTPException, Depends, Request
from typing import List, Dict
from pymongo.asynchronous.collection import AsyncCollection

from api.dependencies import (
    get_db,
    get_current_user as get_client,
    pwd_context,
    RoleChecker,
)
from app.limiter import limiter
from models import User, PyObjectId, UpdateUser

router = APIRouter(prefix="/api/users", tags=["Users"])


def is_admin(user: User):
    return "admin" in user.roles


@router.post("/signup", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_user(request: Request, user: User, db=Depends(get_db)):
    """Create a new user in the database"""
    user_collection = db["users"]

    if await user_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already exists")

    user.hash_password()
    await user_collection.insert_one(user.model_dump(by_alias=True, exclude={"id"}))

    return user


@router.get("/activity", response_model=List[Dict[str, str | int]])
@limiter.limit("10/minute")
async def get_user_activity(
    request: Request,
    current_user: User = Depends(get_client),
    db=Depends(get_db),
):
    """Retrieve user activity map (reviews per day)"""
    pipeline = [
        {"$match": {"user_id": current_user.id}},
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

    review_collection: AsyncCollection = db["review_logs"]

    agg_result = await review_collection.aggregate(pipeline)
    activity_data = await agg_result.to_list(length=None)

    return [{"date": item["_id"], "count": item["count"]} for item in activity_data]


@router.get("/", response_model=User, response_model_exclude={"password"})
@limiter.limit("15/minute")
async def get_current_user(request: Request, current_user: User = Depends(get_client)):
    """Retrieve the current user"""
    return current_user


@router.get(
    "/{user_id}",
    response_model=User,
    response_model_exclude={"password"},
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("10/minute")
async def get_user(
    request: Request,
    user_id: PyObjectId,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Retrieve a user from the database by id"""
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user")

    user_collection = db["users"]

    user = await user_collection.find_one({"_id": ObjectId(user_id)})
    return User(**user)


@router.get(
    "/admin/all",
    response_model=list[User],
    response_model_exclude={"password"},
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("10/minute")
async def get_all_users(
    request: Request, current_user: User = Depends(get_current_user), db=Depends(get_db)
):
    """Retrieve all users from the database"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to view all users")

    user_collection = db["users"]
    users = await user_collection.find().to_list(length=None)

    return [User(**user) for user in users]


@router.put(
    "/update/{user_id}", response_model=User, response_model_exclude={"password"}
)
@limiter.limit("5/minute")
async def update_user(
    request: Request,
    user_id: PyObjectId,
    updated_info: UpdateUser,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Update a user in the database by id"""
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

    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this user"
        )

    user_collection = db["users"]
    old_user = await user_collection.find_one_and_update(
        {"_id": ObjectId(user_id)}, {"$set": user_info_to_update}
    )
    if old_user is None:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

    updated_user = await user_collection.find_one({"_id": ObjectId(user_id)})
    return User(**updated_user)


@router.delete("/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def delete_user(
    request: Request,
    user_id: PyObjectId,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete a user from the database by id"""
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this user"
        )

    user_collection = db["users"]
    result = await user_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
    # user = user_collection.find_one_and_delete({"_id": user_id})

    # if user is None:
    #     raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
