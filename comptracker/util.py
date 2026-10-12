import re, time, json, random, urllib.robotparser, urllib.parse, logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

LONDON = ZoneInfo("Europe/London")
TZ = LONDON                     # the country being collected (set_country); UK by default
from .countries import COUNTRIES
CUR = dict(COUNTRIES["uk"], cc="uk")

def set_country(cc):
    """Switch every date/money helper to country `cc` (timezone, currency, number format, language)."""
    global TZ
    CUR.clear(); CUR.update(COUNTRIES[cc], cc=cc)
    TZ = ZoneInfo(CUR["tz"])
UA = "Mozilla/5.0 (compatible; PersonalCompTracker/1.0; single-user personal use; hourly, polite; no logins)"
log = logging.getLogger("comp")

def now():
    return datetime.now(TZ)

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
        return datetime(int(m.group(3)), mon, int(m.group(1)), default_hour, default_min, tzinfo=TZ)
    except ValueError:
        return None

def infer_year(day, month, hour=23, minute=59):
    n = now()
    for y in (n.year, n.year + 1, n.year - 1):
        try:
            d = datetime(y, month, day, hour, minute, tzinfo=TZ)
        except ValueError:
            continue
        if y == n.year and d >= n - timedelta(days=45):
            return d
        if y == n.year + 1 and d > n:
            return d
    return None

def money(text):
    """first £ amount in text -> float, supports k/m suffix. (Other countries: first amount in local currency.)"""
    if text is None:
        return None
    if CUR["cc"] != "uk": return money_local(text)
    m = re.search(r"£\s?([\d,]+(?:\.\d+)?)\s?(k|m|million|bn)?(?![\w&])", text, re.I)   # "£100 M&S" is not £100m
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
    if CUR["cc"] != "uk": return value_local(text)
    t = text.replace("\u2011", "-")
    m = re.search(r"(?:worth|valued at|value of|value)\s*(?:over|up to|around|approx\.?)?\s*:?\s*£\s?([\d,]+(?:\.\d+)?)\s?(k|m|million)?(?![\w&])", t, re.I)
    cands = []
    if m:
        v = float(m.group(1).replace(",", "")); s = (m.group(2) or "").lower()
        if "," in m.group(1) and s == "k": s = ""   # "£111,222.33k" is already in pounds
        v *= {"k": 1e3, "m": 1e6, "million": 1e6}.get(s, 1)
        return v
    for m in re.finditer(r"£\s?([\d,]+(?:\.\d+)?)\s?(k|m|million)?(?![\w&])", t, re.I):
        pre = t[max(0, m.start() - 14):m.start()]
        if _BAD_CTX.search(pre): continue
        try: v = float(m.group(1).replace(",", ""))
        except ValueError: continue
        s = (m.group(2) or "").lower()
        if "," in m.group(1) and s == "k": s = ""
        v *= {"k": 1e3, "m": 1e6, "million": 1e6}.get(s, 1)
        cands.append(v)
    return max(cands) if cands else None

# ---------------------------------------------------------------- closed / closing-date helpers
_CLOSED_TITLE = re.compile(r"^\W{0,4}(?:(?:competition|giveaway|draw|entries|entry|promotion)\s+|now\s+)?(?:closed|ended|expired)\b(?!\s+(?:loop|circuit|captioning|door))", re.I)
_CLOSED_ANY = re.compile(r"\b(?:this\s+)?(?:competition|giveaway|draw|promotion)\s+(?:is\s+|has\s+)?(?:now\s+)?(?:closed|ended)\b", re.I)

def is_closed_title(title):
    """'CLOSED: Win tickets…', 'Competition closed – …', 'ENDED …' -> True. Titles only; never guesses from dates."""
    t = (title or "").strip()
    return bool(_CLOSED_TITLE.search(t) or _CLOSED_ANY.search(t[:140]))

