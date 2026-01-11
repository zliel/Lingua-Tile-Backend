from pymongo.asynchronous.database import AsyncDatabase


class BaseService:
    def __init__(self, db: AsyncDatabase):
        self.db = db
