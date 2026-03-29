"""Unit tests for shared fetch_url tool."""

from unittest.mock import MagicMock, patch

import pytest

from sidekick.agents.tools.http import (
    fetch_item_page_html,
    fetch_listing_html,
    fetch_url,
)


def _make_pw_mock(
    html: str | None = None,
    content_type: str = "text/html; charset=utf-8",
    status: int = 200,
    url: str = "https://example.com/",
    error: Exception | None = None,
):
    """Build a sync_playwright context manager mock."""
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.url = url
    mock_response.headers = {"content-type": content_type}

    mock_page = MagicMock()
    if error is not None:
        mock_page.goto.side_effect = error
    else:
        mock_page.goto.return_value = mock_response
    mock_page.content.return_value = html or ""
    mock_page.route.return_value = None

    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_chromium = MagicMock()
    mock_chromium.launch.return_value = mock_browser

    mock_pw = MagicMock()
    mock_pw.chromium = mock_chromium

    # sync_playwright() is used as a context manager
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_pw)
    mock_cm.__exit__ = MagicMock(return_value=False)

    return mock_cm


def test_fetch_url_returns_text_for_html():
    with patch("sidekick.agents.tools.http.sync_playwright", return_value=_make_pw_mock(html="<p>hi</p>")):
        r = fetch_url("https://example.com/", max_bytes=10000)
    assert r.status_code == 200
    assert r.body_encoding == "text"
    assert "<p>hi</p>" in r.body
    assert r.error is None


def test_fetch_url_empty_body_for_pdf():
    with patch("sidekick.agents.tools.http.sync_playwright", return_value=_make_pw_mock(
        content_type="application/pdf", url="https://x.com/a.pdf"
    )):
        r = fetch_url("https://x.com/a.pdf")
    assert r.body == ""
    assert r.status_code == 200
    assert "application/pdf" in r.content_type


def test_fetch_url_records_error():
    from playwright.sync_api import Error as PlaywrightError
    with patch("sidekick.agents.tools.http.sync_playwright", return_value=_make_pw_mock(
        error=PlaywrightError("refused")
    )):
        r = fetch_url("https://bad.test/")
    assert r.status_code == 0
    assert r.error


def test_fetch_listing_html_strips_scripts():
    html = "<html><script>x</script><body><a href='/x'>a</a></body></html>"
    with patch("sidekick.agents.tools.http.sync_playwright", return_value=_make_pw_mock(html=html)):
        r = fetch_listing_html("https://list.example/")
    assert r.status_code == 200
    assert "<script" not in r.body
    assert "/x" in r.body or "a" in r.body


def test_fetch_item_page_html_keeps_scripts():
    html = "<html><script>window.__ctx={}</script><body>y</body></html>"
    with patch("sidekick.agents.tools.http.sync_playwright", return_value=_make_pw_mock(html=html)):
        r = fetch_item_page_html("https://item.example/")
    assert r.status_code == 200
    assert "window.__ctx" in r.body
