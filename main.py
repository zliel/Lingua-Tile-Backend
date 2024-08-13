from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.cards import router as cards_router
from api.lessons import router as lessons_router
from api.translations import router as translations_router
from api.auth import router as auth_router
from api.users import router as users_router

title = "LinguaTile API"
description = "An API used by LinguaTile to aid in studying Japanese"
app = FastAPI(title=title, description=description, version="0.1.0")
app.include_router(cards_router)
app.include_router(lessons_router)
app.include_router(translations_router)
app.include_router(auth_router)
app.include_router(users_router)
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Hello World"}
