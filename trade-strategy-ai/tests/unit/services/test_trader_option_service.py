from __future__ import annotations

import pytest

from src.services.trader_option_service import TraderOptionService


class _FakeScalarResult:
    def __init__(self, items: list[str]) -> None:
        self._items = items

    def scalars(self) -> _FakeScalarResult:
        return self

    def all(self) -> list[str]:
        return self._items


class _FakeSession:
    def __init__(self, items: list[str]) -> None:
        self._items = items

    async def execute(self, stmt):  # noqa: ANN001
        return _FakeScalarResult(self._items)


class _FakeSessionScope:
    def __init__(self, items: list[str]) -> None:
        self._session = _FakeSession(items)

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False


class _FakeJobService:
    def __init__(self, items_by_type: dict[str, list[dict[str, object]]]) -> None:
        self._items_by_type = items_by_type

    async def list_jobs(self, *, status: str | None = None, job_type: str | None = None, created_by: str | None = None, skip: int = 0, limit: int = 50):
        del created_by, skip, limit
        assert status == "success"
        items = self._items_by_type.get(job_type or "", [])
        return type(
            "Result",
            (),
            {
                "status": "ok",
                "payload": {
                    "count": len(items),
                    "total": len(items),
                    "skip": 0,
                    "limit": 50,
                    "items": items,
                },
            },
        )()


@pytest.mark.asyncio
async def test_list_trader_options_merges_strategy_and_backtest_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    strategy_scope_factory = lambda: _FakeSessionScope(["trader_b", "trader_a", "trader_a"])  # noqa: E731
    service = TraderOptionService(session_scope_factory=strategy_scope_factory)
    monkeypatch.setattr(
        "src.services.trader_option_service.JobService",
        lambda: _FakeJobService(
            {
                "backtest-run": [
                    {
                        "id": "job-1",
                        "result": {
                            "payload": {
                                "request": {"trader_id": "trader_c"},
                            }
                        },
                    },
                    {
                        "id": "job-2",
                        "result": {
                            "payload": {
                                "request": {"trader_id": "trader_a"},
                            }
                        },
                    },
                ],
                "rule-pool-backtest": [
                    {
                        "id": "job-3",
                        "result": {
                            "payload": {
                                "request": {"trader_id": "trader_d"},
                            }
                        },
                    }
                ],
            }
        ),
    )

    strategy_result = await service.list_trader_options(source="strategy")
    backtest_result = await service.list_trader_options(source="backtest")
    all_result = await service.list_trader_options(source="all")

    assert strategy_result.status == "ok"
    assert strategy_result.payload["items"] == ["trader_a", "trader_b"]

    assert backtest_result.status == "ok"
    assert backtest_result.payload["items"] == ["trader_a", "trader_c", "trader_d"]

    assert all_result.status == "ok"
    assert all_result.payload["items"] == ["trader_a", "trader_b", "trader_c", "trader_d"]


@pytest.mark.asyncio
async def test_list_trader_options_paginates_backtest_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    """backtest trader 选项应分页读取 jobs，避免 1000 条上限漏数据。"""

    class _PagedJobService:
        def __init__(self) -> None:
            self.list_calls: list[dict[str, object]] = []
            self.jobs = [
                {
                    "id": f"job-{i}",
                    "result": {
                        "payload": {
                            "request": {"trader_id": f"trader_{i}"},
                        }
                    },
                    "job_type": "backtest-run",
                    "status": "success",
                }
                for i in range(501)
            ]

        async def list_jobs(self, *, status: str | None = None, job_type: str | None = None, created_by: str | None = None, skip: int = 0, limit: int = 50):
            del created_by
            self.list_calls.append({"status": status, "job_type": job_type, "skip": skip, "limit": limit})
            items = [job for job in self.jobs if (status is None or job.get("status") == status) and (job_type is None or job.get("job_type") == job_type)]
            paginated = items[skip : skip + limit]
            return type(
                "Result",
                (),
                {
                    "status": "ok",
                    "payload": {
                        "count": len(paginated),
                        "total": len(items),
                        "skip": skip,
                        "limit": limit,
                        "items": paginated,
                    },
                },
            )()

    paged_service = _PagedJobService()
    monkeypatch.setattr("src.services.trader_option_service.JobService", lambda: paged_service)

    service = TraderOptionService(session_scope_factory=lambda: _FakeSessionScope(["trader_a"]))
    result = await service.list_trader_options(source="backtest")

    assert result.status == "ok"
    assert result.payload["count"] == 501
    assert result.payload["items"][0] == "trader_0"
    assert len(paged_service.list_calls) >= 2
