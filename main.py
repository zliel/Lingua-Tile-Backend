import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from api.auth import router as auth_router
from api.cards import router as cards_router
from api.lessons import router as lessons_router
from api.sections import router as section_router
from api.translations import router as translations_router
from api.users import router as users_router

title = "LinguaTile API"
description = "An API used by LinguaTile to aid in studying Japanese"
app = FastAPI(title=title, description=description, version="0.8.0")
app.include_router(cards_router)
app.include_router(lessons_router)
app.include_router(translations_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(section_router)
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Hello World, testing!!!"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    logging.error(f"{request}: {exc_str}")
    content = {"status_code": 422, "message": exc_str, "data": None}
    return JSONResponse(
        content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )
