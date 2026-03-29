"""Spider stub — Shasta Pollution Control Board — Meetings.

TODO: implement parse() and any helper callbacks.
Run `sidekick fetch-url https://shastacounty.primegov.com/public/portal?committee=2` to inspect the page before writing selectors.
"""

from __future__ import annotations

import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier, ProcessingProfile
from sidekick.spiders._base import RawItem, SidekickSpider


class ShastaPollutionControlBoardMeetingsSpider(SidekickSpider):
    """Shasta Pollution Control Board — Meetings."""

    name = "shasta-pollution-control-board-meetings"
    source_id = "src_pollution_control_board_us_ca_shasta_meetings"
    endpoint = "https://shastacounty.primegov.com/public/portal?committee=2"
    beat = BeatIdentifier("government:pollution-control-board")
    geo = GeoIdentifier("us:ca:shasta")
    schedule = None

    wait_for_selector = "table[id='archivedMeetingsTable'] tr td:nth-child(4)"

    def parse(self, response):

        for row in response.css('table[id="archivedMeetingsTable"] tbody tr'):
            date = row.css("td:nth-child(2)::text").get()
            iso_date = self._parse_date(date)
            event_group = "-".join([self.source_id, iso_date]) if iso_date else None
            packet_href = row.xpath(
                ".//div[contains(@class,'left')]//a[normalize-space(text())='Packet']/@href"
            ).get()
            if packet_href:
                yield scrapy.Request(response.urljoin(packet_href), callback=self.parse_packet, cb_kwargs={"title": "Packet", "iso_date": iso_date, "event_group": event_group})
            agenda_href = row.xpath(
                ".//div[contains(@class,'left')]//a[normalize-space(text())='Agenda']/@href"
            ).get()
            if agenda_href:
                yield scrapy.Request(response.urljoin(agenda_href), callback=self.parse_agenda, cb_kwargs={"title": "Agenda", "iso_date": iso_date, "event_group": event_group})

            minutes_href = row.xpath(
                ".//div[contains(@class,'left')]//a[normalize-space(text())='Minutes']/@href"
            ).get()
            if minutes_href:
                yield scrapy.Request(response.urljoin(minutes_href), callback=self.parse_minutes, cb_kwargs={"title": "Minutes", "iso_date": iso_date, "event_group": event_group})

            video_href = row.css(
                "td:nth-child(4) a[title='Video']::attr(href)").get()
            if video_href:
                yield scrapy.Request(response.urljoin(video_href), callback=self.parse_listing, cb_kwargs={"iso_date": iso_date, "event_group": event_group})

    def parse_minutes(self, response, title=None, iso_date=None, event_group=None):
        ct = response.headers.get(
            b"Content-Type", b"").decode().split(";")[0].strip() or None
        yield RawItem(
            processing_profile=ProcessingProfile.FULL,
            event_group=event_group,
            url=response.url,
            title=title,
            format_id="pdf",
            media_type=ct,
            body=response.body,
            period_start=iso_date,
            period_end=iso_date,
        )

    def parse_packet(self, response, title=None, iso_date=None, event_group=None):
        ct = response.headers.get(
            b"Content-Type", b"").decode().split(";")[0].strip() or None
        yield RawItem(
            processing_profile=ProcessingProfile.EVIDENCE,
            event_group=event_group,
            url=response.url,
            title=title,
            format_id="pdf",
            media_type=ct,
            body=response.body,
            period_start=iso_date,
            period_end=iso_date,
        )

    def parse_agenda(self, response, title=None, iso_date=None, event_group=None):
        ct = response.headers.get(
            b"Content-Type", b"").decode().split(";")[0].strip() or None
        yield RawItem(
            processing_profile=ProcessingProfile.EVIDENCE,
            event_group=event_group,
            url=response.url,
            title=title,
            format_id="pdf",
            media_type=ct,
            body=response.body,
            period_start=iso_date,
            period_end=iso_date,
        )

    def parse_listing(self, response, iso_date=None, event_group=None):
        # On this page, the only thing we need is the transcript.
        # There is a div id = "transcript-fragments". We need to extract the text of every p and a tag, in order, within this div.
        # We can construct a text file from these, and that is our artifact.
        text = " ".join(response.css(
            "div#transcript-fragments p::text, div#transcript-fragments a::text").getall())
        yield RawItem(
            processing_profile=ProcessingProfile.FULL,
            event_group=event_group,
            url=response.url,
            title="Transcript",
            format_id="txt",
            media_type="text/plain",
            body=text.encode("utf-8"),
            period_start=iso_date,
            period_end=iso_date,
        )

    def _parse_date(self, raw: str) -> str | None:
        """Return ISO date string from a raw date string, or None."""
        from datetime import datetime
        raw = (raw or "").strip()
        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                continue
        return None

