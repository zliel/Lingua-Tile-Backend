import pytest
from tests.factories import CardFactory, UserFactory, LessonFactory
from bson import ObjectId
from api.dependencies import pwd_context


@pytest.mark.asyncio
async def test_get_all_cards_admin(client, db):
    # Setup Admin
    hashed = pwd_context.hash("adminpw")
    admin = UserFactory.build(roles=["admin"], password=hashed)
    await db["users"].insert_one(admin.model_dump(by_alias=True, exclude={"id"}))
    token = (
        await client.post(
            "/api/auth/login", json={"username": admin.username, "password": "adminpw"}
        )
    ).json()["token"]

    # Setup Data
    c1 = CardFactory.build(front_text="C1")
    c2 = CardFactory.build(front_text="C2")
    await db["cards"].insert_one(c1.model_dump(by_alias=True, exclude={"id"}))
    await db["cards"].insert_one(c2.model_dump(by_alias=True, exclude={"id"}))

    response = await client.get(
        "/api/cards/all", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_create_card_admin(client, db):
    # Setup Admin
    hashed = pwd_context.hash("adminpw")
    admin = UserFactory.build(roles=["admin"], password=hashed)
    await db["users"].insert_one(admin.model_dump(by_alias=True, exclude={"id"}))
    token = (
        await client.post(
            "/api/auth/login", json={"username": admin.username, "password": "adminpw"}
        )
    ).json()["token"]

    data = {"front_text": "New Front", "back_text": "New Back", "lesson_ids": []}
    response = await client.post(
        "/api/cards/create", json=data, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    assert response.json()["front_text"] == "New Front"


@pytest.mark.asyncio
async def test_update_card_admin(client, db):
    # Setup Admin
    hashed = pwd_context.hash("adminpw")
    admin = UserFactory.build(roles=["admin"], password=hashed)
    await db["users"].insert_one(admin.model_dump(by_alias=True, exclude={"id"}))
    token = (
        await client.post(
            "/api/auth/login", json={"username": admin.username, "password": "adminpw"}
        )
    ).json()["token"]

    # Setup Card and Lesson
    lesson = LessonFactory.build(title="Target Lesson")
    lesson_id = ObjectId()
    await db["lessons"].insert_one(
        {"_id": lesson_id, **lesson.model_dump(by_alias=True, exclude={"id"})}
    )

    card = CardFactory.build(front_text="Old Front")
    card_id = ObjectId()
    await db["cards"].insert_one(
        {"_id": card_id, **card.model_dump(by_alias=True, exclude={"id"})}
    )

    data = {"front_text": "Updated Front", "lesson_ids": [str(lesson_id)]}
    response = await client.put(
        f"/api/cards/update/{str(card_id)}",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["front_text"] == "Updated Front"

    updated_lesson = await db["lessons"].find_one({"_id": lesson_id})
    assert str(card_id) in updated_lesson["card_ids"]


@pytest.mark.asyncio
async def test_delete_card_admin(client, db):
    # Setup Admin
    hashed = pwd_context.hash("adminpw")
    admin = UserFactory.build(roles=["admin"], password=hashed)
    await db["users"].insert_one(admin.model_dump(by_alias=True, exclude={"id"}))
    token = (
        await client.post(
            "/api/auth/login", json={"username": admin.username, "password": "adminpw"}
        )
    ).json()["token"]

    # Setup Card
    card = CardFactory.build()
    card_id = ObjectId()
    await db["cards"].insert_one(
        {"_id": card_id, **card.model_dump(by_alias=True, exclude={"id"})}
    )

    response = await client.delete(
        f"/api/cards/delete/{str(card_id)}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    assert await db["cards"].find_one({"_id": card_id}) is None


@pytest.mark.asyncio
async def test_get_cards_by_ids_preserves_order(client, db):
    # Setup
    c1 = CardFactory.build(front_text="C1")
    c2 = CardFactory.build(front_text="C2")
    c1_id = ObjectId()
    c2_id = ObjectId()

    await db["cards"].insert_one(
        {"_id": c1_id, **c1.model_dump(by_alias=True, exclude={"id"})}
    )
    await db["cards"].insert_one(
        {"_id": c2_id, **c2.model_dump(by_alias=True, exclude={"id"})}
    )

    ids = [str(c2_id), str(c1_id)]
    response = await client.post("/api/cards/by-ids", json=ids)

    assert response.status_code == 200
    data = response.json()
    assert data[0]["_id"] == str(c2_id)
    assert data[1]["_id"] == str(c1_id)
