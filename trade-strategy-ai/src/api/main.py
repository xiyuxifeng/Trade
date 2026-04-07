from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
