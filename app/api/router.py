from fastapi import APIRouter

from app.api.v1 import conversations, health

api_router = APIRouter()

api_router.include_router(health.router, tags=["system"])
api_router.include_router(conversations.router, prefix="/api/v1", tags=["conversations"])
