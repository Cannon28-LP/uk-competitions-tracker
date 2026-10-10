import re, time, json, urllib.robotparser, urllib.parse, logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

LONDON = ZoneInfo("Europe/London")
UA = "Mozilla/5.0 (compatible; PersonalCompTracker/1.0; single-user personal use; hourly, polite; no logins)"
log = logging.getLogger("comp")

def now():
    return datetime.now(LONDON)

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

def parse_date(text, default_hour=23, default_min=59):
    """Parse '15th Nov 2026' / '10 October 2026' -> aware datetime (end of day). None if no match."""
    if not text:
        return None
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?[ ,]+([A-Za-z]{3,9})\.?,?[ ,]+(20\d\d)", text)
    if not m:
        return None
    mon = MONTHS.get(m.group(2)[:3].lower())
    if not mon:
        return None
    try:
        return datetime(int(m.group(3)), mon, int(m.group(1)), default_hour, default_min, tzinfo=LONDON)
    except ValueError:
        return None

def infer_year(day, month, hour=23, minute=59):
    n = now()
    for y in (n.year, n.year + 1, n.year - 1):
        try:
            d = datetime(y, month, day, hour, minute, tzinfo=LONDON)
        except ValueError:
            continue
        if y == n.year and d >= n - timedelta(days=45):
            return d
        if y == n.year + 1 and d > n:
            return d
    return None

def money(text):
    """first £ amount in text -> float, supports k/m suffix."""
    if text is None:
        return None
    m = re.search(r"£\s?([\d,]+(?:\.\d+)?)\s?(k|m|million|bn)?\b", text, re.I)
    if not m:
        return None
    v = float(m.group(1).replace(",", ""))
    s = (m.group(2) or "").lower()
    if s == "k": v *= 1e3
    elif s in ("m", "million"): v *= 1e6
    return v

def pence_or_pounds(text):
    """'90p' or '£1.29' -> pounds"""
    if not text: return None
    t = text.strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)p", t)
    if m: return float(m.group(1)) / 100
    return money(t)

_BAD_CTX = re.compile(r"(spend|spent|from|for just|for only|just|only|entry|ticket|per|each|deposit|bonus|extra|off)\s*$", re.I)
def prize_value_from_text(text):
    """Conservative: value stated in the title/description. Returns float or None."""
    if not text: return None
    t = text.replace("\u2011", "-")
    m = re.search(r"(?:worth|valued at|value of|value)\s*(?:over|up to|around|approx\.?)?\s*:?\s*£\s?([\d,]+(?:\.\d+)?)\s?(k|m|million)?", t, re.I)
    cands = []
    if m:
        v = float(m.group(1).replace(",", "")); s = (m.group(2) or "").lower()
        v *= {"k": 1e3, "m": 1e6, "million": 1e6}.get(s, 1)
        return v
    for m in re.finditer(r"£\s?([\d,]+(?:\.\d+)?)\s?(k|m|million)?(?![\w])", t, re.I):
        pre = t[max(0, m.start() - 14):m.start()]
        if _BAD_CTX.search(pre): continue
        try: v = float(m.group(1).replace(",", ""))
        except ValueError: continue
        s = (m.group(2) or "").lower()
        v *= {"k": 1e3, "m": 1e6, "million": 1e6}.get(s, 1)
        cands.append(v)
    return max(cands) if cands else None

def norm(s):
    s = (s or "").lower()
    s = re.sub(r"&amp;", "&", s)
    s = re.sub(r"[^a-z0-9£ ]+", " ", s)
    s = re.sub(r"\b(win|this|a|an|the|free entry|free|competition|giveaway)\b", " ", s)
    return re.sub(r"\s+", "", s)

def norm_promoter(s):
    s = (s or "").lower()
    s = re.sub(r"\b(competitions?|comps?|giveaways?|the|limited|ltd|prizes?|draws?)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)

class Fetcher:
    """Polite fetcher: robots.txt check, per-host delay, identifiable UA, no cookies persisted across logins."""
    def __init__(self, delay=1.0):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.8"})
        self.delay = delay
        self.last = {}
        self.robots = {}
        self.errors = []
        self.count = 0

    def _robots(self, url):
        p = urllib.parse.urlsplit(url)
        host = f"{p.scheme}://{p.netloc}"
        if host not in self.robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.s.get(host + "/robots.txt", timeout=15)
                if r.status_code == 200 and "html" not in r.headers.get("content-type", "") and "<html" not in r.text[:300].lower():
                    rp.parse(r.text.splitlines())
                else:
                    rp.parse([])
            except Exception:
                rp.parse([])
            self.robots[host] = rp
        return self.robots[host]

    def allowed(self, url):
        try:
            return self._robots(url).can_fetch(UA, url) and self._robots(url).can_fetch("*", url)
        except Exception:
            return True

    def get(self, url, **kw):
        if not self.allowed(url):
            self.errors.append(f"robots-disallowed {url}")
            log.warning("robots disallow %s", url)
            return None
        host = urllib.parse.urlsplit(url).netloc
        wait = self.delay - (time.time() - self.last.get(host, 0))
        if wait > 0: time.sleep(wait)
        for attempt in (1, 2):
            try:
                r = self.s.get(url, timeout=30, **kw)
                self.last[host] = time.time()
                self.count += 1
                if r.status_code == 200:
                    return r
                if r.status_code in (403, 429, 503):
                    self.errors.append(f"HTTP {r.status_code} {url}")
                    return None
                if r.status_code == 404:
                    self.errors.append(f"HTTP 404 {url}")
                    return None
                self.errors.append(f"HTTP {r.status_code} {url}")
            except Exception as e:
                self.last[host] = time.time()
                if attempt == 2:
                    self.errors.append(f"{type(e).__name__} {url}")
                    return None
                time.sleep(3)
        return None
