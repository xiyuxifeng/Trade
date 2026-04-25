from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from src.common.config import AppConfig
from src.common.utils import append_jsonl
from src.trader_memory.schemas import (
    TraderMemoryFilter,
    TraderMemoryItem,
    TraderMemorySummary,
    TraderMemoryType,
)


def default_memory_path(*, base_dir: Path, config: AppConfig) -> Path:
    """Return the canonical on-disk path for trader memories."""
    return base_dir / config.storage.output_dir / "trader_memory.jsonl"


class TraderMemoryStore:
    """Append-only JSONL store for trader memories.

    Supports soft-delete (archive), hard-delete, and filtered queries.
    """

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

    def _save_all(self, items: list[TraderMemoryItem]) -> None:
        """Rewrite the entire JSONL file with the given items."""
        lines = [item.model_dump_json() for item in items]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _apply_filter(self, items: list[TraderMemoryItem], f: TraderMemoryFilter) -> list[TraderMemoryItem]:
        """Apply TraderMemoryFilter criteria to a list of items."""
        result = [i for i in items if i.trader_id == f.trader_id]

        if not f.include_archived:
            result = [i for i in result if not i.archived]

        if f.memory_types:
            allowed = set(f.memory_types)
            result = [i for i in result if i.memory_type in allowed]

        if f.symbol:
            result = [i for i in result if i.symbol == f.symbol]

        if f.date_from:
            result = [i for i in result if i.as_of_date >= f.date_from]

        if f.date_to:
            result = [i for i in result if i.as_of_date <= f.date_to]

        if f.keyword:
            kw = f.keyword.lower()
            result = [
                i
                for i in result
                if kw in i.title.lower() or kw in i.content.lower()
            ]

        # NTL-S5-006: tags 过滤（匹配任一 tag 即可）
        if f.tags:
            result = [
                i for i in result
                if i.tags and any(tag in i.tags for tag in f.tags)
            ]

        # NTL-S5-006: strategy_version_id 过滤（精确匹配）
        if f.strategy_version_id:
            result = [
                i for i in result
                if i.strategy_version_id == f.strategy_version_id
            ]

        return result

    def list_filtered(self, filter: TraderMemoryFilter) -> list[TraderMemoryItem]:
        """Return memories matching the given filter criteria."""
        items = self._load_all()
        filtered = self._apply_filter(items, filter)
        filtered.sort(key=lambda item: item.created_at, reverse=True)
        return filtered[filter.offset : filter.offset + filter.limit]

    def count_filtered(self, filter: TraderMemoryFilter) -> int:
        """Return the total count of memories matching the filter (ignoring offset/limit)."""
        items = self._load_all()
        filtered = self._apply_filter(items, filter)
        return len(filtered)

    def archive(self, memory_id: UUID) -> bool:
        """Soft-delete: mark a memory item as archived. Returns True if found and updated."""
        items = self._load_all()
        for item in items:
            if item.memory_id == memory_id:
                item.archived = True
                item.archived_at = datetime.now(UTC)
                self._save_all(items)
                return True
        return False

    def restore(self, memory_id: UUID) -> bool:
        """Restore an archived memory item. Returns True if found and updated."""
        items = self._load_all()
        for item in items:
            if item.memory_id == memory_id:
                item.archived = False
                item.archived_at = None
                self._save_all(items)
                return True
        return False

    def hard_delete(self, memory_id: UUID) -> bool:
        """Permanently remove a memory item. Returns True if found and deleted."""
        items = self._load_all()
        original_len = len(items)
        items = [i for i in items if i.memory_id != memory_id]
        if len(items) < original_len:
            self._save_all(items)
            return True
        return False

    def list_recent(
        self,
        *,
        trader_id: str,
        limit: int = 10,
        memory_types: list[TraderMemoryType] | None = None,
    ) -> list[TraderMemoryItem]:
        """Return the most recent memories for one trader."""
        f = TraderMemoryFilter(
            trader_id=trader_id,
            memory_types=memory_types,
            limit=limit,
        )
        return self.list_filtered(f)

    def search_by_symbol(
        self,
        *,
        trader_id: str,
        symbol: str,
        limit: int = 10,
    ) -> list[TraderMemoryItem]:
        """Return memories tied to one symbol for one trader."""
        f = TraderMemoryFilter(
            trader_id=trader_id,
            symbol=symbol,
            limit=limit,
        )
        return self.list_filtered(f)

    def summarize_context(
        self,
        *,
        trader_id: str,
        symbol: str | None = None,
        limit: int = 5,
    ) -> TraderMemorySummary:
        """Build the compact memory summary used by idea generation."""

        all_items = [item for item in self._load_all() if item.trader_id == trader_id]
        active_items = [i for i in all_items if not i.archived]
        active_items.sort(key=lambda item: item.created_at, reverse=True)

        symbol_items = (
            [item for item in active_items if symbol and item.symbol == symbol]
            if symbol
            else []
        )

        by_type: dict[str, int] = {}
        for item in active_items:
            key = item.memory_type.value
            by_type[key] = by_type.get(key, 0) + 1

        recent_titles = [item.title for item in active_items[: max(0, int(limit))]]
        symbol_titles = [item.title for item in symbol_items[: max(0, int(limit))]]
        review_notes = [
            item.content
            for item in active_items
            if item.memory_type == TraderMemoryType.review_note
        ][: max(0, int(limit))]

        # 新增：聚合 new memory types 到 summary
        postmortem_notes = [
            item.content
            for item in active_items
            if item.memory_type == TraderMemoryType.postmortem
        ][: max(0, int(limit))]

        strategy_adjustments = [
            item.content
            for item in active_items
            if item.memory_type == TraderMemoryType.strategy_adjustment
        ][: max(0, int(limit))]

        market_regime_notes = [
            item.content
            for item in active_items
            if item.memory_type == TraderMemoryType.market_regime_note
        ][: max(0, int(limit))]

        return TraderMemorySummary(
            trader_id=trader_id,
            symbol=symbol,
            total_items=len(active_items),
            total_symbol_items=len(symbol_items),
            archived_items=len(all_items) - len(active_items),
            by_type=by_type,
            recent_titles=recent_titles,
            symbol_titles=symbol_titles,
            review_notes=review_notes,
            postmortem_notes=postmortem_notes,
            strategy_adjustments=strategy_adjustments,
            market_regime_notes=market_regime_notes,
        )
