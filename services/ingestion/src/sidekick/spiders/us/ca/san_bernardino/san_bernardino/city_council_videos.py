import re
from datetime import datetime

import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier, ProcessingProfile
from sidekick.spiders._base import RawItem, SidekickSpider


class SanBernardinoCityCouncilVideosSpider(SidekickSpider):
    """San Bernardino City Council meetings — gallery pages with video manifests and agenda PDFs."""

    name = "san-bernardino-city-council-videos"
    source_id = "src_san_bernardino_city_council_videos"
    endpoint = "https://reflect-sanbernardino.cablecast.tv/internetchannel/gallery/13"
    beat = BeatIdentifier("government:city-council")
    geo = GeoIdentifier("us:ca:san-bernardino:san-bernardino")
    schedule = "0 8 * * WED"

    def _parse_date(self, raw: str) -> str | None:
        raw = (raw or "").strip()
        for fmt in ("%m/%d/%y", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                continue
        return None

    def parse(self, response):
        for href in response.css('a[data-testid="gallery-tile-link"]::attr(href)').getall():
            title = response.css(f'a[href="{href}"] div.font-bold::text').get()
            title = title.strip() if title else None
            iso_date = None
            if title:
                m = re.search(r"(\d{2}/\d{2}/\d{2,4})", title)
                if m:
                    iso_date = self._parse_date(m.group(1))
            yield scrapy.Request(
                response.urljoin(href),
                callback=self.parse_show,
                cb_kwargs={"title": title, "iso_date": iso_date},
            )

        next_href = response.css('a[rel="next"]::attr(href)').get()
        if next_href:
            yield scrapy.Request(response.urljoin(next_href), callback=self.parse)

    def parse_show(self, response, title=None, iso_date=None):
        if not iso_date:
            m = re.search(r"(\d{2}/\d{2}/\d{2,4})",
                          response.css("h1::text").get(default=""))
            if m:
                iso_date = self._parse_date(m.group(1))

        pdf_href = response.css(
            'embed[type="application/pdf"]::attr(src)').get()
        if pdf_href:
            yield scrapy.Request(
                response.urljoin(pdf_href),
                callback=self.parse_pdf,
                cb_kwargs={"title": title, "iso_date": iso_date},
            )

        video_src = response.css('iframe.trms-player::attr(src)').get()
        if video_src:
            yield scrapy.Request(
                response.urljoin(video_src),
                callback=self.parse_video_manifest,
                cb_kwargs={"title": title, "iso_date": iso_date},
            )

        for asset_href in response.css('a[href*="/publicfiles/"]::attr(href)').getall():
            yield scrapy.Request(
                response.urljoin(asset_href),
                callback=self.parse_pdf,
                cb_kwargs={"title": title, "iso_date": iso_date},
            )

        for asset_url in response.css('script::text').getall():
            for match in re.findall(r'https?://[^"\']+|/[^"\']+\.m3u8[^"\']*|/[^"\']+\.pdf[^"\']*', asset_url):
                if ".m3u8" in match:
                    yield scrapy.Request(
                        response.urljoin(match),
                        callback=self.parse_video_manifest,
                        cb_kwargs={"title": title, "iso_date": iso_date},
                    )
                elif ".pdf" in match:
                    yield scrapy.Request(
                        response.urljoin(match),
                        callback=self.parse_pdf,
                        cb_kwargs={"title": title, "iso_date": iso_date},
                    )

    def parse_pdf(self, response, title=None, iso_date=None):
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
            meta={"source": "agenda pdf"},
        )

    def parse_video_manifest(self, response, title=None, iso_date=None):
        ct = response.headers.get(
            b"Content-Type", b"").decode().split(";")[0].strip() or None
        yield RawItem(
            processing_profile=ProcessingProfile.FULL,
            url=response.url,
            title=title,
            format_id="hls",
            media_type=ct,
            body=response.body,
            period_start=iso_date,
            period_end=iso_date,
            meta={"source": "video manifest"},
        )
