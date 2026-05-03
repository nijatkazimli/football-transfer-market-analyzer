"""
scrapy_spider.py — Crawls Transfermarkt Premier League squads and collects player data.

Runs via subprocess to avoid Twisted reactor restart issues with Python 3.14.
"""

import scrapy
from scrapy.crawler import CrawlerProcess
from regex_utils import parse_market_value, clean_whitespace, extract_player_id
import json
import os
import subprocess
import sys

BASE_URL = "https://www.transfermarkt.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class TransfermarktSpider(scrapy.Spider):
    """Crawls PL league page → club squad pages → yields player records."""

    name = "transfermarkt_pl"
    allowed_domains = ["transfermarkt.com"]

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS": 1,
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": HEADERS["User-Agent"],
        "DEFAULT_REQUEST_HEADERS": HEADERS,
        "LOG_LEVEL": "INFO",
    }

    def __init__(self, season: str = "2025", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season
        self.start_urls = [
            f"{BASE_URL}/premier-league/startseite/wettbewerb/GB1"
        ]

    def parse(self, response):
        """Extract club links from league table, follow each squad page."""
        club_links = response.css(
            "table.items tbody tr td.hauptlink a[href*='/verein/']::attr(href)"
        ).getall()

        seen = set()
        for link in club_links:
            if link in seen or "/startseite/verein/" not in link:
                continue
            seen.add(link)
            squad_url = link.replace("/startseite/", "/kader/")
            if "/saison_id/" in squad_url:
                squad_url = squad_url.split("/saison_id/")[0]
            squad_url += f"/saison_id/{self.season}/plus/1"
            yield response.follow(squad_url, callback=self.parse_squad)

    def parse_squad(self, response):
        """Parse squad table rows and yield one item per player."""
        club_name = clean_whitespace(
            response.css("header.data-header h1::text").get(default="")
        )

        for row in response.css("table.items > tbody > tr"):
            name_tag = row.css("td.hauptlink a::text").get()
            if not name_tag:
                continue

            profile_href = row.css("td.hauptlink a::attr(href)").get(default="")
            market_value_raw = clean_whitespace(
                row.css("td.rechts.hauptlink a::text").get(default="")
            )

            zentriert_texts = row.css("td.zentriert::text").getall()

            yield {
                "player_name": clean_whitespace(name_tag),
                "player_id": extract_player_id(profile_href),
                "profile_url": BASE_URL + profile_href if profile_href else None,
                "club": club_name,
                "position": clean_whitespace(
                    row.css("td.posrela table tr:last-child td::text").get(default="")
                ),
                "date_of_birth_age": clean_whitespace(zentriert_texts[0]) if zentriert_texts else "",
                "nationalities": row.css("td.zentriert img.flaggenrahmen::attr(title)").getall(),
                "shirt_number": clean_whitespace(
                    row.css("div.rn_nummer::text").get(default="")
                ),
                "market_value_raw": market_value_raw,
                "market_value_eur": parse_market_value(market_value_raw),
            }


def run_scrapy_spider(output_path: str = "data/scrapy_players.json", season: str = "2025"):
    """Run the spider as a subprocess and return parsed JSON results."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(output_path):
        output_path = os.path.join(script_dir, output_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)

    spider_script = os.path.join(script_dir, "scrapy_spider.py")
    proc = subprocess.Popen(
        [sys.executable, spider_script, "--output", output_path, "--season", season],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=script_dir,
    )
    if proc.stdout:
        for line in proc.stdout:
            print(f"  [scrapy] {line}", end="")
    proc.wait()

    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    import argparse
    from scrapy.utils import misc as scrapy_misc
    import scrapy.core.scraper

    # Monkey-patch for Python 3.14 compatibility (inspect.getsource fails on generators)
    _noop = lambda spider, callable: None
    scrapy_misc.warn_on_generator_with_return_value = _noop
    scrapy.core.scraper.warn_on_generator_with_return_value = _noop  # type: ignore[attr-defined]

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/scrapy_players.json")
    parser.add_argument("--season", default="2025")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    process = CrawlerProcess(
        settings={
            "FEEDS": {args.output: {"format": "json", "overwrite": True}},
            "LOG_LEVEL": "INFO",
        }
    )
    process.crawl(TransfermarktSpider, season=args.season)
    process.start()
