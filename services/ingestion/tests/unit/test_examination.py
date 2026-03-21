"""Unit tests for source examination spider validation safeguards."""

from __future__ import annotations

from sidekick.agents.examination.examination import (
    _asset_classes_in_code,
    _asset_class_from_url,
    _has_detail_callback_method,
    _resolve_spider_destination,
    _extract_candidate_asset_urls,
    _validate_spider_code,
)


def test_validate_spider_code_allows_safe_spider_module():
    code = """
import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier
from sidekick.spiders._base import SidekickSpider, RawItem

class ExampleSpider(SidekickSpider):
    name = "example"
    source_id = "src_example"
    endpoint = "https://example.com"
    beat = BeatIdentifier("government:city_council")
    geo = GeoIdentifier("us:il:springfield:springfield")

    def parse(self, response):
        return []
"""
    assert _validate_spider_code(code, "example.py") is None


def test_validate_spider_code_rejects_disallowed_import():
    code = """
import os
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier
from sidekick.spiders._base import SidekickSpider, RawItem

class ExampleSpider(SidekickSpider):
    name = "example"
    source_id = "src_example"
    endpoint = "https://example.com"
    beat = BeatIdentifier("government:city_council")
    geo = GeoIdentifier("us:il:springfield:springfield")
"""
    error = _validate_spider_code(code, "example.py")
    assert error is not None
    assert "Disallowed import" in error


def test_validate_spider_code_allows_re_import():
    code = """
import re
import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier
from sidekick.spiders._base import SidekickSpider, RawItem

class ExampleSpider(SidekickSpider):
    name = "example"
    source_id = "src_example"
    endpoint = "https://example.com"
    beat = BeatIdentifier("government:city_council")
    geo = GeoIdentifier("us:il:springfield:springfield")
"""
    assert _validate_spider_code(code, "example.py") is None


def test_validate_spider_code_rejects_top_level_execution():
    code = """
import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier
from sidekick.spiders._base import SidekickSpider, RawItem

print("unsafe side effect")

class ExampleSpider(SidekickSpider):
    name = "example"
    source_id = "src_example"
    endpoint = "https://example.com"
    beat = BeatIdentifier("government:city_council")
    geo = GeoIdentifier("us:il:springfield:springfield")
"""
    error = _validate_spider_code(code, "example.py")
    assert error is not None
    assert "Disallowed top-level statement" in error


def test_resolve_spider_destination_rejects_path_traversal():
    assert _resolve_spider_destination("../escape.py") is None
    assert _resolve_spider_destination("nested/path.py") is None


def test_resolve_spider_destination_accepts_basename():
    dest = _resolve_spider_destination("city_council_test.py")
    assert dest is not None
    assert dest.name == "city_council_test.py"


def test_extract_candidate_asset_urls_finds_script_embedded_assets():
    html = """
<html><body>
<script>
window.__DATA__ = {
  "video": "https://cdn.example.gov/meetings/1234/master.m3u8",
  "agenda": "/publicfiles/agenda_1234.pdf"
}
</script>
</body></html>
"""
    urls = _extract_candidate_asset_urls("https://example.gov/show/1234", html)
    assert "https://cdn.example.gov/meetings/1234/master.m3u8" in urls
    assert "https://example.gov/publicfiles/agenda_1234.pdf" in urls


def test_asset_class_from_url_classifies_document_video_audio():
    assert _asset_class_from_url("https://example.gov/publicfiles/agenda.pdf") == "document"
    assert _asset_class_from_url("https://cdn.example.gov/vod/meeting/master.m3u8") == "video"
    assert _asset_class_from_url("https://cdn.example.gov/audio/meeting.mp3") == "audio"


def test_asset_classes_in_code_detects_multiple_classes():
    code = """
import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier
from sidekick.spiders._base import SidekickSpider, RawItem

class ExampleSpider(SidekickSpider):
    name = "example"
    source_id = "src_example"
    endpoint = "https://example.com"
    beat = BeatIdentifier("government:city_council")
    geo = GeoIdentifier("us:il:springfield:springfield")
    expected_content = [
        {"media_type": "application/pdf", "content_type": "agenda"},
        {"media_type": "video/mp4", "content_type": "video-raw"},
    ]
"""
    classes = _asset_classes_in_code(code)
    assert "document" in classes
    assert "video" in classes


def test_has_detail_callback_method_true_for_parse_detail():
    code = """
import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier
from sidekick.spiders._base import SidekickSpider, RawItem

class ExampleSpider(SidekickSpider):
    name = "example"
    source_id = "src_example"
    endpoint = "https://example.com"
    beat = BeatIdentifier("government:city_council")
    geo = GeoIdentifier("us:il:springfield:springfield")

    def parse(self, response):
        return []

    def parse_detail(self, response):
        return []
"""
    assert _has_detail_callback_method(code, "example.py") is True
