import re, time, json, random, urllib.robotparser, urllib.parse, logging
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
        if "," in m.group(1) and s == "k": s = ""   # "£111,222.33k" is already in pounds
        v *= {"k": 1e3, "m": 1e6, "million": 1e6}.get(s, 1)
        return v
    for m in re.finditer(r"£\s?([\d,]+(?:\.\d+)?)\s?(k|m|million)?(?![\w])", t, re.I):
        pre = t[max(0, m.start() - 14):m.start()]
        if _BAD_CTX.search(pre): continue
        try: v = float(m.group(1).replace(",", ""))
        except ValueError: continue
        s = (m.group(2) or "").lower()
        if "," in m.group(1) and s == "k": s = ""
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
    """Polite fetcher: robots.txt check, per-host delay, identifiable UA, no cookies persisted across logins.

    Reliability: transient failures (timeouts, connection errors, 5xx, 429, HTTP 202 'not ready') are retried with
    exponential backoff + jitter; 403/404 are final (retrying a block only makes us less polite). After a few 403s from
    one host in a run, the host is skipped for the rest of the run instead of hammering it."""
    RETRY_STATUS = {202, 408, 425, 429, 500, 502, 503, 504}

    def __init__(self, delay=1.0, retries=3, timeout=(10, 30), backoff=2.0, max_backoff=20.0, host_block_after=3):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.8"})
        self.delay = delay
        self.retries, self.timeout, self.backoff, self.max_backoff = retries, timeout, backoff, max_backoff
        self.host_block_after = host_block_after
        self.last = {}
        self.robots = {}
        self.blocked = {}      # host -> consecutive 403 count
        self.errors = []
        self.count = 0
        self.retried = 0

    def _robots(self, url):
        p = urllib.parse.urlsplit(url)
        host = f"{p.scheme}://{p.netloc}"
        if host not in self.robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.s.get(host + "/robots.txt", timeout=(10, 15))
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

    def _sleep_backoff(self, attempt, retry_after=None):
        d = min(self.max_backoff, self.backoff * (2 ** (attempt - 1))) * random.uniform(0.8, 1.25)
        if retry_after is not None: d = max(d, min(float(retry_after), 30.0))
        time.sleep(d)

    def get(self, url, timeout=None, retries=None, **kw):
        if not self.allowed(url):
            self.errors.append(f"robots-disallowed {url}")
            log.warning("robots disallow %s", url)
            return None
        host = urllib.parse.urlsplit(url).netloc
        if self.blocked.get(host, 0) >= self.host_block_after:
            self.errors.append(f"HTTP 403 (host blocked this run, skipped) {url}")
            return None
        attempts = max(1, (self.retries if retries is None else retries))
        last_err = ""
        for attempt in range(1, attempts + 1):
            wait = self.delay - (time.time() - self.last.get(host, 0))
            if wait > 0: time.sleep(wait)
            retry_after = None
            t0 = time.time()
            try:
                r = self.s.get(url, timeout=timeout or self.timeout, **kw)
                self.last[host] = time.time(); self.count += 1
                sc = r.status_code
                if sc == 200:
                    self.blocked[host] = 0
                    return r
                if sc == 403:
                    self.blocked[host] = self.blocked.get(host, 0) + 1
                    self.errors.append(f"HTTP 403 {url}")
                    return None
                if sc in (404, 410):
                    self.errors.append(f"HTTP {sc} {url}")
                    return None
                waf = r.headers.get("x-amzn-waf-action") or r.headers.get("cf-mitigated") or ""
                last_err = f"HTTP {sc}" + (f" ({'bot-challenge: ' + waf if waf else 'not ready / accepted-only response'})" if sc == 202 else "") + f" {url}"
                if sc not in self.RETRY_STATUS:
                    self.errors.append(last_err); return None
                ra = r.headers.get("retry-after")
                retry_after = int(ra) if ra and ra.isdigit() else None
            except requests.RequestException as e:
                self.last[host] = time.time()
                last_err = f"{type(e).__name__} {url} (after {time.time() - t0:.0f}s)"
            if attempt < attempts:
                self.retried += 1
                log.info("retry %d/%d %s", attempt, attempts - 1, last_err)
                self._sleep_backoff(attempt, retry_after)
        self.errors.append(last_err + f" [gave up after {attempts} attempts]")
        return None
