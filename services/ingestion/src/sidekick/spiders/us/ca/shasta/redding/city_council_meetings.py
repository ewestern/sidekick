"""Spider stub — Redding City Council — Meetings.

TODO: implement parse() and any helper callbacks.
Run `sidekick fetch-url https://reddingca.granicus.com/ViewPublisher.php?view_id=4` to inspect the page before writing selectors.
"""

from __future__ import annotations

import re
from datetime import datetime

import scrapy
from scrapy.http import Response
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier, ProcessingProfile
from sidekick.spiders._base import RawItem, SidekickSpider


class ReddingCityCouncilMeetingsSpider(SidekickSpider):
    """Redding City Council — Meetings."""

    name = "redding-city-council-meetings"
    source_id = "src_city_council_us_ca_shasta_redding_meetings"
    endpoint = "https://reddingca.granicus.com/ViewPublisher.php?view_id=4"
    beat = BeatIdentifier("government:city-council")
    geo = GeoIdentifier("us:ca:shasta:redding")
    schedule = None

    def parse(self, response):
        panels = response.xpath(
            "//div[contains(@class,'CollapsiblePanel')]"
            "[.//div[contains(@class,'CollapsiblePanelTab')][contains(normalize-space(.), 'Redding City Council')]]"
        )
        rows = panels.css("table.listingTable tbody tr.listingRow")

        for row in rows:
            meeting_name = self._clean_text(
                row.css("td:nth-child(1)::text").get(default="")
            )
            raw_date = self._clean_text(
                " ".join(row.css("td:nth-child(2)::text").getall())
            )
            duration = self._clean_text(
                " ".join(row.css("td:nth-child(3)::text").getall())
            )
            agenda_text = self._clean_text(
                " ".join(row.css("td:nth-child(4)::text").getall())
            )
            documents_text = self._clean_text(
                " ".join(row.css("td:nth-child(5)::text").getall())
            )

            iso_date = self._parse_date(raw_date)
            event_group = "-".join([self.source_id, iso_date]) if iso_date else None

            onclick = row.css("td:nth-child(6) a::attr(onclick)").get()
            video_url = self._extract_window_open_url(onclick, response)
            if not video_url:
                continue

            yield scrapy.Request(
                video_url,
                callback=self.parse_video_page,
                cb_kwargs={
                    "meeting_name": meeting_name,
                    "raw_date": raw_date,
                    "duration": duration,
                    "agenda_text": agenda_text,
                    "documents_text": documents_text,
                    "iso_date": iso_date,
                    "event_group": event_group,
                },
            )

    # ── asset callbacks ──────────────────────────────────────────────────────

    def _clean_text(self, value: str) -> str:
        return " ".join((value or "").replace("\xa0", " ").split())

    def _extract_window_open_url(
        self, onclick: str | None, response: Response
    ) -> str | None:
        if not onclick:
            return None
        match = re.search(r"window\.open\(\s*['\"]([^'\"]+)['\"]", onclick)
        if not match:
            return None

        url = match.group(1).strip()
        if url.startswith("//"):
            return f"{response.url.split(':', 1)[0]}:{url}"
        return response.urljoin(url)

    def _parse_date(self, raw: str) -> str | None:
        """Return ISO date (YYYY-MM-DD) from the Granicus Date column.

        Typical cell text after ``_clean_text``: ``March 17, 2026 - 5:57 PM``.
        The calendar date is the part before the `` - `` that separates date from time.
        """
        raw = (raw or "").strip()
        if not raw:
            return None
        # Split date vs time: HTML uses " - " between "March 17, 2026" and "5:57 PM"
        date_part = re.split(r"\s+-\s+", raw, maxsplit=1)[0].strip()
        # Normalize odd spacing from split text nodes (e.g. "March 17 , 2026")
        date_part = re.sub(r"\s*,\s*", ", ", date_part)
        date_part = re.sub(r"\s+", " ", date_part).strip()
        fmts = (
            "%B %d, %Y",
            "%b %d, %Y",
            "%m/%d/%Y",
            "%m/%d/%y",
            "%Y-%m-%d",
        )
        for fmt in fmts:
            try:
                return datetime.strptime(date_part, fmt).date().isoformat()
            except ValueError:
                continue
        return None
    def parse_pdf(self, response, title=None, iso_date=None, event_group=None):
        ct = response.headers.get(b"Content-Type", b"").decode().split(";")[0].strip() or None
        yield RawItem(
            processing_profile=ProcessingProfile.FULL,
            url=response.url,
            title=title,
            format_id="pdf",
            media_type=ct,
            body=response.body,
            period_start=iso_date,
            period_end=iso_date,
            event_group=event_group,
        )

    def parse_video_page(
        self,
        response,
        meeting_name=None,
        raw_date=None,
        duration=None,
        agenda_text=None,
        documents_text=None,
        iso_date=None,
        event_group=None,
    ):
        manifest_page_href = response.xpath('//*[@id="player"]/iframe/@src').get()
        if not manifest_page_href:
            return

        yield scrapy.Request(
            response.urljoin(manifest_page_href),
            callback=self.parse_video_manifest_page,
            cb_kwargs={
                "meeting_name": meeting_name,
                "raw_date": raw_date,
                "duration": duration,
                "agenda_text": agenda_text,
                "documents_text": documents_text,
                "iso_date": iso_date,
                "event_group": event_group,
            },
        )

    def parse_video_manifest_page(
        self,
        response,
        meeting_name=None,
        raw_date=None,
        duration=None,
        agenda_text=None,
        documents_text=None,
        iso_date=None,
        event_group=None,
    ):
        m3u8_href = response.css("video source::attr(src)").get()
        if not m3u8_href:
            return

        yield scrapy.Request(
            response.urljoin(m3u8_href),
            callback=self.parse_hls_manifest,
            cb_kwargs={
                "meeting_name": meeting_name,
                "raw_date": raw_date,
                "duration": duration,
                "agenda_text": agenda_text,
                "documents_text": documents_text,
                "iso_date": iso_date,
                "event_group": event_group,
            },
        )

    def parse_hls_manifest(
        self,
        response,
        meeting_name=None,
        raw_date=None,
        duration=None,
        agenda_text=None,
        documents_text=None,
        iso_date=None,
        event_group=None,
    ):
        ct = response.headers.get(b"Content-Type", b"").decode().split(";")[0].strip() or None
        yield RawItem(
            processing_profile=ProcessingProfile.FULL,
            event_group=event_group,
            url=response.url,
            title=meeting_name,
            format_id="hls",
            media_type=ct,
            body=response.body,
            period_start=iso_date,
            period_end=iso_date,
            meta={
                "raw_date": raw_date,
                "duration": duration,
                "agenda": agenda_text,
                "documents": documents_text,
            },
        )
