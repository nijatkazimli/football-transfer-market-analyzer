"""Small regex helpers for parsing Transfermarkt strings."""

import re


def parse_market_value(raw):
    # examples: "€200.00m" -> 200000000, "€500k" -> 500000, "-" -> None
    if not raw or raw.strip() in ("-", ""):
        return None

    m = re.match(r"[€$£]?\s*([\d,.]+)\s*(m|k|bn)?", raw.strip(), re.IGNORECASE)
    if not m:
        return None

    number = float(m.group(1).replace(",", "."))
    suffix = (m.group(2) or "").lower()
    mult = {"m": 1_000_000, "k": 1_000, "bn": 1_000_000_000}.get(suffix, 1)
    return int(number * mult)


def extract_year(text):
    m = re.search(r"\b(19|20)\d{2}\b", text)
    return int(m.group()) if m else None


def extract_date(text):
    # DD/MM/YYYY or YYYY-MM-DD
    m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    return m.group(1) if m else None


def extract_age(text):
    # something like "21/07/2000 (25)"
    m = re.search(r"\((\d{1,2})\)", text)
    return int(m.group(1)) if m else None


def extract_height_cm(text):
    # "1,95 m" -> 195
    m = re.search(r"(\d)[,.](\d{2})\s*m", text)
    if not m:
        return None
    return int(m.group(1)) * 100 + int(m.group(2))


def clean_whitespace(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_player_id(url):
    m = re.search(r"/spieler/(\d+)", url)
    return m.group(1) if m else None


def extract_club_id(url):
    m = re.search(r"/verein/(\d+)", url)
    return m.group(1) if m else None
