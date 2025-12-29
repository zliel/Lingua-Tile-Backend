from models.sections import Section
from polyfactory.factories.pydantic_factory import ModelFactory
from models.users import User
from models.lessons import Lesson
from models.cards import Card
from models.lesson_review import LessonReview


class UserFactory(ModelFactory[User]):
    __model__ = User

    push_subscriptions = []
    completed_lessons = []


class LessonFactory(ModelFactory[Lesson]):
    __model__ = Lesson

    category = "grammar"  # Default value that passes validation
    card_ids = []


class CardFactory(ModelFactory[Card]):
    __model__ = Card

    lesson_ids = []


class LessonReviewFactory(ModelFactory[LessonReview]):
    __model__ = LessonReview


class SectionFactory(ModelFactory):
    __model__ = Section

    lesson_ids = []
