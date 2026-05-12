"""Selenium scraper for player market value history.

The chart on Transfermarkt is rendered by a Svelte widget that hits an internal
JSON API. We open the page in a headless Chrome so the right cookies are set,
then run a same-origin XHR from inside the page to grab the JSON.
"""

import re
import time
import json
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def make_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument(f"user-agent={UA}")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=opts)


def accept_cookies(driver):
    try:
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Accept & continue']"))
        )
        btn.click()
        time.sleep(1)
    except (TimeoutException, NoSuchElementException):
        # banner didn't appear, that's fine
        pass


def fetch_club_names(driver, club_ids):
    if not club_ids:
        return {}
    params = "&".join(f"ids[]={cid}" for cid in club_ids)
    script = f"""
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "https://tmapi-alpha.transfermarkt.technology/clubs?{params}", false);
    xhr.send();
    return xhr.responseText;
    """
    response = json.loads(driver.execute_script(script))
    if response.get("success") and "data" in response:
        return {str(c["id"]): c["name"] for c in response["data"]}
    return {}


def fetch_market_value_history(driver, player_id):
    script = f"""
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "https://tmapi-alpha.transfermarkt.technology/player/{player_id}/market-value-history", false);
    xhr.send();
    return xhr.responseText;
    """
    response = json.loads(driver.execute_script(script))
    if not response.get("success") or "data" not in response:
        return []

    history = response["data"].get("history", [])
    club_ids = list({item["clubId"] for item in history if item.get("clubId")})
    club_names = fetch_club_names(driver, club_ids)

    points = []
    for item in history:
        mv = item.get("marketValue", {})
        c = mv.get("compact", {})
        points.append({
            "date_display": mv.get("determined", ""),
            "value_eur": mv.get("value"),
            "value_raw": f"{c.get('prefix', '')}{c.get('content', '')}{c.get('suffix', '')}",
            "club_at_time": club_names.get(item.get("clubId", ""), ""),
            "age": item.get("age"),
            "season": item.get("seasonId"),
        })
    return points


def scrape_multiple_market_values(player_urls, max_players=20):
    driver = make_driver()
    results = {}
    urls = player_urls[:max_players]

    try:
        for i, url in enumerate(tqdm(urls, desc="Selenium MV", unit="player"), 1):
            m = re.search(r"/spieler/(\d+)", url)
            if not m:
                continue
            player_id = m.group(1)

            mv_url = url.replace("/profil/", "/marktwertverlauf/")
            driver.get(mv_url)
            time.sleep(2)

            if i == 1:
                accept_cookies(driver)

            results[url] = fetch_market_value_history(driver, player_id)
            time.sleep(3)
    finally:
        driver.quit()

    return results
