"""Direct promoter links. Aggregator/listing-site items are resolved to the promoter's own competition page:
detail page -> its 'Enter'/'Visit' button -> (if it is the listing site's own redirect, and robots.txt allows it) follow the
redirect, including a meta-refresh / JS location hop. Tracking/affiliate parameters are stripped. Results are cached in the
state DB (resolved: kept; unresolved: retried after a week), and a per-run budget spreads first-time resolution over several runs.
Never logs in, never submits anything, never fetches a URL robots.txt disallows."""
import re, json, time, logging, urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
from . import safety
from .util import now

log = logging.getLogger("resolve")
TRACK = re.compile(r"^(utm_[a-z]+|fbclid|gclid|gbraid|wbraid|dclid|msclkid|mc_cid|mc_eid|_hsenc|_hsmi|igshid|awc|clickref|irclickid|"
                   r"cjevent|ranmid|raneaid|ransiteid|aff_?id|affiliate|aff|tag|ref_src|src_page|src_pos|sms_ss|at_medium|at_campaign|"
                   r"ito|cmpid|_ga|_gl|trk|tracking)$", re.I)
ENTER = re.compile(r"(enter|visit|view competition|go to|click here|teilnehm|zum gewinnspiel|zur aktion|mitmachen|particip|jouer|je joue|"
                   r"doe mee|meedoen|naar de (?:actie|winactie|site)|deelnemen|partecipa|vai al|sito (?:dedicato|ufficiale)|collegati al sito|"
                   r"competition website|enter now|official (?:site|page))", re.I)
SOCIAL_SHARE = re.compile(r"(sharer|share\?|/share|intent/tweet|pin/create|wa\.me|whatsapp:|mailto:|addtoany|sharethis|t\.me/share)", re.I)
NOT_PROMO = re.compile(r"(begambleaware|gambleaware|gamstop|betblocker|xenforo|w3\.org|schema\.org|ico\.org\.uk|cloudflare|googletagmanager|"
                       r"doubleclick|apple\.com/app|play\.google)", re.I)
LEADGEN = ("sierkje.nl", "dt51.net", "tradetracker", "daisycon", "awin1.com", "ds1.nl", "prf.hn")
MORE_SHORT = SHORTENERS = tuple(safety.SHORTENERS) + ("lnkd.in", "buff.ly", "bitly.com", "rebrand.ly", "linktr.ee", "s.id", "amzn.to")
RETRY_DAYS = 7

def clean_url(u):
    try:
        p = urllib.parse.urlsplit(u)
        q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
             if not TRACK.match(k) and not (k.lower() in ("ref", "source", "src", "via", "partner") and re.search(r"(prize|comp|concours|gewinn|winact|prijs|loquax|tpf|ozbargain|cheapies)", v, re.I))]
        return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), p.fragment if not re.match(r"^(utm|xtor)", p.fragment) else ""))
    except Exception:
        return u

def good_final(u, src_host):
    d = safety.domain(u)
    return bool(d) and u.startswith("http") and d != src_host and not safety.is_aggregator_domain(d) and d not in MORE_SHORT and not NOT_PROMO.search(u)

def _js_hop(text, base):
    m = re.search(r'http-equiv=["\']?refresh["\']?[^>]*?url=\s*["\']?([^"\'>\s]+)', text[:20000], re.I) or \
        re.search(r'(?:window\.|document\.)?location(?:\.href)?\s*=\s*["\'](https?://[^"\']+)', text[:20000]) or \
        re.search(r'location\.replace\(\s*["\'](https?://[^"\']+)', text[:20000])
    return urllib.parse.urljoin(base, m.group(1)) if m else None

