"""
selenium_scraper.py — Extracts market value history from Transfermarkt using Selenium.

Transfermarkt's market value chart is rendered by a Svelte component that fetches
data from an internal JSON API. We use Selenium to navigate to the page (which sets
the required cookies/session), then execute a same-origin XHR to that API endpoint.
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


def _create_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=opts)


def _accept_cookies(driver: webdriver.Chrome):
    """Click cookie consent button if it appears."""
    try:
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Accept & continue']"))
        )
        btn.click()
        time.sleep(1)
    except (TimeoutException, NoSuchElementException):
        pass


def _fetch_club_names(driver: webdriver.Chrome, club_ids: list[str]) -> dict[str, str]:
    """Fetch club names from the TM internal API given a list of club IDs."""
    if not club_ids:
        return {}
    params = "&".join(f"ids[]={cid}" for cid in club_ids)
    script = f"""
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "https://tmapi-alpha.transfermarkt.technology/clubs?{params}", false);
    xhr.send();
    return xhr.responseText;
    """
    result = driver.execute_script(script)
    response = json.loads(result)
    if response.get("success") and "data" in response:
        return {str(c["id"]): c["name"] for c in response["data"]}
    return {}


def _fetch_market_value_history(driver: webdriver.Chrome, player_id: str) -> list[dict]:
    """Execute XHR to the TM internal API to get market value history JSON."""
    script = f"""
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "https://tmapi-alpha.transfermarkt.technology/player/{player_id}/market-value-history", false);
    xhr.send();
    return xhr.responseText;
    """
    result = driver.execute_script(script)
    response = json.loads(result)

    if not response.get("success") or "data" not in response:
        return []

    history = response["data"].get("history", [])
    club_ids = list({item["clubId"] for item in history if item.get("clubId")})
    club_names = _fetch_club_names(driver, club_ids)

    data_points = []
    for item in history:
        mv = item.get("marketValue", {})
        compact = mv.get("compact", {})
        data_points.append({
            "date_display": mv.get("determined", ""),
            "value_eur": mv.get("value"),
            "value_raw": f"{compact.get('prefix', '')}{compact.get('content', '')}{compact.get('suffix', '')}",
            "club_at_time": club_names.get(item.get("clubId", ""), ""),
            "age": item.get("age"),
            "season": item.get("seasonId"),
        })
    return data_points


def scrape_multiple_market_values(
    player_urls: list[str], max_players: int = 20
) -> dict[str, list[dict]]:
    """Scrape market value history for multiple players using a shared browser session."""
    driver = _create_driver()
    results: dict[str, list[dict]] = {}
    urls_to_scrape = player_urls[:max_players]

    try:
        for i, url in enumerate(tqdm(urls_to_scrape, desc="Selenium MV", unit="player"), 1):
            player_id_match = re.search(r"/spieler/(\d+)", url)
            if not player_id_match:
                continue
            player_id = player_id_match.group(1)

            mv_url = url.replace("/profil/", "/marktwertverlauf/")
            driver.get(mv_url)
            time.sleep(2)

            if i == 1:
                _accept_cookies(driver)

            history = _fetch_market_value_history(driver, player_id)
            results[url] = history
            time.sleep(3)
    finally:
        driver.quit()

    return results


if __name__ == "__main__":
    test_url = "https://www.transfermarkt.com/erling-haaland/profil/spieler/418560"
    data = scrape_multiple_market_values([test_url], max_players=1)
    for url, history in data.items():
        print(f"Found {len(history)} data points")
        for pt in history[:3]:
            print(f"  {pt}")
