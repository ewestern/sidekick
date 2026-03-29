"""Shared HTTP fetch for examination and ingestion agents."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, Comment
from playwright.sync_api import Error as PlaywrightError, sync_playwright

logger = logging.getLogger(__name__)

DEFAULT_MAX_BYTES = 2_000_000
DEFAULT_TIMEOUT = 60.0
LISTING_PAGE_MAX_BYTES = 200_000
ITEM_PAGE_MAX_BYTES = 200_000

TEXTUAL_PREFIXES = (
    "text/",
    "application/json",
    "application/xml",
    "application/rss+xml",
    "application/atom+xml",
    "application/xhtml",
)
BINARY_TYPES = frozenset(
    {
        "application/pdf",
        "application/octet-stream",
        "application/zip",
    }
)


def _is_binary_content_type(ct: str) -> bool:
    bare = ct.lower().split(";")[0].strip()
    if bare in BINARY_TYPES:
        return True
    if bare.startswith(("audio/", "video/", "image/")):
        return True
    if bare == "application/octet-stream":
        return True
    return not any(bare.startswith(p) for p in TEXTUAL_PREFIXES) and bare != ""


def strip_html_noise(html: str, *, remove_scripts: bool = True) -> str:
    """Remove noisy markup while optionally preserving scripts.

    Reduces context size for LLM consumption without losing structural information.
    """
    soup = BeautifulSoup(html, "html.parser")
    tag_names = ["style"]
    if remove_scripts:
        tag_names.append("script")
    for tag in soup(tag_names):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()
    for tag in soup.find_all(True):
        tag.attrs.pop("style", None)
    return str(soup)


@dataclass
class FetchResult:
    """Structured result from fetch_url — same contract for both agents."""

    status_code: int
    final_url: str
    content_type: str
    body_encoding: str  # "text" | "base64"
    body: str
    truncated: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "final_url": self.final_url,
            "content_type": self.content_type,
            "body_encoding": self.body_encoding,
            "body": self.body,
            "truncated": self.truncated,
            "error": self.error,
        }


def fetch_url(
    url: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
) -> FetchResult:
    """Load url in a headless browser (JS rendered).

    Returns UTF-8 text of the rendered DOM (possibly truncated) or an empty
    body with content_type set for binary responses.
    """
    # Playwright's sync API binds its internal greenlet dispatcher to the
    # calling thread, so we create a fresh playwright instance per call.
    # This avoids cross-thread greenlet errors when called from thread pools.
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                extra_http_headers={
                    "User-Agent": "SidekickBot/1.0 (+https://sidekick)",
                    **(headers or {}),
                }
            )
            page = context.new_page()

            # Block images, fonts, and media — we only need DOM structure.
            def _abort_unnecessary(route: Any) -> None:
                if route.request.resource_type in ("image", "font", "media"):
                    route.abort()
                else:
                    route.continue_()

            page.route("**/*", _abort_unnecessary)

            try:
                response = page.goto(
                    url, wait_until="networkidle", timeout=timeout * 1000)
            except PlaywrightError as e:
                logger.warning("fetch_url failed %s: %s", url, e)
                return FetchResult(
                    status_code=0,
                    final_url=url,
                    content_type="",
                    body_encoding="text",
                    body="",
                    error=str(e),
                )

            if response is None:
                return FetchResult(
                    status_code=0,
                    final_url=url,
                    content_type="",
                    body_encoding="text",
                    body="",
                    error="No response received",
                )

            status = response.status
            final_url = response.url
            ct = response.headers.get(
                "content-type", "") or "application/octet-stream"

            if status >= 400:
                return FetchResult(
                    status_code=status,
                    final_url=final_url,
                    content_type=ct,
                    body_encoding="text",
                    body="",
                    error=f"HTTP {status}",
                )

            if _is_binary_content_type(ct):
                return FetchResult(
                    status_code=status,
                    final_url=final_url,
                    content_type=ct,
                    body_encoding="text",
                    body="",
                )

            html = page.content()
            truncated = len(html) > max_bytes
            if truncated:
                html = html[:max_bytes]

            return FetchResult(
                status_code=status,
                final_url=final_url,
                content_type=ct,
                body_encoding="text",
                body=html,
                truncated=truncated,
            )

    except PlaywrightError as e:
        logger.warning("fetch_url failed %s: %s", url, e)
        return FetchResult(
            status_code=0,
            final_url=url,
            content_type="",
            body_encoding="text",
            body="",
            error=str(e),
        )


def fetch_listing_html(url: str, *, max_bytes: int = LISTING_PAGE_MAX_BYTES) -> FetchResult:
    """Fetch a listing/index page with scripts stripped to reduce LLM tokens."""
    result = fetch_url(url, max_bytes=max_bytes)
    if result.error or result.body_encoding != "text" or not result.body:
        return result
    ct = result.content_type.lower().split(";")[0].strip()
    if ct == "text/html":
        body = strip_html_noise(result.body, remove_scripts=True)
        return FetchResult(
            status_code=result.status_code,
            final_url=result.final_url,
            content_type=result.content_type,
            body_encoding="text",
            body=body,
            truncated=result.truncated,
            error=result.error,
        )
    return result


def fetch_item_page_html(url: str, *, max_bytes: int = ITEM_PAGE_MAX_BYTES) -> FetchResult:
    """Fetch one item detail page; preserve script tags for embedded JSON URLs."""
    result = fetch_url(url, max_bytes=max_bytes)
    if result.error or result.body_encoding != "text" or not result.body:
        return result
    ct = result.content_type.lower().split(";")[0].strip()
    if ct == "text/html":
        body = strip_html_noise(result.body, remove_scripts=False)
        return FetchResult(
            status_code=result.status_code,
            final_url=result.final_url,
            content_type=result.content_type,
            body_encoding="text",
            body=body,
            truncated=result.truncated,
            error=result.error,
        )
    return result
