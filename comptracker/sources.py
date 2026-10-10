"""Pluggable per-source collectors. Add a new source by writing a function decorated with @source(...)
returning a list of dicts (see FIELDS in collector.py). Each gets a Ctx (polite fetcher + cache)."""
import re, json, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from .util import (LONDON, now, parse_date, infer_year, money, pence_or_pounds, prize_value_from_text, log, closing_from_text, is_closed_title)

REGISTRY = {}

# Sources deliberately NOT collected (shown on the page's status table so nobody assumes they are covered).
EXCLUDED = {
    "Radio: talkSPORT": "talkSPORT's robots.txt disallows automated access to its competitions pages, so it is not collected. (Its competitions are not listed here.)",
}

def source(name, kind, url, note="", direct=False):
    def deco(fn):
        REGISTRY[name] = dict(fn=fn, kind=kind, url=url, note=note, direct=direct, name=name)
        return fn
    return deco

def soup(r):
    return BeautifulSoup(r.text, "lxml")

def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()

def rec(**kw):
    d = dict(title="", promoter="", link="", prize_desc="", prize_value=None, entry_type="", entry_cost=None,
             entry_cost_text="", closes_at=None, closes_precision="", tickets_sold=None, tickets_total=None,
             pct_sold=None, entry_note="", skey="", station="", tags=None, image="")
    d.update(kw)
    if not d["skey"]:
        d["skey"] = d["link"] or d["title"]
    return d

_IMG_JUNK = re.compile(r"(logo|(?<![a-z])icons?(?![a-z])|gware|gambleaware|new620c|spacer|1x1|placeholder|avatar|sprite|\.svg(?:$|\?)|\.gif(?:$|\?))", re.I)

def img_url(node, base="", want=480):
    """Best prize-picture URL inside `node` (or `node` itself if it is an <img>): picks the srcset candidate closest
    to `want` px wide, resolves relative URLs, unwraps image-proxy wrappers, skips logos/icons/gifs. '' if none."""
    if node is None: return ""
    imgs = [node] if getattr(node, "name", "") == "img" else node.select("img")
    for i in imgs:
        best = ""
        srcset = i.get("srcset") or i.get("data-srcset") or ""
        cands = []
        for u, w in re.findall(r"(\S+)\s+(\d+)w\b", srcset):   # URLs may contain commas (Cloudflare resizing)
            cands.append((int(w), u.lstrip(",")))
        if cands:
            big = [c for c in cands if c[0] >= want]
            best = (min(big) if big else max(cands))[1]
        best = best or i.get("data-src") or i.get("data-lazy-src") or i.get("src") or ""
        best = best.strip()
        if not best or best.startswith("data:"): continue
        if base and not best.startswith("http"):
            best = urllib.parse.urljoin(base, best)
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(best).query)
        if "/api/image-proxy" in best and q.get("url"):   # Showroom wraps operator images; link the original
            best = q["url"][0]
        if _IMG_JUNK.search(urllib.parse.urlsplit(best).path) or _IMG_JUNK.search(i.get("class") and " ".join(i["class"]) or ""):
            continue
        if best.startswith("http://"): best = "https://" + best[7:]
        return best
    return ""

def og_image(s, base=""):
    m = s.select_one('meta[property="og:image"]')
    u = (m.get("content") or "").strip() if m else ""
    if u and base and not u.startswith("http"): u = urllib.parse.urljoin(base, u)
    return ("https://" + u[7:]) if u.startswith("http://") else u

def approx_from_left(text):
    """'2 Days' / '1 Day' / '10:49' / '7h left' -> approx datetime"""
    t = clean(text).lower()
    n = now()
    m = re.search(r"(\d+)\s*(?:days?|d)\b", t)
    if m: return n + timedelta(days=int(m.group(1)))
    m = re.search(r"(\d+):(\d{2})(?::(\d{2}))?", t)
    if m: return n + timedelta(hours=int(m.group(1)), minutes=int(m.group(2)))
    m = re.search(r"(\d+)\s*(?:hours?|hrs?|h)\b", t)
    if m: return n + timedelta(hours=int(m.group(1)))
    m = re.search(r"(\d+)\s*(?:mins?|minutes?|m)\b", t)
    if m: return n + timedelta(minutes=int(m.group(1)))
    return None


def detail_closing(ctx, urls, cap, recheck_hours=72):
    """Closing dates from the competition's own page text (terms / 'closing date for entries is…'), via the cached fetch.
    Only explicit statements are used (util.closing_from_text); pages that state no date are re-checked every `recheck_hours`.
    Fetches at most `cap` pages per run (uncached first). Returns {url: (datetime, precision)} for pages with a stated date."""
    found = {}; todo = []
    for u in urls:
        c = ctx.cache_get(u)
        if c and c.get("closes"):
            found[u] = (datetime.fromisoformat(c["closes"]), c.get("prec") or "date"); continue
        age = ctx.cache_age_hours(u)
        if c is None or age is None or age >= recheck_hours: todo.append((0 if c is None else 1, u))
    todo.sort(); fetched = 0
    for _, u in todo:
        if fetched >= cap: break
        r = ctx.get(u); fetched += 1
        if not r: continue
        ss = soup(r)
        for x in ss(["script", "style", "noscript"]): x.decompose()
        res = closing_from_text(clean(ss.get_text(" ")))
        ctx.cache_put(u, {"closes": res[0].isoformat() if res else None, "prec": res[1] if res else "", "v": 2})
        if res: found[u] = res
    ctx.meta["detail_dates"] = ctx.meta.get("detail_dates", 0) + len(found)
    return found

# ---------------------------------------------------------------- Loquax
LOQ = "https://www.loquax.co.uk"

def _loquax_list(ctx, path):
    r = ctx.get(LOQ + path)
    if not r: return []
    s = soup(r); out = []
    for div in s.select("div.compList"):
        a = div.select_one(".structItem-title a")
        if not a: continue
        title = clean(a.get_text())
        info = clean((div.select_one(".smallcompfont") or div).get_text(" "))
        closes = parse_date(info)
        prec = "date"
        if closes:
            if "estimated" in info.lower(): prec = "approx"
            m = re.search(r"ends?\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)", title, re.I)
            if m:
                h = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "pm" else 0)
                closes = closes.replace(hour=h, minute=int(m.group(2) or 0)); prec = "exact"
        img = div.select_one(".structItem-iconContainer img")
        method = clean(img.get("alt", "")) if img else ""
        free = bool(re.search(r"free entry", title, re.I))
        note = "Listed on Loquax (guest view; free Loquax login needed to see the promoter's direct link)."
        if method: note += f" Entry type icon: {method}."
        if "enter asap" in info.lower(): note += " Loquax flags: enter ASAP."
        out.append(rec(title=re.sub(r"\s*\((?:[^)]*(?:free entry|ends \d)[^)]*)\)\s*$", "", title, flags=re.I).strip() or title,
                       link=LOQ + a["href"], closes_at=closes, closes_precision=prec if closes else "",
                       entry_type="free" if free else "", entry_note=note, prize_desc=title))
    return out

@source("Loquax", "aggregator", LOQ + "/competitions/", "Guest view only shows a handful per page; direct promoter links need free login (not used).")
def loquax(ctx):
    out = []
    for p in ["/competitions/newtoday.php", "/competitions/closingsoon.php", "/competitions/dailies.php"]:
        out += _loquax_list(ctx, p)
    return out

