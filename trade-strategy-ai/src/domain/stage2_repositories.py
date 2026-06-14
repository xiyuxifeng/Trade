from __future__ import annotations

from datetime import date
from typing import Protocol

from src.domain.contracts import (
    DailyRuleSelectionContract,
    DatasetSnapshotContract,
    RuleVersionContract,
    StrategyVersionContract,
)


class CanonicalPromptRunRepository(Protocol):
    async def get_by_identity(
        self,
        *,
        prompt_name: str,
        prompt_version: str,
        schema_version: str,
        model: str,
        input_hash: str,
        retry_count: int,
    ) -> object | None: ...

    async def save(self, prompt_run: object) -> object: ...


class CanonicalRuleVersionRepository(Protocol):
    async def get_published_version(self, *, business_key: str) -> RuleVersionContract | None: ...

    async def save(self, rule_version: RuleVersionContract) -> RuleVersionContract: ...


class CanonicalDatasetSnapshotRepository(Protocol):
    async def get_by_fingerprint(self, *, content_fingerprint: str) -> DatasetSnapshotContract | None: ...

    async def save(self, dataset_snapshot: DatasetSnapshotContract) -> DatasetSnapshotContract: ...


class CanonicalStrategyVersionRepository(Protocol):
    async def get_by_business_key(self, *, business_key: str) -> StrategyVersionContract | None: ...

    async def save(self, strategy_version: StrategyVersionContract) -> StrategyVersionContract: ...


class CanonicalDailyRuleSelectionRepository(Protocol):
    async def get_for_trade_date(
        self,
        *,
        strategy_version_id: str,
        trade_date: date,
    ) -> DailyRuleSelectionContract | None: ...

    async def save(self, selection: DailyRuleSelectionContract) -> DailyRuleSelectionContract: ...
