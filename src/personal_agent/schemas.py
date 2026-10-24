from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

NewsCategory = Literal["technology", "politics", "business", "world"]

#Each class defines a datashape
class NewsSummaryRequest(BaseModel):
    categories: list[NewsCategory] = Field(min_length=1, max_length=4)
    lookback_hours: int = Field(default=24, ge=1, le=72)
    max_articles: int = Field(default=12, ge=1, le=25)


class NewsSource(BaseModel):
    id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=300)
    url: HttpUrl
    published_at: datetime | None = None


class NewsSummaryResponse(BaseModel):
    summary: str = Field(min_length=1)
    categories: list[NewsCategory]
    generated_at: datetime
    sources: list[NewsSource]