@source("Loquax Win-a-House", "aggregator", LOQ + "/win-a-house.php", "Public list of paid house/cash prize draws with ticket price and value.")
def loquax_houses(ctx):
    r = ctx.get(LOQ + "/win-a-house.php")
    if not r: return []
    s = soup(r); out = []
    for div in s.select("div.houseList"):
        a = div.select_one("a.headlineLink")
        if not a: continue
        title = clean(a.get_text())
        lis = [clean(x.get_text(" ")) for x in div.select("li.smallhousefont")]
        closes = cost = value = None; guaranteed = False
        for l in lis:
            if l.lower().startswith("closes"): closes = parse_date(l)
            elif l.lower().startswith("cost"): cost = money(l); costtxt = l.split(":", 1)[-1].strip()
            elif l.lower().startswith("value"): value = money(l)
            elif "guaranteed" in l.lower(): guaranteed = True
        desc = clean((div.select_one("p:not(.gambleAware)") or div.find_all("p")[-1]).get_text()) if div.find_all("p") else ""
        hi = div.select_one(".houseImageCell img")
        bg = re.search(r"url\(['\"]?([^'\")]+)", (hi.get("style") or "") if hi else "")
        image = urllib.parse.urljoin(LOQ + "/", bg.group(1)) if bg else img_url(hi, LOQ + "/")
        m = re.match(r"([A-Z][\w' &.\-]+?) (?:are|is) (?:giving|offering|running|launching)", desc)
        note = "Paid ticket draw; Loquax says all have a free (usually postal) entry route unless indicated."
        if guaranteed: note += " Operator guarantees a house winner."
        out.append(rec(title=title, promoter=m.group(1) if m else "", link=LOQ + a["href"], prize_desc=desc[:400],
                       prize_value=value, entry_type="paid", entry_cost=cost, entry_cost_text=(f"£{cost:g}" if cost is not None else ""),
                       closes_at=closes, closes_precision="date" if closes else "", entry_note=note, image=image))
    return out

# ---------------------------------------------------------------- ThePrizeFinder (official RSS feeds + detail pages)
TPF = "https://www.theprizefinder.com"

@source("ThePrizeFinder", "aggregator", TPF, "Uses its published RSS feeds + public competition pages (details cached; a capped number fetched per run).")
def prizefinder(ctx):
    items = {}; fresh_links = set()
    for feed in ["closing-soon", "top-prizes", "new-competitions"]:
        r = ctx.get(f"{TPF}/feed/{feed}")
        if not r: continue
        try:
            root = ET.fromstring(r.content)
        except ET.ParseError:
            ctx.errors.append("TPF rss parse " + feed); continue
        for it in root.iter("item"):
            link = (it.findtext("link") or "").strip()
            title = clean(it.findtext("title"))
            if link and link not in items:
                items[link] = title
            if link and feed == "new-competitions": fresh_links.add(link)
    out = []
    # uncached pages first; then pages cached by an older parser that found no date (the date format "(ends YYYY-MM-DD)" was missed)
    todo = [l for l in items if not ctx.cache_get(l)] + [l for l in items if ctx.cache_get(l) and not ctx.cache_get(l).get("closing") and ctx.cache_get(l).get("v", 1) < 2]
    cap = ctx.cap("tpf", 110)
    fetched = 0
    for l in todo:
        if fetched >= cap: break
        r = ctx.get(l)
        fetched += 1
        if not r: continue
        s = soup(r)
        text = s.get_text("|", strip=True)
        data = {}
        m = re.search(r"Website Name\|([^|]*)\|", text); data["site"] = m.group(1) if m else ""
        # "Closing Date:|2026-10-30" or "Closing Date:|Daily Entry (ends 2026-10-30)"
        m = re.search(r"Closing Date:\|[^|]*?(\d{4}-\d{2}-\d{2})", text); data["closing"] = m.group(1) if m else ""
        data["v"] = 2
        m = re.search(r"Instructions\|([^|]*)\|", text); data["instr"] = m.group(1) if m else ""
        m = re.search(r"Restriction\|([^|]*)\|", text); data["restr"] = m.group(1) if m else ""
        ctx.cache_put(l, data)
    for l, title in items.items():
        d = ctx.cache_get(l)
        if not d: continue
        closes = None
        if d.get("closing"):
            y, mo, da = map(int, d["closing"].split("-"))
            closes = datetime(y, mo, da, 23, 59, tzinfo=LONDON)
        site = d.get("site", "")
        site_clean = re.sub(r"\((?:TW|FB|IG|TT|YT|BL|FBK)\)", "", site).strip()
        instr = d.get("instr", ""); restr = d.get("restr", "")
        paid = bool(re.search(r"purchase|buy|spend|pay\b|subscription", instr + " " + restr, re.I))
        note = "; ".join(x for x in [instr and "Entry: " + instr, restr and "Restriction: " + restr] if x)
        # items that are only in the closing-soon / top-prizes feeds were listed before we looked: don't flag them NEW
        out.append(rec(title=re.sub(r"^Win ", "Win ", title), promoter=site_clean, link=l, prize_desc=title, backfill=l not in fresh_links,
                       prize_value=prize_value_from_text(title), entry_type="paid" if paid else "free",
                       closes_at=closes, closes_precision="date" if closes else "",
                       entry_note=note or "Listed on ThePrizeFinder (free to enter unless the page says otherwise)."))
    ctx.meta["tpf_feed_items"] = len(items); ctx.meta["tpf_details_cached"] = len([1 for l in items if ctx.cache_get(l)])
    return out

# ---------------------------------------------------------------- Competition Showroom
CSR = "https://www.competitionshowroom.com"

def _csr_cards(ctx, path, free_page=False):
    r = ctx.get(CSR + path)
    if not r: return []
    s = soup(r); out = []
    for art in s.select("article"):
        t = art.select_one('[class$="cardTitle"]')
        if not t: continue
        title = clean(t.get("title") or t.get_text())
        op = art.select_one('span[class$="__cardOp"]')
        op = clean(op.get_text()) if op else ""
        tm = art.select_one('[class*="cardTimerInline"]')
        left = clean(tm.get_text()) if tm else ""
        a = art.select_one("a[href*='prizeId']")
        link = CSR + a["href"] if a else ""
        sold = art.select_one('[class$="soldRow"] strong')
        ts = tt = None
        if sold:
            m = re.match(r"([\d,]+)\s*/\s*([\d,]+)", clean(sold.get_text()))
            if m: ts, tt = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
        pct = art.select_one('[class$="pctBadge"]')
        pctv = None
        if pct:
            m = re.search(r"(\d+)", pct.get_text()); pctv = float(m.group(1)) if m else None
        stats = {}
        for st in art.select('[class$="__stat"]'):
            l = st.select_one('[class$="statLbl"]'); v = st.select_one('[class$="statVal"]')
            if l and v: stats[clean(l.get_text()).lower()] = clean(v.get_text())
        price = stats.get("price", "")
        cash = stats.get("cash value", "")
        cat = art.select_one('[class$="cardCat"]'); cat = clean(cat.get_text()) if cat else ""
        isfree = price.upper() == "FREE"
        cost = 0.0 if isfree else money(price)
        closes = approx_from_left(left)
        note = "Free draw (no ticket needed)." if isfree else "Paid ticket draw; most operators also offer a free postal entry route (check their terms)."
        note += f" Showroom category: {cat}." if cat else ""
        out.append(rec(title=title, promoter=op, link=link, prize_desc=title, prize_value=money(cash) if cash and cash.lower() != "none" else None,
                       entry_type="free" if isfree else ("paid" if cost is not None else ""), entry_cost=cost,
                       entry_cost_text="FREE" if isfree else price, closes_at=closes, closes_precision="approx" if closes else "",
                       tickets_sold=ts, tickets_total=tt, pct_sold=pctv, entry_note=note, skey=link or title,
                       image=img_url(art, CSR + "/")))
    return out