def candidates(html, url):
    """Ordered outbound-link candidates from a listing site's detail page."""
    s = BeautifulSoup(html, "lxml"); host = safety.domain(url)
    b = s.find("base", href=True); base = urllib.parse.urljoin(url, b["href"]) if b else url
    out = []
    for m in re.finditer(r'competitionUrl&quot;:\[0,&quot;(https?://.+?)&quot;', html):    # competitions.ie (Astro island props)
        out.append((0, m.group(1).replace("&amp;", "&")))
    for i, a in enumerate(s.find_all("a", href=True)):
        h = a["href"].strip()
        if not h or h.startswith(("#", "javascript:", "mailto:", "tel:")) or SOCIAL_SHARE.search(h): continue
        chrome = a.find_parent(["nav", "footer", "header"])
        if chrome is not None and (chrome.find_parent("article") is None or not ENTER.search(a.get_text(" "))): continue
        h = urllib.parse.urljoin(base, h); d = safety.domain(h)
        t = " ".join(a.get_text(" ").split())[:80]; cls = " ".join(a.get("class") or []); rel = " ".join(a.get("rel") or [])
        same = d == host
        enter = bool(ENTER.search(t)) or bool(re.search(r"(enter|cta|gbut|participate)", cls, re.I))
        redirish = bool(re.search(r"/(go|out|redir|redirect|link|link-track|track|exit|visit|goto|click|maakkans|doemee|concours/\d+)[/.?]?", urllib.parse.urlsplit(h).path + "?", re.I)) or "track.php" in h
        if same and not (enter and redirish): continue
        if not same and NOT_PROMO.search(h): continue
        score = (0 if enter else 2) + (0 if "ugc" in rel or "nofollow" in rel or "btn" in cls or "button" in cls else 1) + i / 10000
        if not same and not enter and "ugc" not in rel: score += 3      # random external links in the text: weak
        out.append((score, h))
    slug = urllib.parse.urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1].split(".")[0]
    if len(slug) > 8:     # a redirect link carrying this listing's own slug beats every other button (ads for other offers)
        out = [(-1 if slug in h else sc, h) for sc, h in out]
        if any(sc < 0 for sc, _ in out): out = [(sc, h) for sc, h in out if sc < 0]
    out.sort(key=lambda x: x[0])
    seen = []; [seen.append(h) for _, h in out if h not in seen]
    return seen[:4]

def follow(fetcher, u, src_host, hops=6):
    """Follow a listing site's redirect chain hop by hop (each hop robots-checked); stop as soon as the target is a promoter
    URL, so the promoter's page itself is not fetched."""
    for _ in range(hops):
        if good_final(u, src_host): return u, None
        if any(x in safety.domain(u) for x in LEADGEN):
            return None, "redirects through an affiliate/lead-generation network, not a promoter page"
        if not fetcher.allowed(u): return None, "robots.txt disallows the site's redirect link"
        res = fetcher.peek(u)
        if res is None: return None, "redirect fetch failed"
        sc, loc, r = res
        if 300 <= sc < 400 and loc:
            u = urllib.parse.urljoin(u, loc); continue
        if sc != 200: return None, (f"redirect returned HTTP {sc}" if sc in (403, 404, 410) else "redirect fetch failed")
        nxt = _js_hop(r.text or "", r.url)
        if not nxt: return None, "redirect did not lead to a promoter page"
        u = nxt
    return (u, None) if good_final(u, src_host) else (None, "too many hops")

def resolve_one(ctx, listing_url, html=None):
    """Return (direct_url or None, reason)."""
    host = safety.domain(listing_url)
    if html is None:
        if not ctx.f.allowed(listing_url): return None, "robots.txt disallows the listing page"
        r = ctx.get(listing_url, retries=1)
        if r is None:
            last = " ".join(ctx.errors[-2:])
            m = re.search(r"HTTP (4\d\d)", last)
            return None, (f"listing page returned HTTP {m.group(1)} (login/blocked)" if m else "listing page fetch failed")
        html = r.text
    if len(html or "") < 2500: return None, "listing page blocked by a bot check"
    why = "no enter/visit link on the listing page"
    for c in candidates(html, listing_url):
        u, why2 = follow(ctx.f, c, host)
        if u: return clean_url(u), "ok"
        why = why2 or why
    return None, why