_MON = "jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
_DOW = r"(?:(?:mon|tues?|wed(?:nes)?|thu(?:rs?)?|fri|sat(?:ur)?|sun)[a-z]*\.?,?\s+)?"
_DATE = _DOW + r"(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(" + _MON + r")\.?,?\s+(20\d\d)"
_GAP = r"(?:(?!\.\s+[A-Z])[^;]){0,50}?"
_CLOSE_RX = re.compile(r"\bclos(?:e|es|ed|ing)\b" + _GAP + r"(?:\bon\b|\bis\b|\bby\b|:|\buntil\b|\bat\b|\bdate\b|\s)\s*" + _DATE, re.I)
_NUM_CLOSE_RX = re.compile(r"\bclos(?:e|es|ing)\b" + _GAP + r"(\d{1,2})/(\d{1,2})/(20\d\d)", re.I)
_RANGE_RX = re.compile(r"(?:start date|end date|competition period|runs?|running|run from)" + r"(?:(?!\.\s+[A-Z])[^;]){0,160}?\bfrom\b" + r"(?:(?!\.\s+[A-Z])[^;]){0,40}?\s(?:to|until|till|-|–)\s+" + _DATE, re.I)
_TIME_RX = re.compile(r"(?<![\d/])(\d{1,2})[.:](\d{2})\s*(am|pm)?(?!\d)|\b(midday|noon)\b", re.I)

def _mk(d, mon, y):
    mi = MONTHS.get(mon[:3].lower())
    try: return datetime(int(y), mi, int(d), 23, 59, tzinfo=TZ) if mi else None
    except ValueError: return None

def closing_from_text(text):
    """Conservative closing-date extraction from a promoter's terms / page text.
    Returns (aware datetime, precision 'date'|'exact') or None. Only explicit 'closes … <day month year>' style statements
    (or a 'from X to <date with year>' competition period) count; nothing is ever inferred or guessed."""
    if not text: return None
    if CUR["lang"] != "en":
        return closing_local(text)
    t = re.sub(r"\s+", " ", text.replace("\u00a0", " ").replace("\ufe0f", ""))
    cands = []
    for m in _CLOSE_RX.finditer(t):
        dt = _mk(m.group(1), m.group(2), m.group(3))
        if not dt: continue
        seg = t[m.start():m.end()]
        tm = None
        for x in _TIME_RX.finditer(seg):
            tm = x
        if tm:
            if tm.group(4): h, mi = 12, 0
            else:
                h, mi = int(tm.group(1)), int(tm.group(2))
                if tm.group(3): h = h % 12 + (12 if tm.group(3).lower() == "pm" else 0)
            if 0 <= h < 24 and 0 <= mi < 60: dt = dt.replace(hour=h, minute=mi); cands.append((dt, "exact")); continue
        cands.append((dt, "date"))
    for m in _NUM_CLOSE_RX.finditer(t):
        try: cands.append((datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), 23, 59, tzinfo=TZ), "date"))
        except ValueError: pass
    if not cands:
        for m in _RANGE_RX.finditer(t):
            dt = _mk(m.group(1), m.group(2), m.group(3))
            if dt: cands.append((dt, "date"))
    if not cands: return None
    return max(cands, key=lambda c: c[0])

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
        self.s.headers.update({"User-Agent": UA, "Accept-Language": CUR.get("accept_language") or "en-GB,en;q=0.8"})
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
                if sc == 202 and waf:      # a WAF bot-challenge never resolves by waiting; one re-check at most, and we do not try to solve it
                    attempts = min(attempts, attempt + 1)
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


# ---------------------------------------------------------------- other countries: money in local currency, local-language dates
_NUM = r"(\d{1,3}(?:[.,\s\u202f\u00a0'](?=\d{3}(?!\d))\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
_SUF = r"(?:\s?(k|mio\.?|millionen|millions?|milioni|miljoen|mln|m)(?![\w&]))?"
_SYM_PRE = {"EUR": r"(?:€|EUR\s)", "AUD": r"(?:AU?\$|A\$|\$)", "NZD": r"(?:NZ\$|\$)", "GBP": r"£"}
_SYM_POST = {"EUR": r"(?:€|euros?\b|eur\b)", "AUD": r"(?:AUD\b|dollars?\b)", "NZD": r"(?:NZD\b|dollars?\b)", "GBP": r"(?:pounds?\b)"}