@source("Competition Showroom", "aggregator", CSR + "/free-entry-competitions",
        "Server-rendered 'free entry' + 'best odds' pages (top ~26 per category); 'View draw' links point to Showroom (robots: not crawled).")
def showroom(ctx):
    out = []
    for p in ["/free-entry-competitions", "/best-odds-competitions", "/best-odds-car-competitions", "/best-odds-tech-competitions",
              "/best-odds-cash-competitions", "/best-odds-watch-competitions", "/best-odds-motorbike-competitions",
              "/best-odds-instant-win-competitions", "/best-odds-toy-competitions", "/best-odds-garden-competitions", "/best-odds-trade-competitions"]:
        out += _csr_cards(ctx, p)
    return out

def _csr_operator(ctx, slug, promoter):
    r = ctx.get(f"{CSR}/competitions/{slug}")
    if not r: return []
    s = soup(r); out = []
    for a in s.select("a[href*='prizeId']"):
        if "View" not in a.get_text(): continue
        box = a
        for _ in range(3):
            box = box.parent
            if len(box.find_all("a", href=re.compile("prizeId"))) > 1: box = box.find_all("a", href=re.compile("prizeId"))[0].parent; break
        # climb until we have the entry text
        node = a
        txt = ""
        for _ in range(4):
            node = node.parent
            txt = clean(node.get_text(" "))
            if "entry" in txt and len(node.find_all("a", href=re.compile("prizeId"))) == 1: break
        m = re.match(r"(.*?)\s*£\s?([\d.,]+)\s*entry", txt)
        if not m: continue
        title = clean(m.group(1)); title = re.sub(r"^(Win\s)?", "", title) and title
        cost = float(m.group(2).replace(",", ""))
        v = re.search(r"£\s?([\d,]+)\s*prize", txt)
        odds = re.search(r"1 in ([\d,]+)\s*max odds", txt)
        out.append(rec(title=title, promoter=promoter, link=CSR + a["href"], prize_desc=title,
                       prize_value=float(v.group(1).replace(",", "")) if v else None, entry_type="paid", entry_cost=cost,
                       entry_cost_text=f"£{cost:g}", tickets_total=int(odds.group(1).replace(",", "")) if odds else None,
                       entry_note="Paid draw (operator page is JS-rendered; data via Showroom operator page). Free postal route usually in operator T&Cs.",
                       skey=CSR + a["href"], image=img_url(node, CSR + "/")))
    return out

@source("BOTB (via Showroom)", "operator", "https://www.botb.com", "botb.com is JS-rendered (no public SSR list); using Showroom's BOTB operator page (top picks only, no closing dates).")
def botb(ctx):
    return _csr_operator(ctx, "botb", "BOTB")

@source("7days Performance (via Showroom)", "operator", "https://www.7daysperformance.co.uk", "7daysperformance.co.uk is a pure JS SPA (no public SSR list); using Showroom's operator page (top picks only).")
def sevendays(ctx):
    return _csr_operator(ctx, "7daysperformance", "7 Days Performance")

# ---------------------------------------------------------------- Dream Car Giveaways
DCG = "https://www.dreamcargiveaways.co.uk"

@source("Dream Car Giveaways", "operator", DCG + "/competitions", "Operator's own public listing (robots allow all).", direct=True)
def dcg(ctx):
    r = ctx.get(DCG + "/competitions")
    if not r: return []
    s = soup(r); out = []; seen = set()
    for a in s.select('a[href^="/competitions/"]'):
        h = a["href"]
        if h in seen or h.count("/") != 2 or h in ("/competitions/cars", "/competitions/cash", "/competitions/tech", "/competitions/watches",
                                                   "/competitions/instant-wins", "/competitions/experiences"): continue
        txt = clean(a.get_text("|"))
        parts = [p for p in txt.split("|") if p]
        if not any("% sold" in p for p in parts) and "sold" not in txt: continue
        seen.add(h)
        flat = clean(a.get_text(" "))
        m = re.search(r"Closes\s+(Today|Tomorrow)\s+(\d{1,2}):(\d{2})", flat)
        closes = None; prec = ""
        n = now()
        if m:
            d = n.date() + timedelta(days=0 if m.group(1) == "Today" else 1)
            closes = datetime(d.year, d.month, d.day, int(m.group(2)), int(m.group(3)), tzinfo=LONDON); prec = "exact"
        else:
            m = re.search(r"(\d+)\s*days?\b", flat)
            if m:
                d = (n + timedelta(days=int(m.group(1))))
                closes = d.replace(hour=23, minute=59, second=0, microsecond=0); prec = "approx"
        m = re.search(r"(\d+)\s*% sold", flat)
        pct = float(m.group(1)) if m else None
        # title = text part following '% sold'
        title = ""
        for i, p in enumerate(parts):
            if "% sold" in p:
                title = parts[i + 1] if i + 1 < len(parts) else ""
                break
        if not title:
            continue
        pm = re.search(r"(£\d+(?:\.\d+)?|FREE)\s*(?:Basket)?\s*$", flat)
        price = pm.group(1) if pm else ""
        isfree = price == "FREE"
        cost = 0.0 if isfree else money(price)
        out.append(rec(title=title, promoter="Dream Car Giveaways", link=DCG + h, prize_desc=title,
                       prize_value=prize_value_from_text(title), entry_type="free" if isfree else "paid", entry_cost=cost,
                       entry_cost_text="FREE" if isfree else price, closes_at=closes, closes_precision=prec, pct_sold=pct,
                       entry_note="Paid ticket draw" + ("; free postal entry route on site (see 'Postal Entry Route')." if not isfree else " (free app entry; see page)."),
                       image=img_url(a, DCG + "/")))
    return out

# ---------------------------------------------------------------- Omaze
OM = "https://www.omaze.co.uk"

