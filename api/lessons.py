from aiocache import cached
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Request, status

from api.dependencies import (
    RoleChecker,
    get_current_user,
    get_current_user_optional,
    get_lesson_service,
)
from app.limiter import limiter
from models.lessons import Lesson
from models.py_object_id import PyObjectId
from models.update_lesson import UpdateLesson
from models.users import User
from services.lessons import LessonService

load_dotenv(".env")
router = APIRouter(prefix="/api/lessons", tags=["Lessons"])


@router.get("/all", response_model=list[Lesson], status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
@cached(ttl=600, key="all_lessons", alias="default")
async def get_all_lessons(
    request: Request, lesson_service: LessonService = Depends(get_lesson_service)
):
    """Retrieve all lessons from the database"""
    return await lesson_service.get_all_lessons()


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("5/minute")
async def create_lesson(
    request: Request,
    lesson: Lesson,
    lesson_service: LessonService = Depends(get_lesson_service),
):
    """Create a new lesson in the database"""
    return await lesson_service.create_lesson(lesson)


@router.get("/total", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_total_lesson_count(
    request: Request, lesson_service: LessonService = Depends(get_lesson_service)
):
    """Retrieve the total number of lessons in the database"""
    return await lesson_service.get_total_lesson_count()


@router.get("/by-category/{category}")
@limiter.limit("10/minute")
@cached(
    ttl=600,
    key_builder=lambda f, *args, **kwargs: f"category_{kwargs['category'].lower()}",
    alias="default",
)
async def get_lessons_by_category(
    request: Request,
    category: str,
    lesson_service: LessonService = Depends(get_lesson_service),
):
    """Retrieve all lessons from the database by category"""
    return await lesson_service.get_lessons_by_category(category)


@router.get("/review/{lesson_id}", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_lesson_review(
    request: Request,
    lesson_id: PyObjectId,
    current_user: User = Depends(get_current_user),
    lesson_service: LessonService = Depends(get_lesson_service),
):
    """Retrieve a lesson review from the database by lesson id for the current user"""
    return await lesson_service.get_lesson_review(str(lesson_id), str(current_user.id))


@router.get("/reviews", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_lesson_reviews(
    request: Request,
    current_user: User = Depends(get_current_user),
    lesson_service: LessonService = Depends(get_lesson_service),
):
    """Retrieve all lesson reviews from the database"""
    return await lesson_service.get_all_reviews_for_user(str(current_user.id))


@router.get("/{lesson_id}")
@limiter.limit("10/minute")
async def get_lesson(
    request: Request,
    lesson_id: PyObjectId,
    current_user: User | None = Depends(get_current_user_optional),
    lesson_service: LessonService = Depends(get_lesson_service),
):
    """Retrieve a lesson from the database by id"""
    return await lesson_service.get_lesson(str(lesson_id), current_user)


@router.put("/update/{lesson_id}", dependencies=[Depends(RoleChecker(["admin"]))])
@limiter.limit("10/minute")
async def update_lesson(
    request: Request,
    lesson_id: PyObjectId,
    updated_info: UpdateLesson,
    lesson_service: LessonService = Depends(get_lesson_service),
):
    """Update a lesson in the database by id"""
    return await lesson_service.update_lesson(str(lesson_id), updated_info)


@router.delete(
    "/delete/{lesson_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("5/minute")
async def delete_lesson(
    request: Request,
    lesson_id: PyObjectId,
    lesson_service: LessonService = Depends(get_lesson_service),
):
    """Delete a lesson from the database by id"""
    await lesson_service.delete_lesson(str(lesson_id))


# Lesson Review Routes
@router.post("/review", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def review_lesson(
    request: Request,
    current_user: User = Depends(get_current_user),
    lesson_service: LessonService = Depends(get_lesson_service),
):
    # Access the "lesson_id" and "user_id" from the request body
    body = await request.json()
    lesson_id = body["lesson_id"]
    overall_performance = body["overall_performance"]

    return await lesson_service.submit_review(
        str(lesson_id), str(current_user.id), overall_performance, current_user
    )


@router.get("/reviews/history/all", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_review_history(
    request: Request,
    current_user: User = Depends(get_current_user),
    lesson_service: LessonService = Depends(get_lesson_service),
):
    """Retrieve all review logs for the current user to show history"""
    return await lesson_service.get_review_history(str(current_user.id))
