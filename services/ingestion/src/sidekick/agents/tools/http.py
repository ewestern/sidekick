"""Shared HTTP fetch for examination and ingestion agents."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from bs4 import BeautifulSoup, Comment

logger = logging.getLogger(__name__)

# Overridable in tests
def _http_client(**kwargs: Any) -> httpx.Client:
    return httpx.Client(**kwargs)

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


def _is_probably_binary(content_type: str, raw: bytes) -> bool:
    ct = content_type.lower().split(";")[0].strip()
    if ct in BINARY_TYPES:
        return True
    if ct.startswith("audio/") or ct.startswith("video/"):
        return True
    if ct.startswith("image/"):
        return True
    if not any(ct.startswith(p) for p in TEXTUAL_PREFIXES) and ct not in ("", "application/octet-stream"):
        # unknown type — try decode
        pass
    try:
        raw.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def fetch_url(
    url: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
) -> FetchResult:
    """GET url with size and timeout limits.

    Returns UTF-8 text (possibly truncated) or base64 for binary/large content.
    """
    h = {
        "User-Agent": "SidekickBot/1.0 (+https://sidekick)",
        **(headers or {}),
    }
    try:
        with _http_client(timeout=timeout, follow_redirects=True) as client:
            with client.stream("GET", url, headers=h) as response:
                final_url = str(response.url)
                ct = response.headers.get("content-type", "") or "application/octet-stream"
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    if not chunk:
                        continue
                    take = min(len(chunk), max_bytes - total)
                    if take > 0:
                        chunks.append(chunk[:take])
                        total += take
                    if total >= max_bytes:
                        break
                raw = b"".join(chunks)
                truncated = total >= max_bytes
                cl = response.headers.get("content-length")
                if cl is not None:
                    try:
                        truncated = truncated or total < int(cl)
                    except ValueError:
                        pass
                status = response.status_code
    except httpx.RequestError as e:
        logger.warning("fetch_url failed %s: %s", url, e)
        return FetchResult(
            status_code=0,
            final_url=url,
            content_type="",
            body_encoding="text",
            body="",
            error=str(e),
        )

    if status >= 400:
        text = raw.decode("utf-8", errors="replace")[:8000]
        return FetchResult(
            status_code=status,
            final_url=final_url,
            content_type=ct,
            body_encoding="text",
            body=text,
            error=f"HTTP {status}",
        )

    if _is_probably_binary(ct, raw) or len(raw) > max_bytes:
        b64 = base64.standard_b64encode(raw).decode("ascii")
        return FetchResult(
            status_code=status,
            final_url=final_url,
            content_type=ct,
            body_encoding="base64",
            body=b64,
            truncated=truncated,
        )

    text = raw.decode("utf-8", errors="replace")
    if len(text) > max_bytes:
        text = text[:max_bytes]
        truncated = True
    return FetchResult(
        status_code=status,
        final_url=final_url,
        content_type=ct,
        body_encoding="text",
        body=text,
        truncated=truncated,
    )


def fetch_listing_html(url: str, *, max_bytes: int = LISTING_PAGE_MAX_BYTES) -> FetchResult:
    """Fetch a listing/index page with scripts stripped to reduce LLM tokens."""
    result = fetch_url(url, max_bytes=max_bytes)
    if result.error or result.body_encoding != "text":
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
    if result.error or result.body_encoding != "text":
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
