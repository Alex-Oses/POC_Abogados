from pydantic import BaseModel


class PaginatedOut[T](BaseModel):
    items: list[T]
    page: int
    limit: int
    total: int
