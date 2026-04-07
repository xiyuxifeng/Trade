from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.api.dependencies import verify_api_key
from src.api.routes import articles_router, trades_router, market_router

app = FastAPI(
    title="Trade Strategy AI API",
    description="Data query and export API for articles, trades, and market data",
    version="1.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(articles_router)
app.include_router(trades_router)
app.include_router(market_router)


@app.get("/health")
async def health_check():
    """Health check endpoint (public, no auth required)."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Trade Strategy AI API",
        "version": "1.0.0",
        "docs": "/docs",
    }


class RunTriggerRequest(BaseModel):
    """Request body for manual trigger endpoints."""
    config_path: str = "config/app.yaml"
    as_of_date: date | None = None
    force: bool = False
    args: dict[str, Any] = {}


@app.post("/run/pre_market")
async def trigger_pre_market(
    request: RunTriggerRequest,
    _: str = Depends(verify_api_key),
):
    """Trigger pre-market analysis."""
    from src.host.handler import handle_command

    command = {
        "type": "run_pre_market",
        "config_path": request.config_path,
        "as_of_date": request.as_of_date.isoformat() if request.as_of_date else None,
        "force": request.force,
        "args": request.args,
    }
    result = handle_command(command)
    return result


@app.post("/run/after_close")
async def trigger_after_close(
    request: RunTriggerRequest,
    _: str = Depends(verify_api_key),
):
    """Trigger after-close evaluation."""
    from src.host.handler import handle_command

    command = {
        "type": "run_after_close",
        "config_path": request.config_path,
        "as_of_date": request.as_of_date.isoformat() if request.as_of_date else None,
        "force": request.force,
        "args": request.args,
    }
    result = handle_command(command)
    return result
