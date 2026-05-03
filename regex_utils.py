"""
regex_utils.py — Regex-based utilities for parsing and cleaning Transfermarkt data.
"""

import re


def parse_market_value(raw: str) -> int | None:
    """
    Convert a market-value string to euros.

    >>> parse_market_value("€200.00m")
    200000000
    >>> parse_market_value("€500k")
    500000
    >>> parse_market_value("-")
    """
    if not raw or raw.strip() in ("-", ""):
        return None

    raw = raw.strip()
    match = re.match(
        r"[€$£]?\s*([\d,.]+)\s*(m|k|bn)?", raw, re.IGNORECASE
    )
    if not match:
        return None

    number = float(match.group(1).replace(",", "."))
    suffix = (match.group(2) or "").lower()

    multiplier = {"m": 1_000_000, "k": 1_000, "bn": 1_000_000_000}.get(
        suffix, 1
    )
    return int(number * multiplier)


def extract_year(text: str) -> int | None:
    """
    Pull a four-digit year from a string.

    >>> extract_year("Contract expires: Jun 30, 2026")
    2026
    """
    match = re.search(r"\b(19|20)\d{2}\b", text)
    return int(match.group()) if match else None


def extract_date(text: str) -> str | None:
    """
    Extract a date in DD/MM/YYYY or YYYY-MM-DD format.

    >>> extract_date("Joined: 01/07/2022")
    '01/07/2022'
    """
    match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text)
    if match:
        return match.group(1)
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    return match.group(1) if match else None


def extract_age(text: str) -> int | None:
    """
    Extract age from strings like '21/07/2000 (25)'.

    >>> extract_age("21/07/2000 (25)")
    25
    """
    match = re.search(r"\((\d{1,2})\)", text)
    return int(match.group(1)) if match else None


def extract_height_cm(text: str) -> int | None:
    """
    Convert height string like '1,95 m' to centimetres.

    >>> extract_height_cm("1,95 m")
    195
    """
    match = re.search(r"(\d)[,.](\d{2})\s*m", text)
    if match:
        return int(match.group(1)) * 100 + int(match.group(2))
    return None


def clean_whitespace(text: str) -> str:
    """Collapse all whitespace into single spaces and strip."""
    return re.sub(r"\s+", " ", text).strip()


def extract_player_id(url: str) -> str | None:
    """
    Extract numeric player ID from a Transfermarkt URL.

    >>> extract_player_id("/erling-haaland/profil/spieler/418560")
    '418560'
    """
    match = re.search(r"/spieler/(\d+)", url)
    return match.group(1) if match else None


def extract_club_id(url: str) -> str | None:
    """
    Extract numeric club ID from a Transfermarkt URL.

    >>> extract_club_id("/manchester-city/startseite/verein/281")
    '281'
    """
    match = re.search(r"/verein/(\d+)", url)
    return match.group(1) if match else None
