README
======

Name: Nijat Kazimli

Project: Football Transfer Market Analyzer
Website: https://www.transfermarkt.com (Premier League 2025/26)


FILES IN THIS PROJECT
---------------------

1. report.ipynb          - Main Jupyter Notebook report (run this for the full pipeline)
2. regex_utils.py        - Regex utility functions for data cleaning
3. scrapy_spider.py      - Scrapy spider module (crawls league & squad pages)
4. profile_scraper.py    - requests + BeautifulSoup profile scraper module
5. selenium_scraper.py   - Selenium dynamic market value extractor module
6. main.py               - Standalone orchestrator script (alternative to notebook)
7. requirements.txt      - Python package dependencies
8. legal_proof.txt       - Legal justification for scraping
9. data/                 - Output directory (created automatically)
    - scrapy_players.json       (raw Scrapy output)
    - players_full.csv          (merged player dataset)
    - market_value_history.csv  (historical market values)


ORDER OF EXECUTION
------------------

Option A — Jupyter Notebook (recommended):
  1. Install dependencies:  pip install -r requirements.txt
  2. Open and run:          report.ipynb (run all cells sequentially)

Option B — Command line:
  1. Install dependencies:  pip install -r requirements.txt
  2. Run:                   python main.py


PREREQUISITES
-------------
- Python 3.10+
- Google Chrome browser (for Selenium WebDriver)
- ChromeDriver (automatically managed by selenium-manager)
- Internet connection


DATASET LOCATION
----------------
The scraped dataset is included in the data/ directory.
If the dataset is too large, it will be available at:
[Google Drive link to be added if needed]


NOTES
-----
- The scraping respects robots.txt and uses a 3-second crawl delay.
- Total runtime: approximately 15-20 minutes (due to polite delays).
- The notebook limits scraping to 30 profiles (BS4) and 10 players (Selenium)
  for demonstration. Adjust MAX_PROFILES_BS4 and MAX_PLAYERS_SELENIUM for
  a full crawl.
