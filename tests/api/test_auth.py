import pytest
from tests.factories import UserFactory
from api.dependencies import pwd_context
from bson import ObjectId


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

    # Verify fail code
    assert response.status_code == 403
