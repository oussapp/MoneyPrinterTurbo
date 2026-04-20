"""Application configuration - root APIRouter.

Defines all FastAPI application endpoints.

Resources:
    1. https://fastapi.tiangolo.com/tutorial/bigger-applications

"""

from fastapi import APIRouter

from app.controllers.v1 import llm, video
from app.controllers.v1.saas import router as saas_router
from app.controllers.v1.stripe_webhooks import router as stripe_router

root_api_router = APIRouter()

# Original MoneyPrinterTurbo endpoints
root_api_router.include_router(video.router)
root_api_router.include_router(llm.router)

# SaaS endpoints (auth, projects, music, credits)
root_api_router.include_router(saas_router)

# Stripe webhooks
root_api_router.include_router(stripe_router)

