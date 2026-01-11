import pytest
from bson import ObjectId

from app.security import pwd_context
from tests.factories import LessonFactory, UserFactory


@pytest.mark.asyncio
async def test_get_all_lessons(client, db):
    # Setup
    l1 = LessonFactory.build(title="Lesson 1", order_index=1)
    l2 = LessonFactory.build(title="Lesson 2", order_index=2)

    await db["lessons"].insert_one(l1.model_dump(by_alias=True, exclude={"id"}))
    await db["lessons"].insert_one(l2.model_dump(by_alias=True, exclude={"id"}))

    response = await client.get("/api/lessons/all")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Lesson 1"
    assert data[1]["title"] == "Lesson 2"


@pytest.mark.asyncio
async def test_create_lesson_admin(client, db):
    # Setup Admin
    hashed = pwd_context.hash("adminpass")
    admin = UserFactory.build(roles=["admin"], password=hashed)
    await db["users"].insert_one(admin.model_dump(by_alias=True, exclude={"id"}))

    login_res = await client.post(
        "/api/auth/login", json={"username": admin.username, "password": "adminpass"}
    )
    token = login_res.json()["token"]

    data = {
        "title": "New Lesson",
        "category": "grammar",
        "sentences": [],
        "order_index": 1,
    }
    response = await client.post(
        "/api/lessons/create", json=data, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    res_data = response.json()
    assert res_data["title"] == "New Lesson"
    assert res_data["category"] == "grammar"
    assert "_id" in res_data


@pytest.mark.asyncio
async def test_create_lesson_user_forbidden(client, db):
    # Setup User
    hashed = pwd_context.hash("userpass")
    user = UserFactory.build(roles=["user"], password=hashed)
    await db["users"].insert_one(user.model_dump(by_alias=True, exclude={"id"}))

    login_res = await client.post(
        "/api/auth/login", json={"username": user.username, "password": "userpass"}
    )
    token = login_res.json()["token"]

    data = {"title": "New Lesson", "category": "grammar"}
    response = await client.post(
        "/api/lessons/create", json=data, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_lessons_by_category(client, db):
    # Setup
    l1 = LessonFactory.build(title="Grammar 1", category="grammar")
    l2 = LessonFactory.build(title="Practice 1", category="practice")

    await db["lessons"].insert_one(l1.model_dump(by_alias=True, exclude={"id"}))
    await db["lessons"].insert_one(l2.model_dump(by_alias=True, exclude={"id"}))

    response = await client.get("/api/lessons/by-category/grammar")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Grammar 1"


@pytest.mark.asyncio
async def test_review_lesson(client, db):
    # Setup User
    hashed = pwd_context.hash("pw")
    user = UserFactory.build(password=hashed, xp=0)
    user_id = str(ObjectId())
    user_dict = user.model_dump(by_alias=True, exclude={"id"})
    user_dict["_id"] = ObjectId(user_id)
    await db["users"].insert_one(user_dict)

    # Setup Lesson
    lesson = LessonFactory.build(category="grammar")
    lesson_id = str(ObjectId())
    lesson_dict = lesson.model_dump(by_alias=True, exclude={"id"})
    lesson_dict["_id"] = ObjectId(lesson_id)
    await db["lessons"].insert_one(lesson_dict)

    # Login
    login_res = await client.post(
        "/api/auth/login", json={"username": user.username, "password": "pw"}
    )
    token = login_res.json()["token"]

    response = await client.post(
        "/api/lessons/review",
        json={"lesson_id": lesson_id, "overall_performance": 3},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["xp_gained"] == 20  # Grammar first time = 20 XP

    # DB Confirmation
    updated_user = await db["users"].find_one({"_id": ObjectId(user_id)})
    assert updated_user["xp"] == 20
    assert lesson_id in updated_user["completed_lessons"]
