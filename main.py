"""
main.py — Orchestrates the full scraping pipeline and exports CSVs.
"""

import os
import pandas as pd
from scrapy_spider import run_scrapy_spider
from profile_scraper import scrape_multiple_profiles
from selenium_scraper import scrape_multiple_market_values

DATA_DIR = "data"


def step1_scrapy_crawl() -> pd.DataFrame:
    print("=" * 60)
    print("STEP 1: Scrapy — Crawling Premier League squads")
    print("=" * 60)
    players = run_scrapy_spider(output_path=os.path.join(DATA_DIR, "scrapy_players.json"))
    df = pd.DataFrame(players)
    print(f"  → {len(df)} players collected\n")
    return df


def step2_bs4_profiles(scrapy_df: pd.DataFrame, max_players: int = 50) -> pd.DataFrame:
    print("=" * 60)
    print("STEP 2: requests + BeautifulSoup — Player profiles")
    print("=" * 60)
    n_clubs = scrapy_df["club"].nunique()
    per_club = max(1, max_players // n_clubs)
    sampled = (
        scrapy_df.dropna(subset=["profile_url"])
        .groupby("club", group_keys=False)
        .apply(lambda g: g.sample(min(len(g), per_club)))
    )
    urls = sampled["profile_url"].unique().tolist()[:max_players]
    print(f"  Scraping {len(urls)} profiles across {n_clubs} clubs...\n")

    profiles = scrape_multiple_profiles(urls, delay=2.0)
    df_profiles = pd.DataFrame(profiles)
    print(f"\n  → {len(df_profiles)} profiles scraped\n")
    return df_profiles


def step3_selenium_market_values(scrapy_df: pd.DataFrame, max_players: int = 20) -> pd.DataFrame:
    print("=" * 60)
    print("STEP 3: Selenium — Market value histories")
    print("=" * 60)
    top_players = (
        scrapy_df.dropna(subset=["market_value_eur"])
        .sort_values("market_value_eur", ascending=False)
        .head(max_players)
    )
    urls = top_players["profile_url"].dropna().unique().tolist()
    print(f"  Fetching history for {len(urls)} top players...\n")

    mv_data = scrape_multiple_market_values(urls, max_players=max_players)

    rows = []
    for url, history in mv_data.items():
        name_matches = top_players.loc[top_players["profile_url"] == url, "player_name"].values
        name = name_matches[0] if len(name_matches) > 0 else ""
        for pt in history:
            pt["player_name"] = name
            pt["profile_url"] = url
            rows.append(pt)

    df_mv = pd.DataFrame(rows)
    print(f"\n  → {len(df_mv)} data points collected\n")
    return df_mv


def step4_merge_and_export(scrapy_df: pd.DataFrame, profiles_df: pd.DataFrame, mv_df: pd.DataFrame):
    print("=" * 60)
    print("STEP 4: Merge and export")
    print("=" * 60)

    if not profiles_df.empty:
        merged = scrapy_df.merge(profiles_df, on="profile_url", how="left", suffixes=("_squad", "_profile"))
    else:
        merged = scrapy_df.copy()

    merged.to_csv(os.path.join(DATA_DIR, "players_full.csv"), index=False, encoding="utf-8-sig")
    print(f"  → players_full.csv ({len(merged)} rows)")

    if not mv_df.empty:
        mv_df.to_csv(os.path.join(DATA_DIR, "market_value_history.csv"), index=False, encoding="utf-8-sig")
        print(f"  → market_value_history.csv ({len(mv_df)} rows)")

    print()
    return merged, mv_df


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    scrapy_df = step1_scrapy_crawl()
    profiles_df = step2_bs4_profiles(scrapy_df, max_players=50)
    mv_df = step3_selenium_market_values(scrapy_df, max_players=20)
    step4_merge_and_export(scrapy_df, profiles_df, mv_df)
    print("Done.")


if __name__ == "__main__":
    main()
