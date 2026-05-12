"""Scrapes individual player profile pages with requests + BeautifulSoup."""

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

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})


def get_info_value(soup, label):
    # Transfermarkt uses two different layouts for player info, so try both.
    label_lc = label.lower()

    # 1) header area
    for li in soup.select("li.data-header__label"):
        if label_lc in li.get_text(" ", strip=True).lower():
            span = li.select_one("span.data-header__content")
            if span:
                return clean_whitespace(span.get_text())

    # 2) info-table (label span, then bold value span next to it)
    info_table = soup.select_one("div.info-table")
    if info_table:
        for span in info_table.select("span.info-table__content--regular"):
            if label_lc in span.get_text().lower():
                value_span = span.find_next_sibling("span")
                if value_span:
                    return clean_whitespace(value_span.get_text())

    return ""


def scrape_player_profile(url, delay=2.0):
    time.sleep(delay)
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    data = {"profile_url": url}

    # full name: drop the shirt number span from the h1
    header = soup.select_one("header.data-header")
    if header:
        h1 = header.select_one("h1")
        if h1:
            for span in h1.select("span"):
                span.decompose()
            data["full_name"] = clean_whitespace(h1.get_text())

    dob_text = get_info_value(soup, "Date of birth")
    data["date_of_birth"] = extract_date(dob_text) or dob_text
    data["age"] = extract_age(dob_text)

    data["place_of_birth"] = get_info_value(soup, "Place of birth")

    height_text = get_info_value(soup, "Height")
    data["height_cm"] = extract_height_cm(height_text)

    # citizenship flags can be in either layout; dedup preserving order
    flag_imgs = soup.select("li.data-header__label img.flaggenrahmen")
    if not flag_imgs:
        flag_imgs = soup.select("span.info-table__content--bold img.flaggenrahmen")
    titles = [clean_whitespace(str(img.get("title", ""))) for img in flag_imgs if img.get("title")]
    data["citizenship"] = list(dict.fromkeys(titles))

    data["position"] = get_info_value(soup, "Position")
    data["foot"] = get_info_value(soup, "Foot")

    data["current_club"] = get_info_value(soup, "Current club")

    joined_text = get_info_value(soup, "Joined")
    data["joined"] = extract_date(joined_text) or joined_text

    contract_text = get_info_value(soup, "Contract expires")
    data["contract_expires"] = extract_date(contract_text) or contract_text
    data["contract_expires_year"] = extract_year(contract_text)

    # market value lives in the header; cut off the trailing "Last update: ..."
    mv_tag = soup.select_one("a.data-header__market-value-wrapper")
    if mv_tag:
        raw = clean_whitespace(mv_tag.get_text())
        raw = re.split(r"\s*Last update", raw)[0].strip()
        data["market_value_raw"] = raw
        data["market_value_eur"] = parse_market_value(raw)
    else:
        data["market_value_raw"] = ""
        data["market_value_eur"] = None

    # international caps/goals (shown as "12/3" near a national team link)
    data["international_caps"] = None
    data["international_goals"] = None
    intl_link = soup.select_one("span.info-table__content--bold a[href*='nationalmannschaft']")
    if intl_link:
        parent = intl_link.find_parent("li") or intl_link.find_parent("div")
        if parent:
            caps = re.search(r"(\d+)\s*/\s*(\d+)", parent.get_text())
            if caps:
                data["international_caps"] = int(caps.group(1))
                data["international_goals"] = int(caps.group(2))

    return data


def scrape_multiple_profiles(urls, delay=2.0):
    results = []
    for url in tqdm(urls, desc="BS4 profiles", unit="player"):
        try:
            results.append(scrape_player_profile(url, delay=delay))
        except Exception as e:
            tqdm.write(f"  error on {url}: {e}")
            results.append({"profile_url": url, "error": str(e)})
    return results
