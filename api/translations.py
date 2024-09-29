import os

import requests
from dotenv import load_dotenv
from fastapi import APIRouter

load_dotenv(".env")
router = APIRouter(prefix="/api/translations", tags=["Translations"])
host = "deep-translate1.p.rapidapi.com"
api_key = os.getenv("API_KEY")
headers = {
    "x-rapidapi-host": host,
    "x-rapidapi-key": api_key,
    "content-type": "application/json",
}

payload = {"q": "Hello, world!", "source": "en", "target": "es"}


@router.get("/{src_text}/{src_lang}/{target_lang}", tags=["Translations"])
async def translate(src_text: str, src_lang: str, target_lang: str) -> dict:
    """Translate text from one language to another"""
    url = f"https://{host}/language/translate/v2"
    querystring = {"q": src_text, "target": target_lang, "source": "en"}
    response = requests.request("POST", url, headers=headers, json=querystring)

    translation_container = response.json()["data"]["translations"]
    translation = translation_container

    translation_response = {
        "sourceText": src_text,
        "sourceLanguage": src_lang,
        "translatedText": translation["translatedText"],
        "targetLanguage": target_lang,
    }

    return translation_response


@router.get("/languages", tags=["Translations"])
async def get_languages() -> list:
    # url = f"https://{host}/language/translate/v2/languages"
    # response = requests.request("GET", url, headers=headers)
    # filter the response to only return english and japanese

    # languages = response.json()["languages"]
    # languages = [lang for lang in languages if lang["language"] in ["en", "ja"]]
    # Calling the deep-translate API to get a list of languages is costly, so we'll just return English and Japanese
    # until I figure out whether I want to cache the results or save them in a MongoDB collection

    languages = [
        {"language": "en", "name": "English"},
        {"language": "ja", "name": "Japanese"},
    ]
    return languages
