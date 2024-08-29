from pymongo import MongoClient
import dotenv


def get_db():
    mongo_host = dotenv.get_key(".env", "MONGO_HOST")
    client = MongoClient(mongo_host)
    db = client['lingua-tile']
    return db

