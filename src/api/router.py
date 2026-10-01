"""Consolidated v1 API router."""

from fastapi import APIRouter
from src.api.routes import health, parser

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(parser.router)
