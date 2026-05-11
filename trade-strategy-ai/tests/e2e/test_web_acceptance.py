from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"
VITEST_BIN = WEB_ROOT / "node_modules" / ".bin" / "vitest"
ACCEPTANCE_TEST = "src/e2e/web-acceptance.test.tsx"


def test_web_acceptance_suite() -> None:
    """运行 Web 级验收套件，保证关键业务链路在仓内可复现。"""

    env = os.environ.copy()
    env.setdefault("CI", "1")

    result = subprocess.run(
        [str(VITEST_BIN), "run", ACCEPTANCE_TEST],
        cwd=WEB_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise AssertionError(
            "Web acceptance suite failed:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

