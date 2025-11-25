from typing import List, Optional

import jaconv
import unicodedata
from MeCab import Tagger
from bson import ObjectId
from pydantic import BaseModel, Field

from .py_object_id import PyObjectId

tagger = Tagger("")


# Helper function to split a sentence into words using MeCab
def split_sentence(sentence: str) -> List[str]:
    words = []
    nodes = tagger.parseToNode(sentence)

    while nodes:
        if nodes.surface == "":
            nodes = nodes.next
            continue

        # Handle kanji
        if any(
            [
                unicodedata.name(char).startswith("CJK UNIFIED IDEOGRAPH")
                for char in nodes.surface
            ]
        ):
            # Add the kanji
            word_to_append = nodes.surface
            # Add the kanji's furigana if it exists
            if nodes.feature.split(",")[9] != "*":
                # If the last char in the furigana is the same as the last character of the word, remove the last character
                if word_to_append[-1] == jaconv.kata2hira(
                    nodes.feature.split(",")[9][-1]
                ):
                    word_to_append += (
                        f"({jaconv.kata2hira(nodes.feature.split(',')[9][:-1])})"
                    )
                else:  # Otherwise, add the furigana
                    word_to_append += (
                        f"({jaconv.kata2hira(nodes.feature.split(',')[9])})"
                    )
            words.append(word_to_append)
        else:
            # The word is kana or punctuation
            word_to_append = nodes.surface
            words.append(word_to_append)

        nodes = nodes.next

    return words


class Sentence(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=str(ObjectId()))
    full_sentence: str = Field(...)
    possible_answers: List[str] = Field(...)
    words: List[str] = Field(default=[])

    @classmethod
    def create(cls, full_sentence: str, possible_answers=None, words=None):
        if possible_answers is None:
            possible_answers = []
        words = split_sentence(full_sentence)
        return cls(
            _id=str(ObjectId()),
            full_sentence=full_sentence,
            possible_answers=possible_answers,
            words=words,
        )

    class Config:
        arbitrary_types_allowed = True
        validate_by_name = True
        json_encoders = {ObjectId: lambda oid: str(oid)}
        json_schema_extra = {
            "example": {
                "full_sentence": "私は学生です",
                "possible_answers": [
                    "I am a student",
                    "I'm a student",
                    "I am a pupil",
                    "I'm a pupil",
                ],
                "words": ["私", "は", "がくせい", "です"],
            }
        }
