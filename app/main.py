import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # LiteLLM reads API keys from os.environ at call time, not from our
    # Settings object, so we push them explicitly on startup.
    if settings.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.gemini_api_key:
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key

    # Phase 4: start Redis ingestion consumer here.
    yield
    # Phase 4: stop consumer here.


app = FastAPI(
    title="LLM Inference Logger",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router)
