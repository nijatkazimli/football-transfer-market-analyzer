"""Scrapy spider that crawls the Premier League table and each club squad page.

The spider is run via subprocess from run_scrapy_spider() so that the Twisted
reactor can be started fresh each time (otherwise a second run from the same
Python process / Jupyter kernel would crash).
"""

import os
import sys
import json
import subprocess

import scrapy
from scrapy.crawler import CrawlerProcess

from regex_utils import parse_market_value, clean_whitespace, extract_player_id


BASE_URL = "https://www.transfermarkt.com"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}


class TransfermarktSpider(scrapy.Spider):
    """League page -> club squad pages -> one item per player."""

    name = "transfermarkt_pl"
    allowed_domains = ["transfermarkt.com"]

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS": 1,
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": UA,
        "DEFAULT_REQUEST_HEADERS": HEADERS,
        "LOG_LEVEL": "INFO",
    }

    def __init__(self, season="2025", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season
        self.start_urls = [f"{BASE_URL}/premier-league/startseite/wettbewerb/GB1"]

    def parse(self, response):
        # grab all club links from the league table, then go to each squad page
        links = response.css(
            "table.items tbody tr td.hauptlink a[href*='/verein/']::attr(href)"
        ).getall()

        seen = set()
        for link in links:
            if link in seen or "/startseite/verein/" not in link:
                continue
            seen.add(link)
            squad_url = link.replace("/startseite/", "/kader/") + f"/saison_id/{self.season}/plus/1"
            yield response.follow(squad_url, callback=self.parse_squad)

    def parse_squad(self, response):
        club_name = clean_whitespace(response.css("header.data-header h1::text").get(default=""))

        for row in response.css("table.items > tbody > tr"):
            name = row.css("td.hauptlink a::text").get()
            if not name:
                continue

            href = row.css("td.hauptlink a::attr(href)").get(default="")
            mv_raw = clean_whitespace(row.css("td.rechts.hauptlink a::text").get(default=""))
            zentriert = row.css("td.zentriert::text").getall()

            yield {
                "player_name": clean_whitespace(name),
                "player_id": extract_player_id(href),
                "profile_url": BASE_URL + href if href else None,
                "club": club_name,
                "position": clean_whitespace(
                    row.css("td.posrela table tr:last-child td::text").get(default="")
                ),
                "date_of_birth_age": clean_whitespace(zentriert[0]) if zentriert else "",
                "nationalities": row.css("td.zentriert img.flaggenrahmen::attr(title)").getall(),
                "shirt_number": clean_whitespace(row.css("div.rn_nummer::text").get(default="")),
                "market_value_raw": mv_raw,
                "market_value_eur": parse_market_value(mv_raw),
            }


def run_scrapy_spider(output_path="data/scrapy_players.json", season="2025"):
    """Run the spider in a separate process and load its JSON output."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(output_path):
        output_path = os.path.join(script_dir, output_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)

    proc = subprocess.Popen(
        [sys.executable, os.path.join(script_dir, "scrapy_spider.py"),
         "--output", output_path, "--season", season],
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
        with open(output_path, encoding="utf-8") as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    import argparse
    from scrapy.utils import misc as scrapy_misc
    import scrapy.core.scraper

    # Python 3.14: inspect.getsource fails inside Scrapy's generator-return check.
    # We disable the warning hook so the spider can run.
    noop = lambda spider, callable: None
    scrapy_misc.warn_on_generator_with_return_value = noop
    scrapy.core.scraper.warn_on_generator_with_return_value = noop  # type: ignore[attr-defined]

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/scrapy_players.json")
    parser.add_argument("--season", default="2025")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    process = CrawlerProcess(settings={
        "FEEDS": {args.output: {"format": "json", "overwrite": True}},
        "LOG_LEVEL": "INFO",
    })
    process.crawl(TransfermarktSpider, season=args.season)
    process.start()
