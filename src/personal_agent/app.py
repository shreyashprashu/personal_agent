import asyncio
import base64
import hmac
from contextlib import asynccontextmanager
from uuid import uuid4
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from personal_agent.agent import build_agent
from personal_agent.schemas import AssistantTurnRequest, AssistantTurnResponse
from personal_agent.settings import Settings, get_settings
from personal_agent.speech import (
    AzureSpeechClient,
    SpeechNotConfiguredError,
    SpeechProviderError,
)


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(20.0, connect=5.0),
        follow_redirects=True,
    ) as http_client:
        app.state.settings = settings
        app.state.http_client = http_client
        app.state.graph = build_agent(settings) if settings.model_is_configured else None
        app.state.speech_client = AzureSpeechClient(settings, http_client)
        app.state.model_semaphore = asyncio.Semaphore(
            settings.max_model_concurrency
        )
        yield


agent_app = FastAPI(
    title="Personal Agent API",
    version="0.2.0",
    lifespan=lifespan,
)


@agent_app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


async def require_api_key(
    request: Request,
    provided_key: Annotated[str | None, Security(api_key_header)],
) -> None:
    settings: Settings = request.app.state.settings
    if not settings.api_auth_is_configured:
        raise HTTPException(status_code=503, detail="API authentication is not configured.")

    expected_key = settings.assistant_api_key.get_secret_value()
    if provided_key is None or not hmac.compare_digest(provided_key, expected_key):
        raise HTTPException(status_code=401, detail="Invalid API key.")


@agent_app.get("/health/live", tags=["health"])
def live() -> dict[str, str]:
    return {"status": "alive"}


@agent_app.get("/health/ready", tags=["health"])
def ready(request: Request) -> dict[str, str]:
    settings: Settings = request.app.state.settings
    missing = []
    if request.app.state.graph is None:
        missing.append("Azure model configuration")
    if not settings.api_auth_is_configured:
        missing.append("ASSISTANT_API_KEY")
    if missing:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "missing": missing},
        )
    return {
        "status": "ready",
        "speech": "configured" if settings.speech_is_configured else "not_configured",
    }


@agent_app.post(
    "/v1/assistant/turn",
    response_model=AssistantTurnResponse,
    tags=["assistant"],
    dependencies=[Depends(require_api_key)],
)
async def assistant_turn(
    payload: AssistantTurnRequest,
    request: Request,
) -> AssistantTurnResponse:
    graph = request.app.state.graph
    if graph is None:
        raise HTTPException(status_code=503, detail="The assistant is not configured.")

    settings: Settings = request.app.state.settings
    if payload.read_aloud and not settings.speech_is_configured:
        raise HTTPException(
            status_code=503,
            detail="Read-aloud is not configured.",
        )

    semaphore: asyncio.Semaphore = request.app.state.model_semaphore
    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=0.25)
    except TimeoutError as exc:
        raise HTTPException(
            status_code=503,
            detail="The assistant is at capacity. Retry shortly.",
            headers={"Retry-After": "2"},
        ) from exc

    try:
        try:
            result = await graph.ainvoke({"query": payload.query})
        except APITimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail="The model request timed out.",
            ) from exc
        except RateLimitError as exc:
            raise HTTPException(
                status_code=503,
                detail="The model provider is rate limiting requests.",
                headers={"Retry-After": "5"},
            ) from exc
        except APIConnectionError as exc:
            raise HTTPException(
                status_code=503,
                detail="The model provider could not be reached.",
            ) from exc
        except APIStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail="The model provider returned an error.",
            ) from exc
    finally:
        semaphore.release()

    audio_base64 = None
    audio_content_type = None
    if payload.read_aloud:
        try:
            audio = await request.app.state.speech_client.synthesize_mp3(
                result["answer"]
            )
        except SpeechNotConfiguredError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except SpeechProviderError as exc:
            raise HTTPException(
                status_code=502,
                detail="Speech synthesis failed.",
            ) from exc
        audio_base64 = base64.b64encode(audio).decode("ascii")
        audio_content_type = "audio/mpeg"

    return AssistantTurnResponse(
        answer=result["answer"],
        citations=result["citations"],
        generated_at=result["generated_at"],
        audio_base64=audio_base64,
        audio_content_type=audio_content_type,
    )
