import pytest
from tests.factories import SectionFactory, UserFactory, LessonFactory, CardFactory
from bson import ObjectId
from api.dependencies import pwd_context


@pytest.mark.asyncio
async def test_create_section_admin(client, db):
    # Setup Admin
    hashed = pwd_context.hash("adminpass")
    admin = UserFactory.build(roles=["admin"], password=hashed)
    await db["users"].insert_one(admin.model_dump(by_alias=True, exclude={"id"}))

    login_res = await client.post(
        "/api/auth/login", json={"username": admin.username, "password": "adminpass"}
    )
    if login_res.status_code != 200:
        print(f"Login failed: {login_res.status_code} {login_res.text}")
    token = login_res.json()["token"]

    data = {"name": "New Section", "order_index": 1}
    response = await client.post(
        "/api/sections/create", json=data, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    res_data = response.json()
    assert res_data["name"] == "New Section"
    assert "_id" in res_data


@pytest.mark.asyncio
async def test_update_section_move_lessons(client, db):
    # Setup Admin
    hashed = pwd_context.hash("adminpass")
    admin = UserFactory.build(roles=["admin"], password=hashed)
    await db["users"].insert_one(admin.model_dump(by_alias=True, exclude={"id"}))

    login_res = await client.post(
        "/api/auth/login", json={"username": admin.username, "password": "adminpass"}
    )
    token = login_res.json()["token"]

    # Setup Data
    sec1 = SectionFactory.build(name="Section 1", lesson_ids=[])
    sec2 = SectionFactory.build(name="Section 2", lesson_ids=[])
    lesson = LessonFactory.build(title="Moving Lesson")

    sec1_id = ObjectId()
    sec2_id = ObjectId()
    lesson_id = ObjectId()

    sec1_data = sec1.model_dump(by_alias=True, exclude={"id"})
    sec1_data["_id"] = sec1_id
    sec1_data["lesson_ids"] = [str(lesson_id)]

    sec2_data = sec2.model_dump(by_alias=True, exclude={"id"})
    sec2_data["_id"] = sec2_id

    lesson_data = lesson.model_dump(by_alias=True, exclude={"id"})
    lesson_data["_id"] = lesson_id
    lesson_data["section_id"] = str(sec1_id)

    await db["sections"].insert_one(sec1_data)
    await db["sections"].insert_one(sec2_data)
    await db["lessons"].insert_one(lesson_data)

    update_data = {"lesson_ids": [str(lesson_id)]}
    response = await client.put(
        f"/api/sections/update/{str(sec2_id)}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    updated_lesson = await db["lessons"].find_one({"_id": lesson_id})
    assert updated_lesson["section_id"] == sec2_id
    updated_sec1 = await db["sections"].find_one({"_id": sec1_id})
    assert str(lesson_id) not in updated_sec1["lesson_ids"]
    updated_sec2 = await db["sections"].find_one({"_id": sec2_id})
    assert str(lesson_id) in updated_sec2["lesson_ids"]


@pytest.mark.asyncio
async def test_delete_section_admin(client, db):
    # Setup Admin
    hashed = pwd_context.hash("adminpass")
    admin = UserFactory.build(roles=["admin"], password=hashed)
    await db["users"].insert_one(admin.model_dump(by_alias=True, exclude={"id"}))
    token = (
        await client.post(
            "/api/auth/login",
            json={"username": admin.username, "password": "adminpass"},
        )
    ).json()["token"]

    # Setup Section
    sec = SectionFactory.build()
    sec_id = ObjectId()
    await db["sections"].insert_one(
        {"_id": sec_id, **sec.model_dump(by_alias=True, exclude={"id"})}
    )

    response = await client.delete(
        f"/api/sections/delete/{str(sec_id)}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    found = await db["sections"].find_one({"_id": sec_id})
    assert found is None


@pytest.mark.asyncio
async def test_download_section_structure(client, db):
    # Setup
    sec = SectionFactory.build(name="DL Section")
    sec_id = ObjectId()
    lesson = LessonFactory.build(title="DL Lesson")
    lesson_id = ObjectId()
    card = CardFactory.build(front_text="Front")
    card_id = ObjectId()

    # Link them
    sec_data = sec.model_dump(by_alias=True, exclude={"id"})
    sec_data["_id"] = sec_id
    sec_data["lesson_ids"] = [str(lesson_id)]

    lesson_data = lesson.model_dump(by_alias=True, exclude={"id"})
    lesson_data["_id"] = lesson_id
    lesson_data["section_id"] = sec_id
    lesson_data["card_ids"] = [str(card_id)]

    card_data = card.model_dump(by_alias=True, exclude={"id"})
    card_data["_id"] = card_id
    card_data["lesson_ids"] = [str(lesson_id)]

    await db["sections"].insert_one(sec_data)
    await db["lessons"].insert_one(lesson_data)
    await db["cards"].insert_one(card_data)

    # Execute
    response = await client.get(f"/api/sections/{str(sec_id)}/download")

    assert response.status_code == 200
    data = response.json()
    assert data["section"]["_id"] == str(sec_id)
    assert len(data["lessons"]) == 1
    assert data["lessons"][0]["_id"] == str(lesson_id)
    assert len(data["cards"]) == 1
    assert data["cards"][0]["_id"] == str(card_id)