@source("Omaze", "operator", OM, "Operator's own public draw pages (Shopify).", direct=True)
def omaze(ctx):
    r = ctx.get(OM + "/")
    if not r: return []
    s = soup(r)
    pages = []
    for a in s.select('a[href^="/pages/"]'):
        t = clean(a.get_text())
        if t in ("The Yorkshire House", "£100k + BMW M3 Touring", "Monthly Millionaire") or (t and a["href"] in ("/pages/yorkshire-iv", "/pages/yorkshire-iv-win-a-bmw-m3", "/pages/monthly-millionaire")):
            if a["href"] not in [p[0] for p in pages]: pages.append((a["href"], t))
    texts = {}; imgs = {}
    for h, t in pages:
        rr = ctx.get(OM + h)
        if not rr: continue
        ss = soup(rr)
        for x in ss(["script", "style", "noscript"]): x.decompose()
        texts[h] = clean(ss.get_text(" "))
        imgs[h] = og_image(ss, OM + "/")
    out = []
    mm = texts.get("/pages/monthly-millionaire", "")
    house_close = None; mm_close = None
    m = re.search(r"House Draw will close on (\d{1,2}(?:st|nd|rd|th)? \w+ 20\d\d)", mm); house_close = parse_date(m.group(1)) if m else None
    m = re.search(r"Monthly Millionaire Draw will close on (\d{1,2}(?:st|nd|rd|th)? \w+ 20\d\d)", mm); mm_close = parse_date(m.group(1)) if m else None
    for h, t in pages:
        txt = texts.get(h, "")
        if not txt: continue
        if h.endswith("yorkshire-iv"):
            v = re.search(r"WIN THIS £([\d,]+) (?:MILLION )?HOUSE", txt, re.I)
            title = "Win the Yorkshire House (£4M) + £250,000 cash – Omaze"
            out.append(rec(title=title, promoter="Omaze", link=OM + h, prize_desc="£4,000,000 house in Yorkshire plus £250,000 cash; supports Blood Cancer UK. One guaranteed winner.",
                           prize_value=4000000.0, entry_type="paid", closes_at=house_close, closes_precision="date" if house_close else "",
                           entry_note="Paid entries (price tiers on page); No Purchase Necessary postal route per Omaze T&Cs.", image=imgs.get(h, "")))
        elif "bmw" in h:
            m = re.search(r"by (\d{1,2}(?:st|nd|rd|th)? \w+,? 20\d\d)", txt)
            c = parse_date(m.group(1)) if m else None
            out.append(rec(title="Early Bird: £100k cash + BMW M3 Touring – Omaze", promoter="Omaze", link=OM + h,
                           prize_desc="Early-bird prize: £100,000 cash + BMW M3 Touring for entering the Yorkshire House Draw early.",
                           prize_value=100000.0, entry_type="paid", closes_at=c, closes_precision="date" if c else "",
                           entry_note="Bonus prize for early entries to the Yorkshire House Draw (paid; postal No Purchase Necessary route in T&Cs).", image=imgs.get(h, "")))
        elif "monthly-millionaire" in h:
            m = re.search(r"£(\d+) (\d+) Entries", txt)
            cost = float(m.group(1)) if m else None
            out.append(rec(title="Monthly Millionaire – £1,000,000 cash – Omaze", promoter="Omaze", link=OM + h,
                           prize_desc="£1,000,000 cash (paid in instalments); 1 guaranteed winner monthly.", prize_value=1000000.0,
                           entry_type="paid", entry_cost=cost, entry_cost_text=(f"from £{cost:g}" if cost else ""),
                           closes_at=mm_close, closes_precision="date" if mm_close else "",
                           entry_note="Paid entries (£10/£20/£30 packs); Postal entry – No Purchase Necessary.", image=imgs.get(h, "")))
    return out

# ---------------------------------------------------------------- MSE forum
MSE = "https://forums.moneysavingexpert.com"

@source("MSE Competitions Time", "forum", MSE + "/categories/competitions-time", "Public forum listing (robots permit); links go to forum threads that contain the entry link.")
def mse(ctx):
    out = []; seen = set()
    for p in ["/categories/competitions-time", "/categories/competitions-time/p2", "/categories/competitions-time/p3"]:
        r = ctx.get(MSE + p)
        if not r: continue
        for a in soup(r).select('a[href*="/discussion/"]'):
            title = clean(a.get_text())
            m = re.match(r"E:\s*(\d{1,2})/(\d{1,2})\s*(.*)", title)
            if not m: continue
            link = a["href"].split("?")[0]
            if link in seen: continue
            seen.add(link)
            closes = infer_year(int(m.group(1)), int(m.group(2)))
            rest = m.group(3)
            tags = re.findall(r"\(([^)]{1,25})\)", rest)
            rest_clean = clean(re.sub(r"\((Gleam|Photo Effort|NL|MD|Daily|Weekly|Instagram|Twitter|Facebook|FB|IG)\)", "", rest, flags=re.I))
            hints = {"gleam": "Gleam widget entry", "photo effort": "Photo/creative entry", "nl": "Newsletter signup", "md": "Multiple draws/winners (MSE tag 'MD')", "daily": "Daily entry"}
            note = "MSE forum thread (free-to-enter comps; thread has the link & forumites' entry tips)."
            if tags: note += " Tags: " + ", ".join(hints.get(t.lower(), t) for t in tags) + "."
            out.append(rec(title=rest_clean or title, link=link, prize_desc=rest_clean, prize_value=prize_value_from_text(rest_clean),
                           entry_type="free", closes_at=closes, closes_precision="date" if closes else "", entry_note=note))
    return out

# ---------------------------------------------------------------- Competitions Time
CT = "https://www.competitions-time.co.uk"

@source("Competitions Time", "aggregator", CT, "Curated free comps (closing-soonest first, ~10 pages); promoter link is behind /redir (disallowed) so link goes to the listing page.")
def competitions_time(ctx):
    out = []; seen = set()
    for p in ["/", "/new"] + [f"/page/{i}" for i in range(2, 12)]:
        r = ctx.get(CT + p)
        if not r:
            if "/page/" in p:  # ran off the end of the listing
                ctx.errors[:] = [e for e in ctx.errors if not ("HTTP 404" in e and "/page/" in e)]
                break
            continue
        s = soup(r)
        for d in s.select("div.comp-desc"):
            a = d.select_one("a")
            if not a: continue
            title = clean(a.get_text())
            txt = clean(d.get_text(" "))
            site = re.search(r"Website:\s*(\S+)", txt)
            closing = re.search(r"Closing:\s*(\d{1,2}\w{2} \w+ 20\d\d)", txt)
            k = (title, site.group(1) if site else "")
            if k in seen: continue
            seen.add(k)
            prev = d.find_previous_sibling("div", class_=re.compile("comp-type"))
            btxt = clean(prev.get_text(" ")) if prev else ""
            note = "Free-to-enter comp listed on Competitions Time"
            if "Registration" in btxt: note += "; account registration required"
            if "Marketing" in btxt: note += "; marketing opt-in"
            if "Multiple" in btxt: note += "; multiple winners"
            closes = parse_date(closing.group(1)) if closing else None
            out.append(rec(title=title, promoter=site.group(1) if site else "", link=CT + a["href"], prize_desc=title,
                           prize_value=prize_value_from_text(title), entry_type="free", closes_at=closes,
                           closes_precision="date" if closes else "", entry_note=note + ".", skey=f"{title}|{site.group(1) if site else ''}"))
        for c in s.select("div.cc2-card"):
            h = c.select_one(".cc2-title")
            if not h: continue
            title = clean(h.get_text())
            w = c.select_one(".cc2-website"); site = clean(w.get_text()) if w else ""
            k = (title, site)
            if k in seen: continue
            seen.add(k)
            dt = c.select_one(".cc2-date-text")
            closes = parse_date(clean(dt.get_text())) if dt else None
            badges = clean((c.select_one(".cc2-badges") or c).get_text(" "))
            note = "Free-to-enter comp listed on Competitions Time"
            if "Registration" in badges: note += "; account registration required"
            if "Marketing" in badges: note += "; marketing opt-in"
            if "Multiple" in badges: note += "; multiple winners"
            cat = c.select_one(".cc2-cat-name")
            out.append(rec(title=title, promoter=site, link=f"{CT}{p if p != '/' else ''}#{c.get('id','')}", prize_desc=title,
                           prize_value=prize_value_from_text(title), entry_type="free", closes_at=closes,
                           closes_precision="date" if closes else "", entry_note=note + ".", skey=f"{title}|{site}",
                           image=img_url(c, CT + "/")))
    return out