def _amount(num, suf):
    n = num.replace("\u202f", " ").replace("\u00a0", " ")
    if CUR.get("decimal_comma"):
        n = re.sub(r"[.\s']", "", n) if re.search(r"[.\s']\d{3}(?!\d)", n) else n
        n = n.replace(",", ".")
    else:
        n = re.sub(r"[,\s']", "", n)
    try: v = float(n)
    except ValueError: return None
    s = (suf or "").lower().rstrip(".")
    if s == "k": v *= 1e3
    elif s in ("m", "mio", "millionen", "million", "millions", "milioni", "miljoen", "mln"): v *= 1e6
    return v

def _money_iter(t):
    c = CUR["currency"]
    rx = re.compile(_SYM_PRE[c] + r"\s?" + _NUM + _SUF + r"(?![\w&])|" + _NUM + _SUF + r"\s?" + _SYM_POST[c], re.I)
    for m in rx.finditer(t):
        if m.group(1) is not None: v = _amount(m.group(1), m.group(2))
        else: v = _amount(m.group(3), m.group(4))
        if v is not None: yield m, v

def money_local(text):
    for m, v in _money_iter(text or ""):
        return v
    return None

_VAL_KW = re.compile(r"(?:worth|valued at|value of|value|im wert von|wert von|gesamtwert|warenwert|wert|d'une valeur (?:totale )?de|valeur|ter waarde van|t\.?w\.?v\.?|del valore (?:complessivo )?di|valore(?: di)?|dal valore di)\s*(?:over|up to|around|approx\.?|je|jeweils|de|di|ca\.?|circa|bis zu|jusqu'à|tot|von)?\s*:?\s*$", re.I)
_BAD_LOCAL = re.compile(r"(spend|spent|from|for just|for only|just|only|entry|ticket|per|each|deposit|bonus|extra|off|ab|für nur|nur|pro|einkaufswert|mindestbestellwert|rabatt|dès|pour|par|réduction|remise|à partir de|vanaf|voor|korting|da|sconto|spesa|acquisto|minimo)\s*$", re.I)

def value_local(text):
    """Stated prize value in local currency ('im Wert von 5.000 €', 'd'une valeur de 3 000 €', 't.w.v. €150', '$2,500')."""
    if not text: return None
    t = text.replace("\u2011", "-")
    best = None; cands = []
    for m, v in _money_iter(t):
        pre = t[max(0, m.start() - 28):m.start()]
        if _VAL_KW.search(pre):
            best = v if best is None else max(best, v); continue
        if _BAD_LOCAL.search(pre[-16:]): continue
        cands.append(v)
    if best is not None: return best
    return max(cands) if cands else None

