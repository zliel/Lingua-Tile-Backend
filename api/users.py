from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.dependencies import (
    RoleChecker,
    get_user_service,
)
from api.dependencies import (
    get_current_user as get_client,
)
from app.limiter import limiter
from models.py_object_id import PyObjectId
from models.update_user import UpdateUser
from models.users import User
from services.users import UserService

router = APIRouter(prefix="/api/users", tags=["Users"])


def is_admin(user: User):
    return "admin" in user.roles


@router.post("/signup", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_user(
    request: Request, user: User, user_service: UserService = Depends(get_user_service)
):
    """Create a new user in the database"""
    return await user_service.create_user(user)


@router.get("/activity", response_model=list[dict[str, str | int]])
@limiter.limit("10/minute")
async def get_user_activity(
    request: Request,
    current_user: User = Depends(get_client),
    user_service: UserService = Depends(get_user_service),
):
    """Retrieve user activity map (reviews per day)"""
    return await user_service.get_user_activity(str(current_user.id))


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
    user_service: UserService = Depends(get_user_service),
):
    """Retrieve a user from the database by id"""
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user")

    return await user_service.get_user_by_id(str(user_id))


@router.get(
    "/admin/all",
    response_model=list[User],
    response_model_exclude={"password"},
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("10/minute")
async def get_all_users(
    request: Request,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """Retrieve all users from the database"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to view all users")

    return await user_service.get_all_users()


@router.put(
    "/update/{user_id}", response_model=User, response_model_exclude={"password"}
)
@limiter.limit("5/minute")
async def update_user(
    request: Request,
    user_id: PyObjectId,
    updated_info: UpdateUser,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """Update a user in the database by id"""
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this user"
        )

    return await user_service.update_user(str(user_id), updated_info)


@router.delete("/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def delete_user(
    request: Request,
    user_id: PyObjectId,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """Delete a user from the database by id"""
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this user"
        )

    await user_service.delete_user(str(user_id))


@router.post("/reset-progress", status_code=status.HTTP_200_OK)
@limiter.limit("3/hour")
async def reset_user_progress(
    request: Request,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """Reset the current user's progress (reviews and XP)"""
    await user_service.reset_progress(str(current_user.id))

    return {"message": "Progress reset successfully"}

    return {"message": "Progress reset successfully"}
