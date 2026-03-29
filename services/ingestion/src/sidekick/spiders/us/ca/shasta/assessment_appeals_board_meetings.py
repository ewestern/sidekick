"""Spider stub — Shasta Assessment Appeals Board — Meetings.

TODO: implement parse() and any helper callbacks.
Run `sidekick fetch-url https://shastacounty.primegov.com/public/portal?committee=1` to inspect the page before writing selectors.
"""

from __future__ import annotations

import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier
from sidekick.spiders._base import RawItem, SidekickSpider
from sidekick.core.vocabulary import ProcessingProfile


class ShastaAssessmentAppealsBoardMeetingsSpider(SidekickSpider):
    """Shasta Assessment Appeals Board — Meetings."""

    name = "shasta-assessment-appeals-board-meetings"
    source_id = "src_assessment_appeals_board_us_ca_shasta_meetings"
    endpoint = "https://shastacounty.primegov.com/public/portal?committee=1"
    beat = BeatIdentifier("government:assessment-appeals-board")
    geo = GeoIdentifier("us:ca:shasta")
    schedule = None
    wait_for_selector = "table[id='archivedMeetingsTable'] tr td:nth-child(4)"

    def parse(self, response):
        ## table id *contains* archivedMeetingsTable
        for row in response.css('table[id*="archivedMeetingsTable"] tbody tr'):
            date = row.css("td:nth-child(2)::text").get()
            iso_date = self._parse_date(date)
            agenda_href = row.xpath(
                ".//div[contains(@class,'left')]//a[normalize-space(text())='Agenda']/@href"
            ).get()
            event_group = "-".join([self.source_id, iso_date]) if iso_date else None
            if agenda_href:
                yield scrapy.Request(response.urljoin(agenda_href), callback=self.parse_agenda, cb_kwargs={"title": "Agenda", "iso_date": iso_date, "event_group": event_group})

    # ── asset callbacks ──────────────────────────────────────────────────────

    def parse_agenda(self, response, title=None, iso_date=None, event_group=None):
        ct = response.headers.get(
            b"Content-Type", b"").decode().split(";")[0].strip() or None
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

    def parse_pdf(self, response, title=None, iso_date=None):
        ct = response.headers.get(
            b"Content-Type", b"").decode().split(";")[0].strip() or None
        yield RawItem(
            url=response.url,
            title=title,
            format_id="pdf",
            media_type=ct,
            body=response.body,
            period_start=iso_date,
            period_end=iso_date,
        )

    # Add more callbacks here as needed (parse_detail, parse_video, etc.)
