from datetime import datetime
from httpx import AsyncClient
import pytest
from tests.factories import UserFactory
from bson import ObjectId

from api.dependencies import pwd_context


@pytest.mark.asyncio
async def test_signup_user(client, db):
    new_user_data = {
        "username": "newuser",
        "password": "newpassword",
        "roles": ["user"],
        "timezone": "UTC",
        "push_subscriptions": [],
        "completed_lessons": [],
    }
    response = await client.post("/api/users/signup", json=new_user_data)

    assert response.status_code == 201
    data = response.json()
    print(data)
    assert data["username"] == "newuser"
    assert "_id" in data
    assert "password" not in data

    user_in_db = await db["users"].find_one({"username": "newuser"})
    assert user_in_db is not None
    assert pwd_context.verify("newpassword", user_in_db["password"])


@pytest.mark.asyncio
async def test_get_current_user_profile(client, db):
    # Setup
    password = "secure"
    hashed = pwd_context.hash(password)
    user = UserFactory.build(password=hashed)
    await db["users"].insert_one(user.model_dump(by_alias=True, exclude={"id"}))

    # Login
    login_res = await client.post(
        "/api/auth/login", json={"username": user.username, "password": password}
    )
    token = login_res.json()["token"]

    response = await client.get(
        "/api/users/", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == user.username
    assert data["timezone"] == user.timezone


@pytest.mark.asyncio
async def test_admin_get_all_users(client, db):
    # Setup Admin
    admin_pw = "adminpw"
    admin = UserFactory.build(password=pwd_context.hash(admin_pw), roles=["admin"])
    await db["users"].insert_one(admin.model_dump(by_alias=True, exclude={"id"}))

    # Setup Normal User
    user = UserFactory.build()
    await db["users"].insert_one(user.model_dump(by_alias=True, exclude={"id"}))

    # Login Admin
    login_res = await client.post(
        "/api/auth/login", json={"username": admin.username, "password": admin_pw}
    )
    print(f"login_res: {login_res}")
    token = login_res.json()["token"]

    response = await client.get(
        "/api/users/admin/all", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2  # At least admin and user


@pytest.mark.asyncio
async def test_user_cannot_view_other_user(client, db):
    # Setup User 1
    pw1 = "pw1"
    u1 = UserFactory.build(password=pwd_context.hash(pw1))
    # We need known IDs for this test to match what we put in DB
    u1_id = ObjectId()
    u1_dict = u1.model_dump(by_alias=True, exclude={"id"})
    u1_dict["_id"] = u1_id
    await db["users"].insert_one(u1_dict)

    # Setup User 2
    u2 = UserFactory.build()
    u2_id = ObjectId()
    u2_dict = u2.model_dump(by_alias=True, exclude={"id"})
    u2_dict["_id"] = u2_id
    await db["users"].insert_one(u2_dict)

    # Login User 1
    login_res = await client.post(
        "/api/auth/login", json={"username": u1.username, "password": pw1}
    )
    token = login_res.json()["token"]

    # User 1 tries to access User 2
    response = await client.get(
        f"/api/users/{str(u2_id)}", headers={"Authorization": f"Bearer {token}"}
    )

    # Verify fail
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_reset_user_progress(client: AsyncClient, db):
    hashed = pwd_context.hash("testpass")
    user = UserFactory.build(password=hashed, xp=100)
    user_id = str(ObjectId())
    user_data = user.model_dump(by_alias=True, exclude={"id"})
    user_data["_id"] = ObjectId(user_id)
    await db["users"].insert_one(user_data)

    login_res = await client.post(
        "/api/auth/login", json={"username": user.username, "password": "testpass"}
    )
    token = login_res.json()["token"]

    # Add a lesson review
    lesson_review_collection = db["lesson_reviews"]
    await lesson_review_collection.insert_one(
        {
            "user_id": user_id,
            "lesson_id": user_id,
            "completed_at": datetime.now(),
        }
    )

    # Add a review log
    review_collection = db["review_logs"]
    await review_collection.insert_one(
        {
            "user_id": user_id,
            "lesson_id": user_id,
            "review_date": datetime.now(),
            "rating": 5,
        }
    )

    user_before = await db["users"].find_one({"_id": ObjectId(user_id)})
    assert user_before["xp"] == 100
    count_before = await review_collection.count_documents({"user_id": user_id})
    assert count_before > 0

    response = await client.post(
        "/api/users/reset-progress", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    user_after = await db["users"].find_one({"_id": ObjectId(user_id)})
    assert user_after["xp"] == 0
    count_after = await review_collection.count_documents({"user_id": user_id})
    assert count_after == 0
