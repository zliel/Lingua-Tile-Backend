from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.cards import router as cards_router
from api.lessons import router as lessons_router
from api.translations import router as translations_router

app = FastAPI()
app.include_router(cards_router)
app.include_router(lessons_router)
app.include_router(translations_router)
origins = ["http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"])

@app.get("/")
async def root():
    return {"message": "Hello World"}