# sources whose listing links can never be resolved without breaking robots.txt or logging in
UNRESOLVABLE = {
    "Competitions Time": "promoter link is only behind /redir/ (robots.txt disallows)",
    "Competitions Today": "promoter link is only behind /go.php (robots.txt disallows)",
    "GewinnHai": "promoter link is only behind /go/ (robots.txt disallows)",
    "Competitions.com.au": "promoter link is behind a sign-up wall (/register) - not used",
    "Competitions.co.nz": "promoter link is behind a sign-up wall (/register) - not used",
    "Competition Showroom": "JS-only prize pages; operator link not in the public HTML",
}
# operator pages scraped via Showroom: the operator's own site is the direct link
OPERATOR_HOME = {"BOTB (via Showroom)": "https://www.botb.com/", "7days Performance (via Showroom)": "https://www.7daysperformance.co.uk/"}

BIG = {"ThePrizeFinder": 3.0, "FindCompetitions": 1.5}     # large backlogs get a bigger share of the run (multiplier)

def apply(ctx, source, items, budget_s=180, max_new=150):
    """Set it['link'] to the promoter URL where possible; it['listing_link'] keeps the listing page; it['direct'] flag."""
    budget_s *= BIG.get(source, 1); max_new = int(max_new * BIG.get(source, 1)); ctx.deadline = time.time() + budget_s + 30
    t_end = time.time() + budget_s; new = 0; stats = dict(direct=0, resolved=0, unresolved=0, pending=0)
    for it in items:
        link = it.get("link") or ""
        if it.get("listing_link"): link = it["listing_link"]
        d = safety.domain(link)
        if not safety.is_aggregator_domain(d):
            it["link"] = clean_url(link); it["direct"] = bool(link); stats["direct"] += 1; continue
        it["listing_link"] = link
        if source in OPERATOR_HOME:
            it["link"] = OPERATOR_HOME[source]; it["direct"] = True; stats["resolved"] += 1; continue
        hint = it.pop("direct_hint", None)       # a source may already know the promoter URL (from its own page)
        if hint and good_final(hint, d):
            it["link"] = clean_url(hint); it["direct"] = True; stats["resolved"] += 1; continue
        rhint = it.pop("redirect_hint", None)   # ... or the listing site's own 'enter' redirect link (saves fetching the detail page)
        key = "resolve:" + link
        c = ctx.cache_get(key)
        if c and (c.get("url") or (now() - datetime.fromisoformat(c["at"])).days < RETRY_DAYS):
            if c.get("url"): it["link"] = c["url"]; it["direct"] = True; stats["resolved"] += 1
            else: it["direct"] = False; it["unresolved_why"] = c.get("why", ""); stats["unresolved"] += 1
            continue
        if source in UNRESOLVABLE:
            it["direct"] = False; it["unresolved_why"] = UNRESOLVABLE[source]; stats["unresolved"] += 1; continue
        if time.time() > t_end or new >= max_new:
            it["direct"] = False; it["unresolved_why"] = "not resolved yet (queued for the next run)"; stats["pending"] += 1; continue
        new += 1
        try:
            if rhint:
                u, why = follow(ctx.f, rhint, d)
                u, why = (clean_url(u), "ok") if u else resolve_one(ctx, link)
            else:
                u, why = resolve_one(ctx, link)
        except Exception as e:
            u, why = None, f"{type(e).__name__}"
        if u is None and why in ("listing page fetch failed", "redirect fetch failed"):
            it["direct"] = False; it["unresolved_why"] = "not resolved yet (fetch failed, will retry)"; stats["pending"] += 1; continue
        ctx.cache_put(key, dict(url=u or "", why=why, at=now().isoformat(timespec="seconds")))
        if u: it["link"] = u; it["direct"] = True; stats["resolved"] += 1
        else: it["direct"] = False; it["unresolved_why"] = why; stats["unresolved"] += 1
    return stats
