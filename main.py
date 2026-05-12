"""Runs the whole scraping pipeline and writes CSVs."""

import os
import pandas as pd

from scrapy_spider import run_scrapy_spider
from profile_scraper import scrape_multiple_profiles
from selenium_scraper import scrape_multiple_market_values

DATA_DIR = "data"


def banner(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def step1_scrapy_crawl():
    banner("STEP 1: Scrapy - crawl Premier League squads")
    players = run_scrapy_spider(output_path=os.path.join(DATA_DIR, "scrapy_players.json"))
    df = pd.DataFrame(players)
    print(f"  {len(df)} players collected")
    return df


def step2_bs4_profiles(scrapy_df, max_players=50):
    banner("STEP 2: requests + BeautifulSoup - player profiles")

    n_clubs = scrapy_df["club"].nunique()
    per_club = max(1, max_players // n_clubs)

    # take a small sample per club so we cover all teams
    sampled = (
        scrapy_df.dropna(subset=["profile_url"])
        .groupby("club", group_keys=False)
        .apply(lambda g: g.sample(min(len(g), per_club)))
    )
    urls = sampled["profile_url"].unique().tolist()[:max_players]
    print(f"  scraping {len(urls)} profiles across {n_clubs} clubs...")

    profiles = scrape_multiple_profiles(urls, delay=2.0)
    df_profiles = pd.DataFrame(profiles)
    print(f"  got {len(df_profiles)} profiles")
    return df_profiles


def step3_selenium_market_values(scrapy_df, max_players=20):
    banner("STEP 3: Selenium - market value histories")

    top_players = (
        scrapy_df.dropna(subset=["market_value_eur"])
        .sort_values("market_value_eur", ascending=False)
        .head(max_players)
    )
    urls = top_players["profile_url"].dropna().unique().tolist()
    print(f"  fetching history for {len(urls)} top players...")

    mv_data = scrape_multiple_market_values(urls, max_players=max_players)
    name_by_url = dict(zip(top_players["profile_url"], top_players["player_name"]))

    rows = []
    for url, history in mv_data.items():
        for pt in history:
            pt["player_name"] = name_by_url.get(url, "")
            pt["profile_url"] = url
            rows.append(pt)

    df_mv = pd.DataFrame(rows)
    print(f"  {len(df_mv)} data points collected")
    return df_mv


def step4_merge_and_export(scrapy_df, profiles_df, mv_df):
    banner("STEP 4: merge and export")

    if not profiles_df.empty:
        merged = scrapy_df.merge(
            profiles_df, on="profile_url", how="left", suffixes=("_squad", "_profile")
        )
    else:
        merged = scrapy_df.copy()

    merged.to_csv(os.path.join(DATA_DIR, "players_full.csv"), index=False, encoding="utf-8-sig")
    print(f"  players_full.csv ({len(merged)} rows)")

    if not mv_df.empty:
        mv_df.to_csv(
            os.path.join(DATA_DIR, "market_value_history.csv"),
            index=False, encoding="utf-8-sig",
        )
        print(f"  market_value_history.csv ({len(mv_df)} rows)")

    return merged, mv_df


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    scrapy_df = step1_scrapy_crawl()
    profiles_df = step2_bs4_profiles(scrapy_df, max_players=50)
    mv_df = step3_selenium_market_values(scrapy_df, max_players=20)
    step4_merge_and_export(scrapy_df, profiles_df, mv_df)
    print("\nDone.")


if __name__ == "__main__":
    main()
