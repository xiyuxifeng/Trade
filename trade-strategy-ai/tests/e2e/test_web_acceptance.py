from __future__ import annotations

import pytest

from tests.e2e.e2e_runner import run_web_acceptance_suite


pytestmark = pytest.mark.integration


def test_web_acceptance_suite() -> None:
    """运行 Web 级验收套件，保证关键业务链路在仓内可复现。"""
    run_web_acceptance_suite()
