from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.cards import router as cards_router
from api.lessons import router as lessons_router
from api.translations import router as translations_router

title = "Japanese Flashcards API"
description = "An API for creating and studying Japanese flashcards"
app = FastAPI(title=title, description=description, version="0.1.0")
app.include_router(cards_router)
app.include_router(lessons_router)
app.include_router(translations_router)
origins = ["http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"])


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Hello World"}
