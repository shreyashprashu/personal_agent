from fastapi import FastAPI, HTTPException
from personal_agent.schemas import NewsSummaryRequest, NewsSummaryResponse

agent_app = FastAPI(
    title="Personal Agent API",
    version="0.1.0"
)

@agent_app.get("/health/live", tags=["health"])
def live() -> dict[str,str]:
    return {"status":"alive"}

@agent_app.get("/health/ready", tags = ["health"])
def ready() -> dict[str,str]:
    return {"status":"ready"}

@agent_app.post(
    "/v1/news/summaries",
    response_model= NewsSummaryResponse,
    tags=["news"],
    responses={501: {"description": "News summarizer is not connected yet."}},
)
def create_news_summary(request:NewsSummaryRequest) -> NewsSummaryResponse:
    raise HTTPException(
        status_code=501,
        detail="News summariser is not connected yet"
    )