MONTHS_LOCAL = {
    "de": ["januar", "februar", "märz", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "dezember"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    "nl": ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"],
    "it": ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
}
_ALT_MON = {"märz": ["maerz", "marz"], "février": ["fevrier"], "août": ["aout"], "décembre": ["decembre"], "jänner": []}
_CLOSE_KW = {
    "de": r"(?:einsendeschluss|teilnahmeschluss|teilnahmezeitraum|aktionszeitraum|enddatum|endet|läuft|laufzeit|gültig|teilnahme (?:ist )?(?:bis|möglich bis)|bis zum|bis einschließlich|bis spätestens|bis)",
    "fr": r"(?:jusqu'au|jusqu’au|se termine|termine le|fin le|fin du jeu|date limite|clôture|clos le|prend fin|avant le|au plus tard le|valable jusqu)",
    "nl": r"(?:t/m|tot en met|tot uiterlijk|uiterlijk|sluit|sluitingsdatum|einddatum|eindigt|loopt tot|deadline|tot)",
    "it": r"(?:fino al|fino alle ore \d{1,2}[.:]\d{2} del|entro il|entro e non oltre il|scadenza|scade il|termina il|si conclude il|valido fino al|dal \d{1,2}[^\d]{1,20}al)",
}

def _local_date_rx(lang):
    names = []
    for i, n in enumerate(MONTHS_LOCAL[lang], 1):
        names.append(n); names += _ALT_MON.get(n, [])
    mon = "|".join(sorted(set(names), key=len, reverse=True))
    return (r"(\d{1,2})(?:\.|er|°|º)?\s*(" + mon + r")\.?\s+(20\d\d)", r"(\d{1,2})[./-](\d{1,2})[./-](20\d\d|\d\d)(?!\d)")

def _mon_index(lang, name):
    name = name.lower()
    for i, n in enumerate(MONTHS_LOCAL[lang], 1):
        if name == n or name in _ALT_MON.get(n, []): return i
    return None

def closing_local(text):
    """Conservative closing date from local-language text: only dates that follow a closing keyword
    ('Einsendeschluss: 31.10.2026', 'jusqu'au 31 octobre 2026', 't/m 31 oktober 2026', 'fino al 31 ottobre 2026').
    Returns (aware datetime, 'date'|'exact') or None. Never infers a year."""
    if not text: return None
    lang = CUR["lang"]
    if lang not in _CLOSE_KW: return None
    t = re.sub(r"\s+", " ", text.replace("\u00a0", " "))
    named, numeric = _local_date_rx(lang)
    rx = re.compile(_CLOSE_KW[lang] + r"[^.;\n]{0,45}?(?:" + named + "|" + numeric + ")", re.I)
    cands = []
    for m in rx.finditer(t):
        try:
            if m.group(1):
                mi = _mon_index(lang, m.group(2)); d = int(m.group(1)); y = int(m.group(3))
            else:
                d, mi, y = int(m.group(4)), int(m.group(5)), int(m.group(6))
                if y < 100: y += 2000
            dt = datetime(y, mi, d, 23, 59, tzinfo=TZ)
        except (TypeError, ValueError):
            continue
        seg = t[m.end():m.end() + 22]
        tm = re.match(r"\s*(?:,|um|à|alle|om|ore|h)?\s*(?:ore\s*)?(\d{1,2})[:.h](\d{2})", seg, re.I)
        if tm and int(tm.group(1)) < 24 and int(tm.group(2)) < 60:
            cands.append((dt.replace(hour=int(tm.group(1)), minute=int(tm.group(2))), "exact"))
        else:
            cands.append((dt, "date"))
    rng = {"fr": (r"\bdu", r"(?:au|jusqu'au)"), "it": (r"\bdal", r"(?:al|fino al)"), "de": (r"\bvom", r"(?:bis(?: zum| einschließlich)?|-|–)"),
           "nl": (r"\bvan", r"(?:t/m|tot en met|tot|-|–)")}[lang]
    rrx = re.compile(rng[0] + r"\s+(?:le\s+|il\s+)?\d{1,2}(?:[./-]\d{1,2}(?:[./-](?:20)?\d\d)?|\.?\s*[a-zéûäöüà]+(?:\s+20\d\d)?)\s+" + rng[1] + r"\s+(?:le\s+|il\s+)?(?:" + named + "|" + numeric + ")", re.I)
    for m in rrx.finditer(t):
        try:
            if m.group(1): dt = datetime(int(m.group(3)), _mon_index(lang, m.group(2)), int(m.group(1)), 23, 59, tzinfo=TZ)
            else:
                y = int(m.group(6)); y = y + 2000 if y < 100 else y
                dt = datetime(y, int(m.group(5)), int(m.group(4)), 23, 59, tzinfo=TZ)
            cands.append((dt, "date"))
        except (TypeError, ValueError):
            continue
    if not cands: return None
    return max(cands, key=lambda c: c[0])

def dmy(text, default_hour=23, default_min=59):
    """'31.10.2026' / '31/10/2026' / '2026-10-31' -> aware datetime in the current country's timezone (end of day)."""
    if not text: return None
    m = re.search(r"(20\d\d)-(\d{1,2})-(\d{1,2})", text)
    try:
        if m: return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), default_hour, default_min, tzinfo=TZ)
        m = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](20\d\d)", text)
        if m: return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), default_hour, default_min, tzinfo=TZ)
    except ValueError:
        return None
    return None

def local_named_date(text):
    """'31 octobre 2026' / '12 Ottobre 2026' (any position) -> aware datetime, end of day."""
    lang = CUR["lang"]
    if lang not in MONTHS_LOCAL: return parse_date(text)
    named, _ = _local_date_rx(lang)
    m = re.search(named, text or "", re.I)
    if not m: return None
    try: return datetime(int(m.group(3)), _mon_index(lang, m.group(2)), int(m.group(1)), 23, 59, tzinfo=TZ)
    except (TypeError, ValueError): return None
