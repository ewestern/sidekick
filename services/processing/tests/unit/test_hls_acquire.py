"""HLS acquisition (mocked ffmpeg)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from sidekick.core.models import Artifact

from sidekick.processing.acquisition.hls import acquire_hls_stub


def _write_fake_audio(_url: str, out_path: Path) -> None:
    out_path.write_bytes(b"fake-audio")


def test_acquire_hls_stub_puts_bytes_and_completes():
    row = Artifact(
        id="art_hls",
        content_type="audio-raw",
        stage="raw",
        status="pending_acquisition",
        acquisition_url="https://example.com/stream.m3u8",
        beat="government:city_council",
        geo="us:il:springfield:springfield",
    )
    store = MagicMock()
    store.read_row.return_value = row
    object_store = MagicMock()
    object_store.put.return_value = "s3://bucket/artifacts/raw/government-city_council/us-il-springfield-springfield/art_hls"

    with patch(
        "sidekick.processing.acquisition.hls._ffmpeg_hls_to_mp3",
        side_effect=_write_fake_audio,
    ):
        acquire_hls_stub("art_hls", store, object_store)

    object_store.put.assert_called_once()
    put_body = object_store.put.call_args[0][1]
    assert put_body == b"fake-audio"
    store.complete_acquisition.assert_called_once()
    c_args, c_kwargs = store.complete_acquisition.call_args
    assert c_args[0] == "art_hls"
    assert c_args[1].startswith("s3://")
    assert c_kwargs.get("media_type") == "audio/mpeg"