# ---------------------------------------------------------------- Competitions Today
CTD = "https://www.competitionstoday.co.uk"

@source("Competitions Today", "aggregator", CTD, "Free comps; links point at the site's own detail page.")
def competitions_today(ctx):
    out = []; seen = set()
    for p in ["/", "/latestcompetitions.php", "/competitionsendingsoon.php", "/premium-competitions.php", "/daily-competitions.php", "/most-popular-competitions.php"]:
        r = ctx.get(CTD + p)
        if not r: continue
        s = soup(r)
        for a in s.select("a[href]"):
            h = a["href"]
            if "go.php" in h or "#" in h or h.startswith("http") or ".php" in h or h in ("/", "") or "categories" in h: continue
            title = clean(a.get_text())
            if len(title) < 12 or not re.search(r"\b(win|chance|enter|share|prize|get)\b", title, re.I) and "?p=n" not in h: continue
            link = CTD + "/" + h.lstrip("/").split("?")[0]
            if link in seen: continue
            # find the "Closes:" text in the enclosing block
            box = a; closes = None
            for _ in range(4):
                box = box.parent
                if box is None: break
                m = re.search(r"Closes:\s*(\d{1,2}\w{2} \w+ 20\d\d)", clean(box.get_text(" ")))
                if m:
                    # make sure the block contains only one title link
                    if len([x for x in box.select("a.hpStdLink, a[href]") if x.get("href", "").split("?")[0] == a["href"].split("?")[0]]) >= 1:
                        closes = parse_date(m.group(1)); break
            seen.add(link)
            out.append(rec(title=title, link=link, prize_desc=title, prize_value=prize_value_from_text(title), entry_type="free",
                           closes_at=closes, closes_precision="date" if closes else "",
                           entry_note="Free comp listed on Competitions Today (check page: some need registration/purchase)."))
    return out

# ---------------------------------------------------------------- FindCompetitions
FC = "https://findcompetitions.com"

@source("FindCompetitions", "aggregator", FC, "Comparison site covering 100+ paid/free operators; direct operator links + ticket counts from public detail pages (cached, capped per run).")
def findcompetitions(ctx):
    pages = ["/win/free", "/win/free?page=2", "/win/free?page=3", "/competitions", "/competitions?page=2", "/competitions?page=3",
             "/competitions/ending-soon", "/competitions/ending-soon?page=2", "/competitions/category/cars", "/competitions/category/cars?page=2",
             "/competitions/category/cash", "/competitions/category/cash?page=2", "/competitions/category/tech", "/competitions/category/tickets"]
    items = {}
    for p in pages:
        r = ctx.get(FC + p)
        if not r: continue
        s = soup(r)
        for a in s.select('a[href*="/competitions/c/"]'):
            h = a["href"].split("?")[0]
            if h in items: continue
            box = a
            parts = []
            for _ in range(3):
                box = box.parent
                parts = [x.strip() for x in clean(box.get_text("|")).split("|") if x.strip()]
                if any(re.search(r"\b\d+\s*[dhm]\s+left\b", x) for x in parts): break
            op = left = title = ""
            for i, x in enumerate(parts):
                if re.search(r"\b\d+\s*[dhm]\s+left\b", x):
                    left = x; op = parts[i - 1] if i else ""; title = parts[i + 1] if i + 1 < len(parts) else ""
                    break
            if not title: continue
            # the card picture sits a level or two above the text box; stop before reaching a neighbouring card
            ib = box; image = img_url(ib, FC + "/")
            for _ in range(3):
                if image or ib.parent is None: break
                ib = ib.parent
                if len({x["href"].split("?")[0] for x in ib.select('a[href*="/competitions/c/"]')}) > 1: break
                image = img_url(ib, FC + "/")
            items[h] = dict(op=op, left=left, title=title, image=image)
    # details
    cap = ctx.cap("fc", 70)
    order = sorted(items, key=lambda l: (ctx.cache_age(l)))  # uncached first (age=inf->first via -1), then oldest
    n = 0
    for l in order:
        if n >= cap: break
        age = ctx.cache_age_hours(l)
        if age is not None and age < 5: continue
        r = ctx.get(l); n += 1
        if not r: continue
        s = soup(r)
        d = {}
        for sc in s.select('script[type="application/ld+json"]'):
            try: j = json.loads(sc.string or "")
            except Exception: continue
            if isinstance(j, dict) and j.get("@type") == "Product":
                off = j.get("offers") or {}
                d["price"] = off.get("price"); d["url"] = off.get("url"); d["brand"] = (j.get("brand") or {}).get("name")
                im = j.get("image"); im = im[0] if isinstance(im, list) and im else im
                if isinstance(im, str) and im.startswith("http"): d["image"] = im
            if isinstance(j, dict) and j.get("@type") == "FAQPage":
                for q in j.get("mainEntity", []):
                    if q.get("name", "").startswith("When does the draw close"):
                        d["close_text"] = (q.get("acceptedAnswer") or {}).get("text", "")
                    if q.get("name", "").startswith("Is there a free entry"):
                        d["free_route"] = (q.get("acceptedAnswer") or {}).get("text", "").startswith("Yes")
        for x in s(["script", "style", "noscript"]): x.decompose()
        t = clean(s.get_text(" "))
        m = re.search(r"([\d,]+) / ([\d,]+) tickets", t)
        if m: d["sold"] = int(m.group(1).replace(",", "")); d["total"] = int(m.group(2).replace(",", ""))
        m = re.search(r"(\d+)% sold", t)
        if m: d["pct"] = int(m.group(1))
        if d.get("brand"):
            m = re.search(re.escape(d["brand"]) + r"\s+(Verified|Trusted|Listed|Unrated|Caution|Avoid|New)\b", t)
            if m: d["trust"] = m.group(1)
        d["vcode"] = "Signatory of the UK Voluntary Code" in t
        ctx.cache_put(l, d)
    out = []
    for l, it in items.items():
        d = ctx.cache_get(l) or {}
        closes = None; prec = ""
        ct = d.get("close_text", "")
        m = re.search(r"(\d{1,2}) (\w+) (20\d\d) at (\d{1,2})(?::(\d{2}))?\s*(am|pm)", ct, re.I)
        if m:
            mon = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}[m.group(2)[:3].lower()]
            h = int(m.group(4)) % 12 + (12 if m.group(6).lower() == "pm" else 0)
            closes = datetime(int(m.group(3)), mon, int(m.group(1)), h, int(m.group(5) or 0), tzinfo=LONDON); prec = "exact"
        else:
            closes = approx_from_left(it["left"].replace(" left", "")); prec = "approx" if closes else ""
        price = d.get("price")
        try: cost = float(price) if price not in (None, "") else None
        except ValueError: cost = None
        direct = d.get("url") or ""
        isfree = cost == 0
        note = "Via FindCompetitions (comparison site; entry happens on the operator's site)."
        if d.get("free_route") and not isfree: note += " Operator publishes a free postal/no-purchase entry route."
        out.append(rec(title=it["title"], promoter=d.get("brand") or it["op"], link=direct or l, prize_desc=it["title"],
                       prize_value=prize_value_from_text(it["title"]), entry_type=("free" if isfree else "paid") if cost is not None else "",
                       entry_cost=cost, entry_cost_text=("FREE" if isfree else (f"£{cost:g}" if cost is not None else "")),
                       closes_at=closes, closes_precision=prec, tickets_sold=d.get("sold"), tickets_total=d.get("total"),
                       pct_sold=d.get("pct"), entry_note=note, skey=l, image=it.get("image") or d.get("image") or ""))
        out[-1]["agg_link"] = l
        out[-1]["extra"] = {"fc_trust": d.get("trust", ""), "vcode": bool(d.get("vcode")), "free_route": d.get("free_route")}
    ctx.meta["fc_list_items"] = len(items)
    return out

