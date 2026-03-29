"""Redding — City News (cityofredding.gov news list)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

import scrapy
from scrapy.http import Response
from sidekick.core.vocabulary import GeoIdentifier, ProcessingProfile, SourceTier
from sidekick.spiders._base import RawItem, SidekickSpider


class ReddingCityNewsSpider(SidekickSpider):
    """Redding — City News."""

    name = "redding-city-news"
    source_id = "src_us_ca_shasta_redding_city_news"
    endpoint = "https://www.cityofredding.gov/newslist.php"
    geo = GeoIdentifier("us:ca:shasta:redding")
    schedule = None
    source_tier = SourceTier.SECONDARY
    outlet = "City of Redding Press Release"

    def parse(self, response: Response) -> Any:
        for block in response.css("#newslist-container div.news-list-item"):
            href = block.xpath(
                ".//a[h3[contains(@class, 'news-title')]]/@href"
            ).get()
            if not href:
                continue
            title = self._clean_text(
                " ".join(block.xpath(".//h3[contains(@class, 'news-title')]//text()").getall())
            )
            raw_date = block.css(".news-date::text").get()
            iso_date = self._parse_news_teaser_date(raw_date)
            yield scrapy.Request(
                response.urljoin(href),
                callback=self.parse_article,
                cb_kwargs={"title": title or None, "iso_date": iso_date},
            )

    def parse_article(
        self,
        response: Response,
        title: str | None = None,
        iso_date: str | None = None,
    ) -> Any:
        """Fetch one news article page; body is plain text from ``#post_content``."""
        event_group = self._article_event_group(response.url)
        text = self._post_content_plain_text(response)
        resolved_title = (
            self._clean_text(title or "")
            or self._clean_text(response.css("title::text").get() or "")
        )
        yield RawItem(
            processing_profile=ProcessingProfile.FULL,
            url=response.url,
            title=resolved_title,
            format_id="txt",
            media_type="text/plain",
            body=text.encode("utf-8"),
            period_start=iso_date,
            period_end=iso_date,
            event_group=event_group,
        )

    def _post_content_plain_text(self, response: Response) -> str:
        """Collect text from every descendant text node under ``#post_content``, one per line."""
        root = response.xpath('//*[@id="post_content"]')
        if not root:
            return ""
        lines: list[str] = []
        for fragment in root.xpath(".//text()").getall():
            line = self._clean_text(fragment)
            if line:
                lines.append(line)
        return "\n".join(lines)

    def _article_event_group(self, url: str) -> str | None:
        match = re.search(r"_R(\d+)", url, flags=re.IGNORECASE)
        if not match:
            return None
        return f"{self.source_id}-r{match.group(1)}"

    def _clean_text(self, value: str) -> str:
        return " ".join((value or "").replace("\xa0", " ").split())

    def _parse_news_teaser_date(self, raw: str | None, ref: date | None = None) -> str | None:
        """Parse teaser lines like ``Mar 26`` (no year) using ``ref`` for the year.

        If the implied calendar date is more than one day after ``ref``, the prior
        year is used so December crawls still attach January teasers correctly.
        """
        raw = self._clean_text(raw or "")
        if not raw:
            return None
        ref_d = ref or date.today()
        for fmt in ("%b %d", "%B %d"):
            try:
                parsed = datetime.strptime(f"{raw} {ref_d.year}", f"{fmt} %Y").date()
                if parsed > ref_d + timedelta(days=1):
                    parsed = datetime.strptime(f"{raw} {ref_d.year - 1}", f"{fmt} %Y").date()
                return parsed.isoformat()
            except ValueError:
                continue
        return None
