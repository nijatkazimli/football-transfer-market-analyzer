"""
profile_scraper.py — Scrapes player profile pages using requests + BeautifulSoup.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from regex_utils import (
    clean_whitespace,
    extract_date,
    extract_age,
    extract_height_cm,
    parse_market_value,
    extract_year,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def _get_info_value(soup: BeautifulSoup, label: str) -> str:
    """Extract a value from the player info section by its label text.

    Transfermarkt uses two layouts depending on the section:
      1. li.data-header__label with span.data-header__content (header area)
      2. div.info-table with span pairs: regular (label) → bold (value)
    """
    for li in soup.select("li.data-header__label"):
        li_text = li.get_text(separator="|", strip=True)
        if label.lower() in li_text.lower():
            content_span = li.select_one("span.data-header__content")
            if content_span:
                return clean_whitespace(content_span.get_text())
            parts = li_text.split("|")
            for i, part in enumerate(parts):
                if label.lower() in part.lower() and i + 1 < len(parts):
                    return clean_whitespace(parts[i + 1])

    info_table = soup.select_one("div.info-table")
    if info_table:
        for span in info_table.select("span.info-table__content--regular"):
            if label.lower() in span.get_text().lower():
                value_span = span.find_next_sibling("span")
                if value_span:
                    return clean_whitespace(value_span.get_text())

    return ""


def scrape_player_profile(url: str, delay: float = 2.0) -> dict:
    """Fetch a single player profile page and return structured data."""
    time.sleep(delay)
    resp = SESSION.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    data: dict = {"profile_url": url}

    # Full name — remove shirt number <span> inside the <h1>
    header = soup.select_one("header.data-header")
    if header:
        name_tag = header.select_one("h1")
        if name_tag:
            for span in name_tag.select("span"):
                span.decompose()
            data["full_name"] = clean_whitespace(name_tag.get_text())

    # Date of birth and age
    dob_text = _get_info_value(soup, "Date of birth")
    data["date_of_birth"] = extract_date(dob_text) or dob_text
    data["age"] = extract_age(dob_text)

    data["place_of_birth"] = _get_info_value(soup, "Place of birth")

    height_text = _get_info_value(soup, "Height")
    data["height_cm"] = extract_height_cm(height_text)

    # Citizenship — deduplicated via dict.fromkeys
    citizenship_imgs = soup.select("li.data-header__label img.flaggenrahmen")
    if not citizenship_imgs:
        citizenship_imgs = soup.select("span.info-table__content--bold img.flaggenrahmen")
    data["citizenship"] = list(dict.fromkeys(
        clean_whitespace(str(img.get("title", "")))
        for img in citizenship_imgs if img.get("title")
    ))

    data["position"] = _get_info_value(soup, "Position")
    data["foot"] = _get_info_value(soup, "Foot")

    data["current_club"] = _get_info_value(soup, "Current club")
    joined_text = _get_info_value(soup, "Joined")
    data["joined"] = extract_date(joined_text) or joined_text
    contract_text = _get_info_value(soup, "Contract expires")
    data["contract_expires"] = extract_date(contract_text) or contract_text
    data["contract_expires_year"] = extract_year(contract_text)

    # Market value from header — strip trailing "Last update: ..." text
    mv_tag = soup.select_one("a.data-header__market-value-wrapper")
    if mv_tag:
        mv_raw = clean_whitespace(mv_tag.get_text())
        mv_raw = re.split(r"\s*Last update", mv_raw)[0].strip()
        data["market_value_raw"] = mv_raw
        data["market_value_eur"] = parse_market_value(mv_raw)
    else:
        data["market_value_raw"] = ""
        data["market_value_eur"] = None

    # International caps/goals
    data["international_caps"] = None
    data["international_goals"] = None
    intl_link = soup.select_one("span.info-table__content--bold a[href*='nationalmannschaft']")
    if intl_link:
        parent = intl_link.find_parent("li") or intl_link.find_parent("div")
        if parent:
            caps_match = re.search(r"(\d+)\s*/\s*(\d+)", parent.get_text())
            if caps_match:
                data["international_caps"] = int(caps_match.group(1))
                data["international_goals"] = int(caps_match.group(2))

    return data


def scrape_multiple_profiles(urls: list[str], delay: float = 2.0) -> list[dict]:
    """Scrape multiple player profiles with polite delays."""
    results = []
    for url in tqdm(urls, desc="BS4 profiles", unit="player"):
        try:
            results.append(scrape_player_profile(url, delay=delay))
        except Exception as e:
            tqdm.write(f"  Error: {e}")
            results.append({"profile_url": url, "error": str(e)})
    return results


if __name__ == "__main__":
    test_url = "https://www.transfermarkt.com/erling-haaland/profil/spieler/418560"
    result = scrape_player_profile(test_url)
    for k, v in result.items():
        print(f"  {k}: {v}")
