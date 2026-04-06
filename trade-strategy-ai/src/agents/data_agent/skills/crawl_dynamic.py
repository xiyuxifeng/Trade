from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class DynamicRenderRequest:
    """Parameters for a JS-rendered page fetch."""

    url: str
    headers: Mapping[str, str] | None = None
    wait_until: str = "networkidle"
    timeout_ms: int = 30000


def render_page_html(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    wait_until: str = "networkidle",
    timeout_ms: int = 30000,
) -> str:
    """Render a JS-heavy page with Playwright and return the final HTML.

    The import is intentionally lazy so unit tests can monkeypatch this function
    without requiring the browser runtime.
    """

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Playwright is not available for dynamic rendering") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(extra_http_headers=dict(headers or {}))
        page = context.new_page()
        try:
            page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            return page.content()
        finally:
            context.close()
            browser.close()
