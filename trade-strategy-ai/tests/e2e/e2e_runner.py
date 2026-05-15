from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"
VITEST_BIN = WEB_ROOT / "node_modules" / ".bin" / "vitest"
NODE18_BIN = Path("/Users/wanghui/.nvm/versions/node/v18.20.8/bin")


def _prepend_node18_path(env: dict[str, str]) -> None:
    """优先使用仓内已验证的 Node 18 运行时。"""
    if NODE18_BIN.exists():
        current_path = env.get("PATH", "")
        env["PATH"] = f"{NODE18_BIN}:{current_path}" if current_path else str(NODE18_BIN)


def _run_checked(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    """运行外部命令，并把失败输出转成可读的断言错误。"""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "E2E runner failed:\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


def run_web_acceptance_suite() -> None:
    """运行 Web 级验收套件，保证关键业务链路在仓内可复现。"""
    env = os.environ.copy()
    env.setdefault("CI", "1")
    _prepend_node18_path(env)
    _run_checked(
        [str(VITEST_BIN), "run", "src/e2e/web-acceptance.test.tsx"],
        cwd=WEB_ROOT,
        env=env,
    )


def run_cli_e2e_regression(
    *,
    config: Path,
    max_articles: int = 1,
    extract_limit: int = 1,
) -> None:
    """调用 CLI 的 e2e-regression 作为内部 smoke gate。"""
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(PROJECT_ROOT))
    _prepend_node18_path(env)
    _run_checked(
        [
            sys.executable,
            "-m",
            "cli.main",
            "e2e-regression",
            "--config",
            str(config),
            "--max-articles",
            str(max_articles),
            "--extract-limit",
            str(extract_limit),
        ],
        cwd=PROJECT_ROOT,
        env=env,
    )
