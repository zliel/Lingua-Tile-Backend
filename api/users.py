from fastapi import APIRouter, status, HTTPException, Depends

from api.dependencies import get_db, get_current_user, pwd_context
from models import User, PyObjectId, UpdateUser

router = APIRouter(prefix="/api/users", tags=["Users"])


def is_admin(user: User):
    return "admin" in user.roles


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user(user: User, db=Depends(get_db)):
    """Create a new user in the database"""
    user_collection = db['users']

    if user_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already exists")

    user.hash_password()
    user_collection.insert_one(user.dict(by_alias=True))

    return user


@router.get("/", response_model=User, response_model_exclude={"password"})
async def get_current_user(current_user: User = Depends(get_current_user)):
    """Retrieve the current user"""
    if current_user is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return current_user


@router.get("/{user_id}", response_model=User, response_model_exclude={"password"})
async def get_user(user_id: PyObjectId, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """Retrieve a user from the database by id"""
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user")

    user_collection = db['users']

    user = user_collection.find_one({"_id": user_id})
    return User(**user)


@router.get("/admin/all", response_model=list[User], response_model_exclude={"password"})
async def get_all_users(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """Retrieve all users from the database"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to view all users")

    user_collection = db['users']
    users = user_collection.find()
    user_list = []
    for user in users:
        if user is not None:
            user_list.append(User(**user))
        else:
            raise HTTPException(status_code=404, detail="No users found")

    return user_list


@router.put("/update/{user_id}", response_model=User, response_model_exclude={"password"})
async def update_user(user_id: PyObjectId, updated_info: UpdateUser, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """Update a user in the database by id"""
    user_info_to_update = {k: v for k, v in updated_info.dict().items() if v is not None}

    if "password" in user_info_to_update:
        if user_info_to_update["password"].strip() != "":
            user_info_to_update["password"] = pwd_context.hash(user_info_to_update["password"])
        else:
            del user_info_to_update["password"]

    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    user_collection = db['users']
    old_user = user_collection.find_one_and_update({"_id": user_id}, {"$set": user_info_to_update})
    if old_user is None:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

    updated_user = user_collection.find_one({"_id": user_id})
    return User(**updated_user)


@router.delete("/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: PyObjectId, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """Delete a user from the database by id"""
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")

    user_collection = db['users']
    user = user_collection.find_one_and_delete({"_id": user_id})

    if user is None:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
