from typing import Annotated

from pydantic.functional_validators import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(str)]

# class PyObjectId(ObjectId):
#     @classmethod
#     def __get_pydantic_core_schema__(
#         cls, source_type: Any, handler: GetCoreSchemaHandler
#     ) -> cs.CoreSchema:
#         return cs.no_info_plain_validator_function(
#             function=cls.validate,
#             serialization=cs.to_string_ser_schema(),
#         )
#
#     @classmethod
#     def validate(cls, v) -> Optional[ObjectId]:
#         if not v:
#             return
#         if isinstance(v, ObjectId):
#             return v
#         if not ObjectId.is_valid(v):
#             raise ValueError("Invalid ObjectId")
#         return ObjectId(v)
#
#     @classmethod
#     def __get_pydantic_json_schema__(
#         cls, core_schema: cs.CoreSchema, handler: GetJsonSchemaHandler
#     ) -> JsonSchemaValue:
#         json_schema = handler(core_schema)
#         json_schema = handler.resolve_ref_schema(json_schema)
#         json_schema["examples"] = [
#             {
#                 "objectId": "60c72b2f9b1e8c001c8b4567",  # Example ObjectId
#             }
#         ]
#         json_schema["title"] = "PyObjectId"
#         return json_schema
#
#     def __str__(self) -> str:
#         return str(self)