# ---------------------------------------------------------------- Nitrous
NIT = "https://nitrouscompetitions.com"

@source("Nitrous Competitions", "operator", NIT + "/all-competitions", "Small paid car/bike/cash operator; own public listing.", direct=True)
def nitrous(ctx):
    r = ctx.get(NIT + "/all-competitions")
    if not r: return []
    s = soup(r); out = []; seen = set()
    for a in s.select('a[href^="/competition/"]'):
        h = a["href"]
        if h in seen: continue
        seen.add(h)
        txt = clean(a.get_text(" "))
        txt2 = re.sub(r"^(?:⏰\s*)?(?:Closes (?:today|in \d+ \w+)|Ends[^A-Z]*)\s*", "", txt)
        txt2 = re.sub(r"PRICE DROP\s*", "", txt2)
        m = re.match(r"(.*?)\s+(£\d+(?:\.\d+)?|\d+p)\s+(?:(£\d+(?:\.\d+)?|\d+p)\s+)?per entry", txt2)
        if not m: continue
        title = clean(m.group(1)); cost = pence_or_pounds(m.group(3) or m.group(2))
        dm = re.search(r"Draws\s+\w{3}\s+(\d{1,2})\s+(\w{3})\s*·\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)", txt)
        closes = None
        if dm:
            mon = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}[dm.group(2).lower()]
            hh = int(dm.group(3)) % 12 + (12 if dm.group(5).lower() == "pm" else 0)
            closes = infer_year(int(dm.group(1)), mon, hh, int(dm.group(4) or 0))
        sm = re.search(r"([\d,]+)\s+sold\s*\(\s*(\d+)\s*%", txt)
        out.append(rec(title=title, promoter="Nitrous Competitions", link=NIT + h, prize_desc=title, prize_value=prize_value_from_text(title),
                       entry_type="paid", entry_cost=cost, entry_cost_text=f"£{cost:g}" if cost is not None else "",
                       closes_at=closes, closes_precision="exact" if closes else "",
                       tickets_sold=int(sm.group(1).replace(",", "")) if sm else None, pct_sold=float(sm.group(2)) if sm else None,
                       entry_note="Paid entries (skill question); free postal entry route on every Nitrous competition.",
                       image=img_url(a, NIT + "/")))
    return out

# ---------------------------------------------------------------- Compete For Cars
CFC = "https://competeforcars.co.uk"

@source("Compete For Cars", "operator", CFC + "/current-competitions/", "Small paid car operator; own public listing (WooCommerce).", direct=True)
def competeforcars(ctx):
    r = ctx.get(CFC + "/current-competitions/")
    if not r: return []
    s = soup(r); out = []
    for li in s.select("li.product"):
        a = li.select_one("a[href*='/product/']")
        if not a: continue
        t = li.select_one("h2, h3, .woocommerce-loop-product__title")
        title = clean(t.get_text()) if t else clean(a.get_text())
        txt = clean(li.get_text(" "))
        title = re.sub(r"^Win This Incredible\s*", "", title).strip() or title
        pm = re.search(r"£\s?(\d+(?:\.\d+)?)", txt)
        cost = float(pm.group(1)) if pm else None
        dt = li.select_one("[data-time]")
        closes = None
        if dt:
            try: closes = datetime.fromtimestamp(int(dt["data-time"]), LONDON)
            except Exception: pass
        out.append(rec(title=title, promoter="Compete For Cars", link=a["href"], prize_desc=txt[:200], entry_type="paid", entry_cost=cost,
                       entry_cost_text=f"£{cost:g}" if cost is not None else "", closes_at=closes, closes_precision="exact" if closes else "",
                       entry_note="Paid entries (qualifying question); free postal entry route per their FAQ.",
                       image=img_url(li.select_one("img.attachment-woocommerce_thumbnail") or li, CFC + "/")))
    return out

# ---------------------------------------------------------------- Latest Deals (community-posted free comps)
LD = "https://www.latestdeals.co.uk"
_LD_OBJ = re.compile(r'\{_id:"([0-9a-f]{24})",(.*?)\}', re.S)
_LD_KV = re.compile(r'(\w+):("(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?|!0|!1|null)')

def _ld_items(html):
    """The listing page embeds its data as a JS object stream ({_id:"..",title:"..",...}); read the flat competition records."""
    out = []
    for m in _LD_OBJ.finditer(html):
        d = {"_id": m.group(1)}
        for k, v in _LD_KV.findall(m.group(2)):
            if v.startswith('"'):
                try: v = json.loads(v)
                except ValueError: v = v.strip('"')
            elif v in ("!0", "!1"): v = v == "!0"
            elif v == "null": v = None
            else: v = float(v) if "." in v else int(v)
            d.setdefault(k, v)
        if d.get("type") == "competition" and d.get("title") and d.get("slug"):
            out.append(d)
    return out

@source("Latest Deals", "aggregator", LD + "/competitions",
        "Community-posted UK competitions (mostly free). Data embedded in the public listing pages (first pages only); links go to Latest Deals' page for each comp.")
def latestdeals(ctx):
    seen = {}
    for page in range(1, ctx.cap("ld_pages", 8) + 1):
        # a 202 means "accepted but not ready" (or a bot-challenge); the fetcher polls with backoff, giving up after a few tries
        r = ctx.get(LD + "/competitions" + (f"?page={page}" if page > 1 else ""), retries=3 if page == 1 else 2)
        if not r: break
        got = _ld_items(r.text)
        new = [d for d in got if d["_id"] not in seen]
        for d in new: seen[d["_id"]] = d
        if not new: break
    out = []; n = now()
    for d in seen.values():
        closes = None
        try:
            if d.get("endDate"): closes = datetime.fromisoformat(d["endDate"].replace("Z", "+00:00")).astimezone(LONDON)
        except ValueError: pass
        if closes and closes < n: continue
        entry = d.get("entry") or ""
        host = d.get("competitionHost") or ""
        promoter = d.get("merchantName") or host
        if host.startswith("@"): promoter = f"{host} on {d.get('merchantName') or entry or 'social media'}"
        elif promoter.lower() in ("x", "twitter", "instagram", "facebook", "tiktok", "youtube", "threads", "gleam"):
            promoter = f"Giveaway on {promoter}"
        paid = bool(re.search(r"\b(text|sms|phone|call|purchase|buy)\b", entry, re.I))
        note = f"Entry: {entry}" + (f" (@{host.lstrip('@')})" if host.startswith("@") else "") + "." if entry else "See the page for how to enter."
        if d.get("frequency") and d["frequency"] != "Once": note += f" Enter {d['frequency'].lower()}."
        note += " Posted by the Latest Deals community; open their page for the promoter's entry link."
        img = f"https://images.latestdeals.co.uk/post-small/p-{d['_id']}-{d['image']}.jpg" if isinstance(d.get("image"), int) and d["image"] > 0 else ""
        out.append(rec(title=d["title"], promoter=promoter, link=f"{LD}/competitions/{d['slug']}", prize_desc=d["title"],
                       prize_value=prize_value_from_text(d["title"]), entry_type="" if paid else "free",
                       closes_at=closes, closes_precision="exact" if closes else "", entry_note=note, skey="ld:" + d["_id"], image=img))
    ctx.meta["ld_items"] = len(seen)
    return out

