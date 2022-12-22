from bson.objectid import ObjectId


class Card:
    def __init__(self, front_text: str, back_text: str, lesson_id: str, _id: str = None):
        self.front_text = front_text
        self.back_text = back_text
        self.lesson_id = lesson_id
        self._id = _id if _id else str(ObjectId())
