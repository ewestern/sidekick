"""Unit tests for the Scrapy spider harness.

Covers: format detection, ArtifactWriterPipeline, DeduplicationMiddleware,
spider discovery, and SpiderMeta validation.

All database / object-store access is mocked.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest
import scrapy
from sidekick.core.vocabulary import ContentType, ProcessingProfile, Stage
from scrapy import signals
from scrapy.exceptions import DropItem

from sidekick.core.models import Artifact, Source
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier
from sidekick.spiders._base import SidekickSpider, RawItem, SpiderMeta
from sidekick.spiders._discovery import discover_spiders
from sidekick.spiders._format_registry import UnknownFormatError, detect_format
from sidekick.spiders._middleware import DeduplicationMiddleware
from sidekick.spiders._pipeline import ArtifactWriterPipeline
from sidekick.spiders._scaffold import _cron_daily_at_local, _names_from_parts


def _make_spider(**kwargs) -> SidekickSpider:
    """Dynamically create a minimal SidekickSpider subclass."""

    class _TestSpider(SidekickSpider):
        name = kwargs.get("name", "test-spider")
        source_id = kwargs.get("source_id", "src_test")
        endpoint = kwargs.get("endpoint", "https://example.com")
        beat = kwargs.get("beat", BeatIdentifier("government:city-council"))
        geo = kwargs.get("geo", GeoIdentifier("us:il:springfield:springfield"))
        schedule = kwargs.get("schedule", None)

        def parse(self, response):  # pragma: no cover
            return []

    spider = _TestSpider.__new__(_TestSpider)
    spider.crawler = MagicMock()
    return spider


def _make_pipeline(existing_artifacts=None, spider=None):
    artifact_store = MagicMock()
    object_store = MagicMock()
    artifact_store.query.return_value = existing_artifacts or []
    artifact_store.write.return_value = "art_new"
    object_store.put.return_value = "s3://artifacts/raw/_/_/art_new"
    pipeline = ArtifactWriterPipeline(artifact_store, object_store)
    pipeline._crawler = MagicMock()  # type: ignore[reportAttributeAccessIssue]
    pipeline._crawler.spider = spider or _make_spider()
    pipeline._ctx = MagicMock()
    pipeline._ctx.artifact_results = {}
    return pipeline, artifact_store, object_store


async def _collect_middleware_output(middleware, items):
    """Async helper to collect output from process_spider_output."""
    async def _aiter(it):
        for item in it:
            yield item

    return [item async for item in middleware.process_spider_output(None, _aiter(items))]


def _make_raw_item(**kwargs) -> RawItem:
    defaults = dict(
        url="https://example.com/doc.pdf",
        body=b"%PDF content",
        media_type="application/pdf",
        format_id="pdf",
        title=None,
    )
    defaults.update(kwargs)
    return RawItem(**defaults)


# ── detect_format ─────────────────────────────────────────────────────────────


def test_detect_format_pdf_by_extension():
    spec = detect_format("https://example.com/agenda.pdf", None, None)
    assert spec.format_id == "pdf"
    assert spec.content_type == "document-raw"


def test_detect_format_txt_by_extension():
    spec = detect_format("https://example.com/transcript.txt", None, None)
    assert spec.format_id == "txt"
    assert spec.stage == "processed"
    assert spec.content_type == "document-text"


def test_detect_format_m3u8_by_extension():
    spec = detect_format("https://example.com/stream.m3u8", None, None)
    assert spec.format_id == "hls"
    assert spec.is_async is True


def test_detect_format_ts_by_extension():
    spec = detect_format("https://example.com/segment.ts", None, None)
    assert spec.format_id == "mpeg-ts"
    assert spec.is_async is True


def test_detect_format_pdf_by_mime_header():
    spec = detect_format(
        "https://api.example.com/publicfiles/1", "application/pdf", None)
    assert spec.format_id == "pdf"


def test_detect_format_hls_alias_apple_mpegurl():
    """application/vnd.apple.mpegurl must resolve to hls — the San Bernardino case."""
    spec = detect_format(
        "https://example.com/video/1",
        "application/vnd.apple.mpegurl",
        None,
    )
    assert spec.format_id == "hls"
    assert spec.is_async is True


def test_detect_format_hls_alias_x_mpegurl():
    spec = detect_format(
        "https://example.com/video/1",
        "application/x-mpegURL",  # mixed case common in the wild
        None,
    )
    assert spec.format_id == "hls"


def test_detect_format_pdf_by_magic_bytes():
    spec = detect_format(
        "https://example.com/nodotextension", None, b"%PDF-1.4 ...")
    assert spec.format_id == "pdf"


def test_detect_format_hls_by_magic_bytes():
    spec = detect_format("https://example.com/stream",
                         None, b"#EXTM3U\n#EXT-X-VERSION:3")
    assert spec.format_id == "hls"


def test_detect_format_extension_beats_mime():
    """URL extension takes priority over Content-Type header."""
    spec = detect_format("https://example.com/doc.pdf", "text/html", b"<html>")
    assert spec.format_id == "pdf"


def test_detect_format_query_string_handled():
    """Query strings must not confuse extension detection."""
    spec = detect_format(
        "https://example.com/stream.m3u8?token=abc123", None, None)
    assert spec.format_id == "hls"


def test_detect_format_api_url_no_extension_uses_mime():
    """API URL with no extension falls through to Content-Type header."""
    spec = detect_format(
        "https://api.example.com/publicfiles/42", "application/pdf", None)
    assert spec.format_id == "pdf"


def test_detect_format_unknown_raises():
    with pytest.raises(UnknownFormatError):
        detect_format("https://example.com/mystery",
                      "application/x-unknown-format", None)


# ── SpiderMeta validation ─────────────────────────────────────────────────────


def test_spider_meta_validates_required_fields():
    spider = _make_spider()
    meta = spider.get_meta()
    assert isinstance(meta, SpiderMeta)
    assert meta.source_id == "src_test"
    assert meta.beat == "government:city-council"
    assert meta.geo == "us:il:springfield:springfield"


def test_spider_meta_allows_missing_beat():
    meta = SpiderMeta(
        name="x",
        source_id="src_x",
        endpoint="https://example.com",
        geo=GeoIdentifier("us:il:springfield:springfield"),
    )
    assert meta.beat is None


def test_spider_meta_raises_on_missing_required_field():
    with pytest.raises(Exception):
        SpiderMeta(  # type: ignore[call-arg]
            name="x",
            # source_id omitted — required field
            endpoint="https://example.com",
            geo=GeoIdentifier("us:il:springfield:springfield"),
        )


def test_spider_meta_schedule_optional():
    meta = SpiderMeta(
        name="x",
        source_id="src_x",
        endpoint="https://example.com",
        beat=BeatIdentifier("government:city-council"),
        geo=GeoIdentifier("us:il:springfield:springfield"),
    )
    assert meta.schedule is None


# ── ArtifactWriterPipeline ────────────────────────────────────────────────────


def test_pdf_written_to_object_store():
    item = _make_raw_item(url="https://example.com/agenda.pdf",
                          media_type="application/pdf", body=b"%PDF data")
    pipeline, artifact_store, object_store = _make_pipeline()

    pipeline.process_item(item)

    object_store.put.assert_called_once()
    assert object_store.put.call_args[0][1] == b"%PDF data"

    written: Artifact = artifact_store.write.call_args[0][0]
    assert written.content_uri is not None
    assert written.status == "active"
    assert written.processing_profile == ProcessingProfile.FULL


def test_processing_profile_from_raw_item():
    item = _make_raw_item(processing_profile="index")
    pipeline, artifact_store, _ = _make_pipeline()
    pipeline.process_item(item)
    written: Artifact = artifact_store.write.call_args[0][0]
    assert written.processing_profile == ProcessingProfile.INDEX


def test_spider_default_processing_profile():
    class _Spider(SidekickSpider):
        name = "prof-spider"
        source_id = "src_prof"
        endpoint = "https://example.com"
        beat = BeatIdentifier("government:city-council")
        geo = GeoIdentifier("us:il:springfield:springfield")
        default_processing_profile = ProcessingProfile.STRUCTURED

    spider = _Spider.__new__(_Spider)
    spider.crawler = MagicMock()
    pipeline, artifact_store, _ = _make_pipeline(spider=spider)
    item = _make_raw_item()
    pipeline.process_item(item)
    written: Artifact = artifact_store.write.call_args[0][0]
    assert written.processing_profile == ProcessingProfile.STRUCTURED


def test_html_stored_in_object_store():
    item = _make_raw_item(
        url="https://example.com/release.html",
        media_type="text/html",
        format_id="html",
        body=b"<html>Press release</html>",
    )
    pipeline, artifact_store, object_store = _make_pipeline()

    pipeline.process_item(item)

    object_store.put.assert_called_once()
    written: Artifact = artifact_store.write.call_args[0][0]
    assert written.content_uri is not None


def test_artifact_carries_source_metadata():
    spider = _make_spider(
        beat=BeatIdentifier("education:school-board"),
        geo=GeoIdentifier("us:il:springfield:springfield"),
        source_id="src_edu",
    )
    pipeline, artifact_store, _ = _make_pipeline(spider=spider)
    item = _make_raw_item()

    pipeline.process_item(item)

    art: Artifact = artifact_store.write.call_args[0][0]
    assert art.beat == "education:school-board"
    assert art.geo == "us:il:springfield:springfield"
    assert art.source_id == "src_edu"
    assert art.stage == "raw"
    assert art.created_by == "spider:test-spider"


def test_txt_written_as_processed_document_text():
    item = _make_raw_item(
        url="https://example.com/transcript.txt",
        media_type="text/plain",
        format_id="txt",
        body=b"Speaker: Ready for enrichment.",
    )
    pipeline, artifact_store, object_store = _make_pipeline()

    pipeline.process_item(item)

    object_store.put.assert_called_once()
    written: Artifact = artifact_store.write.call_args[0][0]
    assert written.stage == "processed"
    assert written.content_type == "document-text"
    assert written.media_type == "text/plain"
    assert written.derived_from is None


def test_item_beat_overrides_spider_beat():
    spider = _make_spider(beat=BeatIdentifier("government:city-council"))
    pipeline, artifact_store, _ = _make_pipeline(spider=spider)
    item = _make_raw_item(beat="education:school-board")

    pipeline.process_item(item)

    art: Artifact = artifact_store.write.call_args[0][0]
    assert art.beat == "education:school-board"


def test_artifact_beat_can_be_null_when_item_and_spider_lack_beat():
    spider = _make_spider(beat=None)
    pipeline, artifact_store, _ = _make_pipeline(spider=spider)
    item = _make_raw_item()

    pipeline.process_item(item)

    art: Artifact = artifact_store.write.call_args[0][0]
    assert art.beat is None


def test_source_url_entity_recorded():
    pipeline, artifact_store, _ = _make_pipeline()
    item = _make_raw_item(url="https://example.com/march.pdf")

    pipeline.process_item(item)

    art: Artifact = artifact_store.write.call_args[0][0]
    source_url_entities = [e for e in (
        art.entities or []) if e.get("type") == "source-url"]
    assert len(source_url_entities) == 1
    assert source_url_entities[0]["name"] == "https://example.com/march.pdf"


def test_title_entity_recorded_when_present():
    pipeline, artifact_store, _ = _make_pipeline()
    item = _make_raw_item(title="March Agenda")

    pipeline.process_item(item)

    art: Artifact = artifact_store.write.call_args[0][0]
    title_entities = [e for e in (
        art.entities or []) if e.get("type") == "title"]
    assert len(title_entities) == 1
    assert title_entities[0]["name"] == "March Agenda"


def test_m3u8_creates_stub_artifact():
    """HLS URLs must produce a pending_acquisition stub, not attempt an inline download."""
    url = "https://cdn.example.com/meeting.m3u8?token=abc"
    item = _make_raw_item(
        url=url, media_type="application/vnd.apple.mpegurl", format_id="hls", body=b"#EXTM3U")
    pipeline, artifact_store, object_store = _make_pipeline()

    pipeline.process_item(item)

    # No S3 write — content is not acquired yet
    object_store.put.assert_not_called()

    # Stub artifact written with correct fields
    written: Artifact = artifact_store.write.call_args[0][0]
    assert written.status == "pending_acquisition"
    assert written.acquisition_url == url
    assert written.content_uri is None
    assert written.content_type == "audio-raw"
    assert written.processing_profile == ProcessingProfile.FULL

def test_missing_format_id_raises_drop_item():
    """Items without format_id declared by the spider must be dropped immediately."""
    item = _make_raw_item(
        url="https://example.com/mystery",
        media_type="application/pdf",
        body=b"%PDF",
        format_id=None,
    )
    pipeline, artifact_store, _ = _make_pipeline()

    with pytest.raises(DropItem, match="format_id"):
        pipeline.process_item(item)

    artifact_store.write.assert_not_called()


def test_unknown_format_id_raises_drop_item():
    """Items declaring an unknown format_id (not in FORMAT_REGISTRY) must be dropped."""
    item = _make_raw_item(
        url="https://example.com/mystery",
        media_type="application/x-completely-unknown",
        body=b"\x00\x01\x02",
        format_id="not-a-real-format",
    )
    pipeline, artifact_store, _ = _make_pipeline()

    with pytest.raises(DropItem):
        pipeline.process_item(item)

    artifact_store.write.assert_not_called()


def test_stored_mime_type_is_canonical_not_source():
    """stored_mime_type comes from FormatSpec, not the raw Content-Type header."""
    # Source sends audio/mp3 (non-standard alias), but stored MIME should be audio/mpeg
    item = _make_raw_item(
        url="https://example.com/recording.mp3",
        media_type="audio/mp3",
        format_id="mp3",
        body=b"ID3\x04",
    )
    pipeline, artifact_store, _ = _make_pipeline()
    pipeline.process_item(item)

    written: Artifact = artifact_store.write.call_args[0][0]
    assert written.media_type == "audio/mpeg"


# ── DeduplicationMiddleware ───────────────────────────────────────────────────


def _make_middleware(existing_artifacts=None):
    artifact_store = MagicMock()
    artifact_store.query.return_value = existing_artifacts or []
    return DeduplicationMiddleware(artifact_store), artifact_store


def test_dedup_loads_seen_urls_on_spider_opened():
    existing = Artifact(
        id="art_old",
        title="March Agenda",
        content_type=ContentType.DOCUMENT_RAW,
        stage=Stage.RAW,
        entities=[
            {"type": "source-url", "name": "https://example.com/march.pdf"},
        ],
    )
    middleware, artifact_store = _make_middleware(
        existing_artifacts=[existing])
    spider = _make_spider()

    middleware.spider_opened(spider)

    assert "https://example.com/march.pdf" in middleware._seen


def test_dedup_from_crawler_connects_spider_opened_signal():
    artifact_store = MagicMock()
    crawler = MagicMock()
    crawler.settings = {"SIDEKICK_RUN_TOKEN": "run-token"}
    crawler.signals = MagicMock()
    crawler.signals.connect = MagicMock()

    with patch("sidekick.spiders._middleware.get_context") as get_context:
        get_context.return_value = MagicMock(artifact_store=artifact_store)
        instance = DeduplicationMiddleware.from_crawler(crawler)

    assert isinstance(instance, DeduplicationMiddleware)
    crawler.signals.connect.assert_called_once_with(
        instance.spider_opened, signal=signals.spider_opened
    )


def test_dedup_drops_seen_item():
    middleware, _ = _make_middleware()
    middleware._seen.add("https://example.com/already.pdf")

    item = _make_raw_item(url="https://example.com/already.pdf")
    output = asyncio.run(_collect_middleware_output(middleware, [item]))
    assert len(output) == 0


def test_dedup_passes_new_item():
    middleware, _ = _make_middleware()

    item = _make_raw_item(url="https://example.com/new.pdf")
    output = asyncio.run(_collect_middleware_output(middleware, [item]))
    assert len(output) == 1


def test_dedup_adds_new_url_to_seen():
    middleware, _ = _make_middleware()

    item = _make_raw_item(url="https://example.com/new.pdf")
    asyncio.run(_collect_middleware_output(middleware, [item]))

    assert "https://example.com/new.pdf" in middleware._seen


def test_dedup_prevents_duplicate_within_run():
    middleware, _ = _make_middleware()

    item1 = _make_raw_item(url="https://example.com/doc.pdf")
    item2 = _make_raw_item(url="https://example.com/doc.pdf")

    output = asyncio.run(_collect_middleware_output(
        middleware, [item1, item2]))
    assert len(output) == 1


def test_dedup_passes_non_raw_items_unchanged():
    """scrapy.Request objects (not RawItems) must be passed through unchanged."""
    middleware, _ = _make_middleware()

    req = scrapy.Request("https://example.com/page")
    output = asyncio.run(_collect_middleware_output(middleware, [req]))
    assert len(output) == 1
    assert output[0] is req


# ── discover_spiders ──────────────────────────────────────────────────────────


def test_discover_spiders_returns_dict():
    # The spiders package currently has no non-_ modules, so result should be empty.
    result = discover_spiders()
    assert isinstance(result, dict)


def test_discover_spiders_skips_underscore_modules():
    # Harness modules (_base, _pipeline, etc.) must not appear in results.
    result = discover_spiders()
    for source_id in result:
        cls = result[source_id]
        assert not cls.__module__.split(".")[-1].startswith("_")


def test_scaffold_names_are_derived_from_geo_and_source():
    names = _names_from_parts("us:ca:shasta:redding", "agendas")

    assert names["filename"] == "agendas.py"
    assert names["source_id"] == "src_us_ca_shasta_redding_agendas"
    assert names["spider_name"] == "redding-agendas"
    assert names["class_name"] == "ReddingAgendasSpider"


def test_cron_daily_at_local_uses_minute_and_hour():
    assert _cron_daily_at_local(datetime(2026, 3, 27, 14, 7, 0)) == "7 14 * * *"
    assert _cron_daily_at_local(datetime(2026, 1, 1, 0, 0, 0)) == "0 0 * * *"