# ---------------------------------------------------------------- ITV Win (This Morning, GMB, Lorraine ...)
ITV = "https://www.itv.com/win"

@source("ITV Win", "operator", ITV + "/", "ITV's competitions hub (This Morning, GMB, Loose Women...). One request per run to the JSON the page itself loads.", direct=True)
def itv_win(ctx):
    r = ctx.get(ITV + "/api/v9/init", timeout=(10, 45), retries=2)   # ~200 KB JSON; from GitHub runners it times out even at 75s x4 (host appears to tarpit datacentre IPs), so fail fast
    if not r: return []
    try: data = r.json()
    except ValueError:
        ctx.errors.append("ITV: response was not JSON"); return []
    out = []
    for c in data.get("competitions") or []:
        if c.get("status") not in ("active", "on-hold") or not c.get("isCompetition", True): continue
        meta = c.get("meta") or {}
        if (meta.get("comingSoon") or {}).get("dateStart"): continue
        card = ((meta.get("display") or {}).get("card") or {}).get("title") or ""
        title = clean(BeautifulSoup(card, "lxml").get_text(" ")) if card else ""
        title = title.rstrip("!") or ("Win " + clean(c.get("name") or ""))
        closes = None
        try:
            if c.get("dateStop"): closes = datetime.fromisoformat(c["dateStop"].replace("Z", "+00:00")).astimezone(LONDON)
        except ValueError: pass
        pay = meta.get("payment") or {}
        chans = [k for k, v in (meta.get("channels") or {}).items() if isinstance(v, dict) and v.get("enabled")]
        if c.get("isFree"):
            etype, cost, ctext, note = "free", 0.0, "FREE", "Free to enter online (ITV account)."
        elif c.get("isTokenPaid"):
            etype, cost, ctext, note = "paid", None, "ITV Win tokens", "Entered with ITV Win tokens (bought on the site)."
        else:
            cost = (pay.get("cost") or 0) / 100 or None
            etype, ctext = "paid", (f"£{cost:g}" if cost else "")
            note = "Paid entry" + (f" from £{cost:g}" if cost else "") + " via " + ", ".join(x for x in chans if x != "postal") + "."
        if c.get("hasQuiz"): note += " Entry includes a quiz question."
        if "postal" in chans: note += " Free postal entry route available (see ITV's terms)."
        media = (meta.get("media") or {}).get("desktop") or {}
        pic = media.get("cardImage") or media.get("detailsImage") or ""
        name = clean(c.get("name") or title)
        out.append(rec(title=title, promoter="ITV", link=f"{ITV}/competitions/{c['id']}", prize_desc=name,
                       prize_value=prize_value_from_text(name), entry_type=etype, entry_cost=cost, entry_cost_text=ctext,
                       closes_at=closes, closes_precision="exact" if closes else "", entry_note=note, skey=f"itv:{c['id']}",
                       image=f"{ITV}/files/640xAUTO/{pic}" if pic else "", tags=["tv"]))
    return out

# ---------------------------------------------------------------- olive magazine (Immediate Media)
OLV = "https://www.olivemagazine.com"

@source("olive magazine", "publisher", OLV + "/competitions/", "Immediate Media food & travel magazine's own competitions page (free to enter; closing dates are on each page).")
def olive(ctx):
    r = ctx.get(OLV + "/competitions/")
    if not r: return []
    out = []; seen = set()
    for art in soup(r).select("article.card"):
        a = art.select_one('a[href*="/competitions/"]')
        title = clean(art.get("data-item-name") or (a.get_text() if a else ""))
        if not a or not title or a["href"] in seen: continue
        seen.add(a["href"])
        link = a["href"] if a["href"].startswith("http") else OLV + a["href"]
        image = img_url(art, OLV + "/")
        if not image:
            src = art.select_one("picture source[srcset]")
            if src:
                cands = re.findall(r"(\S+)\s+(\d+)w\b", src["srcset"])
                if cands: image = max(cands, key=lambda c: int(c[1]))[0]
        out.append(rec(title=title, promoter="olive magazine", link=link, prize_desc=title, prize_value=prize_value_from_text(title),
                       entry_type="free", entry_note="Free magazine competition; closing date and terms are on the competition page.",
                       skey=link, image=image))
    # closing dates are stated in each page's terms text ("Closing date for entries is 23.59 on …"); an old date means a dead listing
    dates = detail_closing(ctx, [o["link"] for o in out], ctx.cap("olive_detail", 20))
    keep = []
    for o in out:
        d = dates.get(o["link"])
        if d:
            if d[0] < now(): continue
            o["closes_at"], o["closes_precision"] = d
        keep.append(o)
    return keep

# ================================================================ RADIO
MONTH_RX = "january|february|march|april|may|june|july|august|september|october|november|december"

def _radio_rec(**kw):
    kw.setdefault("tags", ["radio"])
    return rec(**kw)

GLOBAL_STATIONS = [("Heart", "https://www.heart.co.uk/digital/win/"), ("Capital", "https://www.capitalfm.com/digital/win/"),
                   ("Capital XTRA", "https://www.capitalxtra.com/win/"), ("Smooth", "https://www.smoothradio.com/win/"),
                   ("Classic FM", "https://www.classicfm.com/win/"), ("Radio X", "https://www.radiox.co.uk/win/")]

@source("Radio: Global (Heart, Capital, Smooth, Classic FM, Radio X…)", "radio", "https://www.heart.co.uk/digital/win/",
        "Public /win pages of Global stations. LBC/Gold: no public prize-draw list reachable (LBC redirects to news; gold.radio unreachable).")
