from __future__ import annotations

from pathlib import Path

from src.common.config import AppConfig
from src.common.utils import append_jsonl
from src.trader_memory.schemas import TraderMemoryItem, TraderMemorySummary, TraderMemoryType


def default_memory_path(*, base_dir: Path, config: AppConfig) -> Path:
    """Return the canonical on-disk path for trader memories."""
    return base_dir / config.storage.output_dir / "trader_memory.jsonl"


class TraderMemoryStore:
    """Append-only JSONL store for trader memories."""

    def __init__(self, *, path: Path) -> None:
        self.path = Path(path)

    def append(self, item: TraderMemoryItem) -> Path:
        """Append one memory item to the JSONL file."""

        append_jsonl(self.path, item.model_dump(mode="json"))
        return self.path

    def _load_all(self) -> list[TraderMemoryItem]:
        """Read all persisted memories, skipping malformed rows."""
        if not self.path.exists():
            return []

        items: list[TraderMemoryItem] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(TraderMemoryItem.model_validate_json(line))
            except Exception:  # noqa: BLE001
                continue
        return items

    def list_recent(
        self,
        *,
        trader_id: str,
        limit: int = 10,
        memory_types: list[TraderMemoryType] | None = None,
    ) -> list[TraderMemoryItem]:
        """Return the most recent memories for one trader."""

        items = [item for item in self._load_all() if item.trader_id == trader_id]
        if memory_types:
            allowed = set(memory_types)
            items = [item for item in items if item.memory_type in allowed]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return items[: max(0, int(limit))]

    def search_by_symbol(
        self,
        *,
        trader_id: str,
        symbol: str,
        limit: int = 10,
    ) -> list[TraderMemoryItem]:
        """Return memories tied to one symbol for one trader."""

        items = [
            item
            for item in self._load_all()
            if item.trader_id == trader_id and item.symbol == symbol
        ]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return items[: max(0, int(limit))]

    def summarize_context(
        self,
        *,
        trader_id: str,
        symbol: str | None = None,
        limit: int = 5,
    ) -> TraderMemorySummary:
        """Build the compact memory summary used by idea generation."""

        all_items = [item for item in self._load_all() if item.trader_id == trader_id]
        all_items.sort(key=lambda item: item.created_at, reverse=True)
        symbol_items = [item for item in all_items if symbol and item.symbol == symbol] if symbol else []

        by_type: dict[str, int] = {}
        for item in all_items:
            key = item.memory_type.value
            by_type[key] = by_type.get(key, 0) + 1

        recent_titles = [item.title for item in all_items[: max(0, int(limit))]]
        symbol_titles = [item.title for item in symbol_items[: max(0, int(limit))]]
        review_notes = [
            item.content
            for item in all_items
            if item.memory_type == TraderMemoryType.review_note
        ][: max(0, int(limit))]

        return TraderMemorySummary(
            trader_id=trader_id,
            symbol=symbol,
            total_items=len(all_items),
            total_symbol_items=len(symbol_items),
            by_type=by_type,
            recent_titles=recent_titles,
            symbol_titles=symbol_titles,
            review_notes=review_notes,
        )
