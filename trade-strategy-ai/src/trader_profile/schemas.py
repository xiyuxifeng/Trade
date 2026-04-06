from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class SymbolStat(BaseModel):
    """Lightweight symbol frequency stat used to build a trader profile."""

    symbol: str
    mentions: int = 0


class TraderProfile(BaseModel):
    """Minimal trader profile aggregated from articles, concepts, and clusters."""

    trader_id: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # A small, stable set of fields to start with. This is intentionally not a
    # "full profile" model yet; we want a minimal object that can be reliably
    # produced from current data (metadata + clusters).
    top_symbols: list[SymbolStat] = Field(default_factory=list)
    style_cluster_ids: list[str] = Field(default_factory=list)
    concept_tags: list[str] = Field(default_factory=list)

    evidence: dict[str, int] = Field(default_factory=dict)


class TraderProfilesFile(BaseModel):
    """Versioned on-disk container for all trader profiles."""

    schema_version: str = "v1"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    profiles_by_trader: dict[str, TraderProfile] = Field(default_factory=dict)