def radio_global(ctx):
    comps = {}; arts = {}
    for name, url in GLOBAL_STATIONS:
        r = ctx.get(url)
        if not r: continue
        s = soup(r)
        for a in s.select('a[href*="winplus."]'):
            m = re.search(r"winplus\.[^/]+/competition/(\d+|cashcall)(?:/([a-z0-9-]+))?", a["href"])
            title = clean(a.get_text())
            if not m or not title: continue
            cid = m.group(1)
            c = comps.setdefault(cid, dict(title=title, stations=[], slug=m.group(2) or "", host=re.search(r"//(winplus\.[^/]+)", a["href"]).group(1), image=""))
            c["image"] = c["image"] or img_url(a, url)
            if name not in c["stations"]: c["stations"].append(name)
        base = re.match(r"https?://[^/]+", url).group(0)
        for a in s.select('a[href^="/win/"]'):
            t = clean(a.get_text()); h = a["href"].split("?")[0]
            if not t or h.rstrip("/") == "/win" or "terms" in h or "faq" in h: continue
            if not re.match(r"^(win\b|how to win|enter\b|chance to win|\w+ .*\bwin\b(?! \w+ £))", t, re.I) or re.search(r"\bwins\b|\bwon\b|winner\b.*(announced|revealed)", t, re.I): continue
            k = base + h
            for k2, v2 in arts.items():
                if v2["title"].lower() == t.lower(): k = k2; break
            c = arts.setdefault(k, dict(title=t, stations=[], image=""))
            c["image"] = c["image"] or img_url(a, url)
            if name not in c["stations"]: c["stations"].append(name)
    out = []
    # station articles (heart.co.uk/win/…) carry their terms as static text; winplus.* pages are JS-only, so no dates there
    adates = detail_closing(ctx, [k for k in arts if "winplus." not in k and "birthday-draw" not in k], ctx.cap("global_detail", 15), recheck_hours=48)
    for cid, c in comps.items():
        slug = c["slug"] or cid
        link = f"https://{c['host']}/competition/{cid}" + (f"/{c['slug']}" if c["slug"] else "")
        title = re.sub(r"!$", "", c["title"])
        out.append(_radio_rec(title=title, promoter="Global (" + ", ".join(c["stations"]) + ")", station=", ".join(c["stations"]), link=link,
                              prize_desc=title, prize_value=prize_value_from_text(title),
                              entry_note="Global WIN+: sign in with a free Global iD / UK mobile number. Some Win+ competitions sell optional entry bundles – read the competition page and terms before paying.",
                              skey=f"global:{cid}", image=c["image"]))
    for k, c in arts.items():
        ad = adates.get(k)
        if ad and ad[0] < now(): continue
        out.append(_radio_rec(title=c["title"], promoter="Global (" + ", ".join(c["stations"]) + ")", station=", ".join(c["stations"]), link=k,
                              prize_desc=c["title"], prize_value=prize_value_from_text(c["title"]),
                              entry_type="paid" if re.search(r"birthday draw", c["title"], re.I) else "",
                              closes_at=ad[0] if ad else None, closes_precision=ad[1] if ad else "",
                              entry_note=("The Birthday Draw is a paid weekly prize draw (Global & ITV); check its rules for the free entry route. " if re.search(r"birthday draw", c["title"], re.I) else "") + "Station competition article – see page for how to enter and closing date.", skey="global:" + k, image=c["image"]))
    ctx.meta["stations_ok"] = len({s for c in list(comps.values()) + list(arts.values()) for s in c["stations"]})
    return out

BAUER_STATIONS = [("kiss", "Kiss"), ("kisstory", "Kisstory"), ("absolute-radio", "Absolute Radio"), ("hits-radio", "Hits Radio"),
                  ("greatest-hits", "Greatest Hits Radio"), ("magic", "Magic"), ("mellow-magic", "Mellow Magic"), ("jazz-fm", "Jazz FM"),
                  ("planet-rock", "Planet Rock"), ("kerrang", "Kerrang! Radio"), ("heat", "Heat Radio"), ("clyde", "Clyde 1"),
                  ("forth", "Forth 1"), ("tay", "Tay FM"), ("northsound", "Northsound 1"), ("mfr", "MFR"), ("downtown", "Downtown Radio"),
                  ("cool-fm", "Cool FM")]
_JUNK = re.compile(r"(terms|ts-and-cs|t-cs|-tcs|survey|trial-job|register|what-you-think|tell-us|call-yersel|music-online-quiz|kool-ride|on-?air-terms|privacy|faq)", re.I)

@source("Radio: Bauer / Hello Rayo (Kiss, Absolute, Hits, Magic, Jazz FM, Clyde…)", "radio", "https://www.hellorayo.co.uk/kiss/competitions",
        "Bauer Media public competition pages for 18 national/regional stations; closing dates are only on JS-rendered detail pages, so usually blank.")
def radio_bauer(ctx):
    comps = {}; n_ok = 0
    n = now()
    for slug, name in BAUER_STATIONS:
        r = ctx.get(f"https://www.hellorayo.co.uk/{slug}/competitions")
        if not r: continue
        n_ok += 1
        for a in soup(r).select('a[href*="/competitions/win/"]'):
            m = re.search(r"/competitions/win/([a-z0-9-]+)", a["href"])
            title = clean(a.get_text())
            if not m or len(title) < 6 or title.lower() == "win": continue
            cs = m.group(1)
            if _JUNK.search(cs) or _JUNK.search(title): continue
            if not re.search(r"\b(win|winner|chance|prize|prizes|giveaway|draw|tickets?|cash|vip|£\s?\d)", title, re.I) or re.search(r"^listen\b", title, re.I): continue
            c = comps.setdefault(cs, dict(title=title, stations=[], first=slug))
            if name not in c["stations"]: c["stations"].append(name)
    out = []
    # closing dates: a few Bauer pages are competition T&Cs whose static text states the period ("… from Monday 29th June to
    # Friday 3rd July 2026"); most entry pages are JS widgets with no date, which stay blank (never guessed)
    def _slug_date(cs):
        m = re.search(r"(\d{1,2})(?:st|nd|rd|th)-(" + MONTH_RX + ")", cs)
        return parse_date(f"{m.group(1)} {m.group(2)} {n.year}") if m else None
    plinks = {cs: f"https://www.hellorayo.co.uk/{c['first']}/competitions/win/{cs}" for cs, c in comps.items()}
    undated = [plinks[cs] for cs, c in comps.items() if not _slug_date(cs) and not re.match(r"^\W*closed\b", c["title"], re.I)]
    dates = detail_closing(ctx, undated, ctx.cap("bauer_detail", 40), recheck_hours=96)
    for cs, c in comps.items():
        closes = None; prec = "date"
        m = re.search(r"(\d{1,2})(?:st|nd|rd|th)-(" + MONTH_RX + ")", cs)
        if m:
            closes = _slug_date(cs)
            if closes and closes < n - timedelta(days=1): continue  # dated slug in the past
        elif plinks[cs] in dates:
            closes, prec = dates[plinks[cs]]
            if closes < n: continue                                    # the page's own T&Cs say it has finished
        title = c["title"]
        paid = bool(re.search(r"make me a winner", title, re.I))
        out.append(_radio_rec(title=title, promoter="Bauer Media (" + ", ".join(c["stations"][:4]) + (" +%d more" % (len(c["stations"]) - 4) if len(c["stations"]) > 4 else "") + ")",
                              station=", ".join(c["stations"]), link=f"https://www.hellorayo.co.uk/{c['first']}/competitions/win/{cs}",
                              prize_desc=title, prize_value=prize_value_from_text(title), closes_at=closes, closes_precision=prec if closes else "",
                              entry_type="paid" if paid else "", entry_note=("Make Me A Winner is a paid prize draw promoted on Bauer stations; free postal entry in its rules. " if paid else "") + "Radio station competition (online/on-air); open the page for the entry method and closing date.",
                              skey=f"bauer:{cs}"))
    ctx.meta["stations_ok"] = n_ok
    return out

