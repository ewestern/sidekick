"""Spider stub — Shasta Board Of Supervisors — Meetings.

TODO: implement parse() and any helper callbacks.
Run `sidekick fetch-url https://shastacounty.primegov.com/public/portal?committee=3` to inspect the page before writing selectors.
"""

from __future__ import annotations

from datetime import datetime
import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier, ProcessingProfile
from sidekick.spiders._base import RawItem, SidekickSpider


class ShastaBoardOfSupervisorsMeetingsSpider(SidekickSpider):
    """Shasta Board Of Supervisors — Meetings."""

    name = "shasta-board-of-supervisors-meetings"
    source_id = "src_board_of_supervisors_us_ca_shasta_meetings"
    endpoint = "https://shastacounty.primegov.com/public/portal?committee=3"
    beat = BeatIdentifier("government:board-of-supervisors")
    geo = GeoIdentifier("us:ca:shasta")
    schedule = None
    wait_for_selector = "table[id='archivedMeetingsTable'] tr td:nth-child(4)"

    def parse(self, response):
        # Under table[id='archivedMeetingsTable > tbody, each tr contains a separate meeting, with links to relevant material
        # The second td has the date; In the third td, there are many links. We want the href of the anchor tag, which has a span
        # within it with the text "Packet"
        for row in response.css('table[id="archivedMeetingsTable"] tbody tr'):
            date = row.css("td:nth-child(2)::text").get()
            iso_date = self._parse_date(date)
            event_group = "-".join([self.source_id, iso_date]) if iso_date else None
            packet_href = row.xpath(
                ".//div[contains(@class,'left')]//a[normalize-space(text())='HTML Packet']/@href"
            ).get()
            if packet_href:
                yield scrapy.Request(response.urljoin(packet_href), callback=self.parse_packet_items, cb_kwargs={"title": "Packet", "iso_date": iso_date, "event_group": event_group})
            ## Agenda HREF
            agenda_href = row.xpath(
                ".//div[contains(@class,'left')]//a[normalize-space(text())='Agenda']/@href"
            ).get()
            if agenda_href:
                yield scrapy.Request(response.urljoin(agenda_href), callback=self.parse_agenda, cb_kwargs={"title": "Agenda", "iso_date": iso_date, "event_group": event_group})

            # Lastely, in the fourth td, there is a link to the listing page. a[title='Video']. Follow it.
            video_href = row.css(
                "td:nth-child(4) a[title='Video']::attr(href)").get()
            if video_href:
                yield scrapy.Request(response.urljoin(video_href), callback=self.parse_listing, cb_kwargs={ "iso_date": iso_date, "event_group": event_group})

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

    def parse_packet_items(self, response, title=None, iso_date=None, event_group=None):
        # Packet page structure:
        # - div.item_contents[id^="agenda_item_area_"]
        #   - div.attachment-holder
        #     - first <a>: preview link (/viewer/preview...)
        #     - second <a>: download link (/api/compilemeetingattachmenthistory/historyattachment/...)
        holders = response.css(
            'div.item_contents[id^="agenda_item_area_"] div.attachment-holder'
        )
        for holder in holders:
            download_anchor = holder.xpath(
                ".//a[contains(@href, '/api/compilemeetingattachmenthistory/historyattachment/')]"
            )
            href = download_anchor.attrib.get("href")
            if not href:
                continue

            text_title = " ".join(
                t.strip() for t in download_anchor.xpath(".//text()").getall() if t.strip()
            )
            anchor_title = (download_anchor.attrib.get("title") or "").strip()
            clean_title = text_title or anchor_title or title or "Packet Attachment"

            yield RawItem(
                processing_profile=ProcessingProfile.EVIDENCE,
                event_group=event_group,
                title=clean_title,
                url=response.urljoin(href),
                format_id="pdf",
                media_type="application/pdf",
                period_start=iso_date,
                period_end=iso_date,
            )

    # ── asset callbacks ──────────────────────────────────────────────────────

    # parse a date of this format
    # Mar 24, 2026 09:00 AM
    def _parse_date(self, raw: str) -> str | None:
        """Return ISO date string from a raw date string, or None."""
        raw = (raw or "").strip()
        for fmt in ("%b %d, %Y %I:%M %p", "%B %d, %Y %I:%M %p"):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                continue
        return None
