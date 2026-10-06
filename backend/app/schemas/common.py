from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PublicModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
    applied_filters: dict[str, str | int | None] = {}


class ErrorDetail(BaseModel):
    code: str
    message: str
    field_errors: list[dict[str, str]] = []
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
