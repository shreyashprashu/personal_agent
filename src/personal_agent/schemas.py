from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class AssistantTurnRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    read_aloud: bool = False


class Citation(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl
    start_index: int | None = Field(default=None, ge=0)
    end_index: int | None = Field(default=None, ge=0)


class AssistantTurnResponse(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[Citation]
    generated_at: datetime
    audio_base64: str | None = None
    audio_content_type: str | None = None
