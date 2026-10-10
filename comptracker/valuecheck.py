"""Sanity check for prize values that come from headline text (e.g. 'Win £1.4M+ Prize Every Time').
A flagged value is NOT shown as the prize value (so it can't top 'Biggest prize' or pass the value filter); the claimed figure is
kept in `prize_value_claimed` with a note, and the page shows it as 'unverified'. Nothing is invented: values are only removed from
the headline slot, never replaced."""
import re
from .util import prize_value_from_text

# generous per-category ceilings for ONE prize; above this a title-derived figure is almost always a headline/aggregate claim
CAPS = {"Cars": 5e6, "Motorbikes": 3e5, "Boats": 1e7, "Home/Property": 1.5e7, "Money/Cash": 5e6, "Holidays/Travel": 2.5e5,
        "Tech/Gadgets": 1e5, "Gift cards/Vouchers": 1e5, "Experiences/Events": 2.5e5, "Fashion/Beauty": 2.5e5,
        "Food/Drink": 5e4, "Family/Kids": 5e4, "Other": 1e6}
ABSOLUTE_MAX = 5e7
HEDGE = re.compile(r"(\bevery\s*time\b|\beach\s*time\b|\bup\s*to\b|\bper\s+(?:day|week|month|win|entry)\b|\bfrom\s+£|£\s?[\d.,]+\s?(?:k|m|bn|million)?\s?\+(?!\s*£)|\bchance of winning\b|\bpotential\b|\bbonus\b.*£)", re.I)
ALT = re.compile(r"\bor\s+(?:up to\s+)?£", re.I)
ASSET = {"Cars", "Boats", "Home/Property"}
ASSET_WORDS = re.compile(r"\b(house|home|townhouse|penthouse|cottages?|villa|bungalow|apartment|flat|property|mansion|farm|barn|lodge|land)\b", re.I)

def check(item):
    """-> (value, claimed, note). value is the (possibly cleared) prize value."""
    v = item.get("prize_value")
    if v is None: return None, None, ""
    text = f"{item.get('title','')} {item.get('prize_desc','')}"
    cat = item.get("category") or "Other"
    if cat in ASSET or ASSET_WORDS.search(item.get("title", "")): cat = "Home/Property"
    # only figures lifted from the headline text are second-guessed; a value the source states in its own data field is kept
    if abs((prize_value_from_text(text) or -1) - v) > 1 and abs((prize_value_from_text(item.get("title", "")) or -1) - v) > 1 and v <= ABSOLUTE_MAX:
        return v, None, ""
    if v > ABSOLUTE_MAX:
        return None, v, "Figure is implausibly large; ignored."
    if v >= 100000 and HEDGE.search(text):
        return None, v, "Headline figure from the title ('up to' / 'every time' / '+'), not a single guaranteed prize."
    if v >= 100000 and ALT.search(text) and cat not in ASSET:
        return None, v, "Title offers alternatives ('… or £…'); the top figure may not be what you'd win."
    if v > CAPS.get(cat, 1e5):
        return None, v, f"Unusually high for a {cat.lower()} prize; treated as unverified."
    return v, None, ""
