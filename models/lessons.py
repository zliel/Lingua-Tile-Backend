from bson.objectid import ObjectId


class Lesson:
    def __init__(self, name: str, cards: list = None, _id: str = None):
        self.name = name
        self.cards = cards if cards else []
        self._id = _id if _id else str(ObjectId())
