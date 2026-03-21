import re
import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier
from sidekick.spiders._base import SidekickSpider, RawItem


class CityCouncilSanBernardinoCaAgendasSpider(SidekickSpider):
    """San Bernardino City Council gallery — agenda PDFs and video manifests from Cablecast detail pages."""

    name = "city_council_san_bernardino_ca_agendas"
    source_id = "src_san_bernardino_ca_cablecast_gallery_13"
    endpoint = "https://reflect-sanbernardino.cablecast.tv/internetchannel/gallery/13"
    beat = BeatIdentifier("government:city_council")
    geo = GeoIdentifier("us:ca:san_bernardino:san_bernardino")
    schedule = "0 6 * * WED"
    expected_content = [
        {"media_type": "application/pdf", "content_type": "agenda"},
        {"media_type": "application/vnd.apple.mpegurl", "content_type": "video-raw"},
        {"media_type": "application/x-mpegURL", "content_type": "video-raw"},
    ]

    def parse(self, response):
        for href in response.css('a[data-testid="gallery-tile-link"]::attr(href)').getall():
            yield scrapy.Request(response.urljoin(href), callback=self.parse_show)

        next_href = response.css('a[rel="next"]::attr(href)').get()
        if next_href:
            yield scrapy.Request(response.urljoin(next_href), callback=self.parse)

    def parse_show(self, response):
        title = response.css('h1::text').get(default='').strip() or None

        for pdf_href in response.css('embed[type="application/pdf"]::attr(src), a[aria-label*="view or download"]::attr(href)').getall():
            if pdf_href:
                yield scrapy.Request(response.urljoin(pdf_href), callback=self.parse_pdf, cb_kwargs={"title": title})

        # Hidden video manifest URLs are often present in JS/config, surfaced via candidate_asset_urls.
        for url in self._extract_manifest_urls(response):
            yield scrapy.Request(response.urljoin(url), callback=self.parse_manifest, cb_kwargs={"title": title})

        # Fallbacks from visible script/config tokens.
        for token_url in getattr(response, "candidate_asset_urls", []) or []:
            if self._looks_like_manifest(token_url):
                yield scrapy.Request(response.urljoin(token_url), callback=self.parse_manifest, cb_kwargs={"title": title})

    def _extract_manifest_urls(self, response):
        found = []
        text = response.text
        for m in re.finditer(r'https?://[^\"\'\s>]+\.m3u8(?:\?[^\"\'\s>]*)?', text):
            found.append(m.group(0))
        for m in re.finditer(r'(?<![A-Za-z0-9])(/[^\"\'\s>]+\.m3u8(?:\?[^\"\'\s>]*)?)', text):
            found.append(m.group(1))
        # de-dup while preserving order
        out = []
        seen = set()
        for u in found:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    def _looks_like_manifest(self, url):
        return ".m3u8" in url or "master.m3u8" in url or "playlist.m3u8" in url

    def parse_pdf(self, response, title=None):
        ct = response.headers.get(b"Content-Type", b"").decode(errors="ignore").split(";")[0].strip() or None
        yield RawItem(url=response.url, title=title, format_id="pdf", media_type=ct, body=response.body)

    def parse_manifest(self, response, title=None):
        ct = response.headers.get(b"Content-Type", b"").decode(errors="ignore").split(";")[0].strip() or None
        yield RawItem(url=response.url, title=title, format_id="hls", media_type=ct, body=response.body)
