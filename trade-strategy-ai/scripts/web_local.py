from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence

import typer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEB_DIST = PROJECT_ROOT / "web" / "dist"

app = typer.Typer(add_completion=False, help="本机非 Docker 部署命令")


def _run_command(cmd: Sequence[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    """在指定工作目录执行一次性命令。"""
    subprocess.run(list(cmd), cwd=str(cwd), env=env, check=True)


def _spawn_command(cmd: Sequence[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.Popen[str]:
    """启动长驻子进程。"""
    return subprocess.Popen(list(cmd), cwd=str(cwd), env=env)


def _require_web_dist(web_dist: Path = DEFAULT_WEB_DIST) -> Path:
    """确保前端构建产物已生成。"""
    index_path = web_dist / "index.html"
    if not index_path.exists():
        typer.echo(f"前端产物不存在: {index_path}，请先运行 `python -m scripts.web_local build`", err=True)
        raise typer.Exit(code=2)
    return web_dist


def _api_env(*, web_dist: Path | None = None) -> dict[str, str]:
    """构造 API 子进程环境。"""
    env = dict(os.environ)
    if web_dist is not None:
        env["WEB_STATIC_DIR"] = str(web_dist)
    return env


def _api_command() -> tuple[str, ...]:
    """返回 API 启动命令。"""
    return ("uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000")


def _worker_command() -> tuple[str, ...]:
    """返回 Worker 启动命令。"""
    return (sys.executable, "-m", "cli.main", "job-worker-start", "--config", "config/app.yaml")


@app.command("build")
def build() -> None:
    """构建前端生产产物。"""
    _run_command(("corepack", "pnpm", "build"), cwd=PROJECT_ROOT / "web")


@app.command("migrate")
def migrate() -> None:
    """执行数据库迁移。"""
    _run_command((sys.executable, "-m", "cli.main", "db-migrate", "--config", "config/app.yaml"), cwd=PROJECT_ROOT)


@app.command("start-api")
def start_api(
    web_dist: Path = typer.Option(DEFAULT_WEB_DIST, help="前端构建产物目录"),
) -> None:
    """启动 API，并可选托管本机前端静态资源。"""
    static_dir = _require_web_dist(web_dist)
    _run_command(_api_command(), cwd=PROJECT_ROOT, env=_api_env(web_dist=static_dir))


@app.command("start-worker")
def start_worker() -> None:
    """启动数据库轮询式 Job Worker。"""
    _run_command(_worker_command(), cwd=PROJECT_ROOT)


@app.command("start")
def start(
    web_dist: Path = typer.Option(DEFAULT_WEB_DIST, help="前端构建产物目录"),
) -> None:
    """同时启动 API 和 Worker，并在任一子进程退出时停止整个本机部署。"""
    static_dir = _require_web_dist(web_dist)
    api_proc = _spawn_command(_api_command(), cwd=PROJECT_ROOT, env=_api_env(web_dist=static_dir))
    worker_proc = _spawn_command(_worker_command(), cwd=PROJECT_ROOT)
    processes = [api_proc, worker_proc]

    try:
        while True:
            exited = next((proc for proc in processes if proc.poll() is not None), None)
            if exited is not None:
                for proc in processes:
                    if proc is not exited and proc.poll() is None:
                        proc.terminate()
                for proc in processes:
                    if proc is not exited:
                        try:
                            proc.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                raise SystemExit(exited.returncode or 1)
            time.sleep(1.0)
    except KeyboardInterrupt:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        raise SystemExit(130)


def main() -> None:
    """CLI 入口。"""
    app()


if __name__ == "__main__":
    main()
