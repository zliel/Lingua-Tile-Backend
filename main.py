import dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()
origins = ["http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"])

host = "deep-translate1.p.rapidapi.com"
api_key = dotenv.get_key(".env", "API_KEY")
headers = {
    "x-rapidapi-host": host,
    "x-rapidapi-key": api_key,
    "content-type": "application/json",
}

payload = {
    "q": "Hello, world!",
    "source": "en",
    "target": "es"
}


@app.get("/")
async def root():
    return {"message": "Hello World"}


# write a function to call the API
@app.get("/translate/{src_text}/{src_lang}/{target_lang}")
async def translate(src_text, src_lang, target_lang):

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


# write a function to call the "/languages" endpoint and return a list of languages
@app.get("/languages")
async def get_languages():
    # url = f"https://{host}/language/translate/v2/languages"
    # response = requests.request("GET", url, headers=headers)
    # # filter the response to only return english and japanese
    # languages = response.json()["languages"]
    # languages = [lang for lang in languages if lang["language"] in ["en", "ja"]]
    languages = [{"language": "en", "name": "English"}, {"language": "ja", "name": "Japanese"}]
    return languages
