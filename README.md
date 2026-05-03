# Football Transfer Market Analyzer

Web scraping pipeline for Transfermarkt Premier League 2025/26 data using Scrapy, BeautifulSoup, Selenium, and Python regex.

**Author:** Nijat Kazimli  
**Website:** https://www.transfermarkt.com

## Project Structure

| File | Description |
|------|-------------|
| `report.ipynb` | Main Jupyter Notebook report (run this for the full pipeline) |
| `regex_utils.py` | Regex utility functions for data cleaning |
| `scrapy_spider.py` | Scrapy spider (crawls league & squad pages) |
| `profile_scraper.py` | requests + BeautifulSoup profile scraper |
| `selenium_scraper.py` | Selenium dynamic market value extractor |
| `main.py` | Standalone orchestrator script (alternative to notebook) |
| `requirements.txt` | Python package dependencies |
| `legal_proof.txt` | Legal justification for scraping |
| `data/` | Output directory (created automatically) |

## Output Data

| File | Content |
|------|---------|
| `data/scrapy_players.json` | Raw Scrapy output (528 players, 20 clubs) |
| `data/players_full.csv` | Merged player dataset |
| `data/market_value_history.csv` | Historical market values |

## How to Run

### Option A — Jupyter Notebook (recommended)

```bash
pip install -r requirements.txt
# Open report.ipynb and run all cells
```

### Option B — Command line

```bash
pip install -r requirements.txt
python main.py
```

## Prerequisites

- Python 3.10+
- Google Chrome (for Selenium WebDriver)
- ChromeDriver (automatically managed by selenium-manager)
- Internet connection

## Notes

- Respects `robots.txt` and uses a 3-second crawl delay
- Total runtime: ~15–20 minutes (due to polite delays)
- The notebook limits scraping to 30 profiles (BS4) and 10 players (Selenium) for demonstration — adjust `MAX_PROFILES_BS4` and `MAX_PLAYERS_SELENIUM` for a full crawl
