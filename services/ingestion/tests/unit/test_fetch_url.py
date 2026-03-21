"""Unit tests for shared fetch_url tool."""

from types import SimpleNamespace

import httpx
import pytest

from sidekick.agents.tools import http as http_tools
from sidekick.agents.tools.http import (
    fetch_item_page_html,
    fetch_listing_html,
    fetch_url,
)


@pytest.fixture
def httpx_mock(monkeypatch):
    responses: list[tuple[str, dict]] = []

    def add_response(
        url: str,
        html: str | None = None,
        content: bytes | None = None,
        headers: dict | None = None,
    ) -> None:
        responses.append(
            (
                url,
                {
                    "html": html,
                    "content": content,
                    "headers": headers or {},
                },
            )
        )

    def add_exception(exc: Exception, url: str) -> None:
        responses.append((url, {"exc": exc}))

    def handler(request: httpx.Request) -> httpx.Response:
        for u, spec in responses:
            if request.url.host in u or str(request.url) == u:
                if "exc" in spec:
                    raise spec["exc"]
                body = spec.get("content")
                if body is None and spec.get("html") is not None:
                    body = spec["html"].encode()
                elif body is None:
                    body = b""
                h = {"content-type": "text/html; charset=utf-8", **spec.get("headers", {})}
                return httpx.Response(200, content=body, headers=h)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    real = httpx.Client

    def client_factory(**kw: object) -> httpx.Client:
        return real(
            transport=transport,
            timeout=kw.get("timeout", 60.0),
            follow_redirects=kw.get("follow_redirects", True),
        )

    monkeypatch.setattr(http_tools, "_http_client", client_factory)
    return SimpleNamespace(add_response=add_response, add_exception=add_exception)


def test_fetch_url_returns_text_for_html(httpx_mock):
    httpx_mock.add_response(url="https://example.com/", html="<p>hi</p>")
    r = fetch_url("https://example.com/", max_bytes=10000)
    assert r.status_code == 200
    assert r.body_encoding == "text"
    assert "<p>hi</p>" in r.body
    assert r.error is None


def test_fetch_url_base64_for_pdf(httpx_mock):
    pdf = b"%PDF-1.4 minimal"
    httpx_mock.add_response(
        url="https://x.com/a.pdf",
        content=pdf,
        headers={"content-type": "application/pdf"},
    )
    r = fetch_url("https://x.com/a.pdf")
    assert r.body_encoding == "base64"
    assert r.status_code == 200


def test_fetch_url_records_error(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("refused"), url="https://bad.test/")
    r = fetch_url("https://bad.test/")
    assert r.status_code == 0
    assert r.error


def test_fetch_listing_html_strips_scripts(httpx_mock):
    html = "<html><script>x</script><body><a href='/x'>a</a></body></html>"
    httpx_mock.add_response(url="https://list.example/", html=html)
    r = fetch_listing_html("https://list.example/")
    assert r.status_code == 200
    assert "<script" not in r.body
    assert "/x" in r.body or "a" in r.body


def test_fetch_item_page_html_keeps_scripts(httpx_mock):
    html = "<html><script>window.__ctx={}</script><body>y</body></html>"
    httpx_mock.add_response(url="https://item.example/", html=html)
    r = fetch_item_page_html("https://item.example/")
    assert r.status_code == 200
    assert "window.__ctx" in r.body
