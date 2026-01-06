import pytest

from models.cards import Card
from models.lesson_review import LessonReview
from models.lessons import Lesson
from models.sections import Section
from models.users import User
from tests.factories import (
    CardFactory,
    LessonFactory,
    LessonReviewFactory,
    SectionFactory,
    UserFactory,
)


@pytest.mark.asyncio
async def test_factories_build():
    user = UserFactory.build()
    assert isinstance(user, User)
    assert user.username is not None

    lesson = LessonFactory.build()
    assert isinstance(lesson, Lesson)
    assert lesson.title is not None

    lesson_review = LessonReviewFactory.build()
    assert isinstance(lesson_review, LessonReview)
    assert lesson_review is not None

    card = CardFactory.build()
    assert isinstance(card, Card)
    assert card is not None

    section = SectionFactory.build()
    assert isinstance(section, Section)
    assert section.name is not None


@pytest.mark.asyncio
async def test_client_fixture(client):
    response = await client.get("/")
    assert response.status_code == 200
