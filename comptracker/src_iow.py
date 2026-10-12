"""Isle of Wight local competitions (UK sources tagged 'iow'). Public pages only, no Facebook, no logins.
Checked Oct 2026: isleofwightradio.com is a parked domain (the station is iwradio.co.uk, which has no competitions page);
Wightlink / Red Funnel / Hovertravel / IOW Festival have no public competitions page (their giveaways run on social media);
Island Echo's search/API is behind a Cloudflare challenge (its public RSS feed is used)."""
import re
from datetime import timedelta
from .sources import source, rec, soup, clean, img_url, detail_closing
from .util import now, prize_value_from_text, closing_from_text, parse_date

IOW_RX = re.compile(r"(isle of wight|\bI\.?o\.?W\b|wightlink|red funnel|hovertravel|\bventnor\b|\bshanklin\b|\bsandown\b(?! park)|\bryde\b|\bcowes\b|"
                    r"robin hill|blackgang|the needles (?:landmark|attraction|park)|osborne house|tapnell|monkey haven|garlic farm|\bbembridge\b|"
                    r"\bgodshill\b|\bseaview hotel|\bwight\b|\bislanders?\b.*\bwight)", re.I)

def is_iow(it):
    return bool(IOW_RX.search(" ".join([it.get("title") or "", it.get("prize_desc") or "", it.get("promoter") or "", it.get("link") or ""])))

CP = "https://www.countypress.co.uk"

@source("Isle of Wight County Press", "publisher", CP + "/competitions/",
        "The Island's newspaper (Newsquest). Its competitions page; many are open to digital subscribers only (flagged as paid entry).", direct=True)
def county_press(ctx):
    r = ctx.get(CP + "/competitions/")
    if not r: return []
    out = []
    for card in soup(r).select(".omnicompetitioncard"):
        a = card.select_one('a[href*="/competitions/"]'); h3 = card.select_one("h3")
        if not a or not h3: continue
        link = a["href"] if a["href"].startswith("http") else CP + a["href"]
        title = clean(h3.get_text()); desc = clean((card.select_one(".metadata-container p") or h3).get_text())
        ban = clean((card.select_one(".banner") or card).get_text())
        cl = closing_from_text(ban) if "closing" in ban.lower() else None
        out.append(rec(title=title, promoter="Isle of Wight County Press", link=link, prize_desc=desc, prize_value=prize_value_from_text(title + " " + desc),
                       entry_type="free", entry_note="Isle of Wight County Press competition (UK residents 18+).",
                       closes_at=cl[0] if cl else None, closes_precision=cl[1] if cl else "", skey=link, image=img_url(card, CP + "/"), tags=["iow"]))
    # subscriber-only check (cached per page; re-checked every 3 days)
    for o in out:
        c = ctx.cache_get("cpsub:" + o["link"])
        if c is None or (ctx.cache_age_hours("cpsub:" + o["link"]) or 0) > 72:
            rr = ctx.get(o["link"])
            if rr is None: continue
            t = clean(soup(rr).get_text(" "))
            c = {"sub": bool(re.search(r"subscriber-only|must be a digital subscriber", t, re.I))}
            ctx.cache_put("cpsub:" + o["link"], c)
        if c.get("sub"):
            o.update(entry_type="paid", entry_cost=None, entry_cost_text="Digital subscription required",
                     entry_note="County Press digital subscribers only (subscription needed to enter).")
    return [o for o in out if not o["closes_at"] or o["closes_at"] > now()]

WIN = re.compile(r"^(win|competition|giveaway)\b|\b(competition|giveaway|prize draw)\s*[:–-]\s*win\b|\bchance to win\b|\bwin (?:a|an|tickets|one of|\d)", re.I)
NOT_COMP = re.compile(r"\b(wins|won|winner|winning|award|awards|prize for|shortlist|trophy|league|match|cup|race|bid|grants?)\b", re.I)

@source("Isle of Wight local news & tourism (OnTheWight, Island Echo, Visit Isle of Wight)", "publisher", "https://onthewight.com/",
        "OnTheWight (WordPress public API search), Island Echo (public RSS feed) and Visit Isle of Wight's competitions page; only posts that are giveaways ('Win …'). Often none are running.", direct=True, allow_empty=True)
def iow_local(ctx):
    out = []; n = {}
    # OnTheWight: public WP REST search (robots allow all), last 90 days
    after = (now() - timedelta(days=90)).strftime("%Y-%m-%dT00:00:00")
    for q in ("win", "competition", "giveaway"):
        r = ctx.get(f"https://onthewight.com/wp-json/wp/v2/posts?search={q}&per_page=30&after={after}&_fields=date,link,title,excerpt")
        if not r: continue
        try: posts = r.json()
        except ValueError: continue
        for p in posts:
            t = clean(soup_text(p.get("title", {}).get("rendered", "")))
            if WIN.search(t) and (t.lower().startswith("win ") or not NOT_COMP.search(t)):
                ex = clean(soup_text(p.get("excerpt", {}).get("rendered", "")))
                out.append(rec(title=t, promoter="OnTheWight", link=p["link"], prize_desc=ex[:300] or t, prize_value=prize_value_from_text(t),
                               entry_type="free", entry_note="OnTheWight giveaway; how to enter and closing date are in the article.", skey=p["link"], tags=["iow"]))
                n["onthewight"] = n.get("onthewight", 0) + 1
    # Island Echo: public RSS
    r = ctx.get("https://www.islandecho.co.uk/feed/")
    if r:
        for m in re.finditer(r"<item>(.*?)</item>", r.text, re.S):
            it = m.group(1)
            t = clean(soup_text(_tag(it, "title"))); link = clean(_tag(it, "link"))
            if WIN.search(t):
                out.append(rec(title=t.title() if t.isupper() else t, promoter="Island Echo", link=link, prize_desc=clean(soup_text(_tag(it, "description")))[:300] or t,
                               prize_value=prize_value_from_text(t), entry_type="free", entry_note="Island Echo giveaway; details in the article.", skey=link, tags=["iow"]))
                n["islandecho"] = n.get("islandecho", 0) + 1
    # Visit Isle of Wight: competitions page (links inside the main content that are competitions)
    r = ctx.get("https://www.visitisleofwight.co.uk/offers/competitions")
    if r:
        s = soup(r); main = s.find("main") or s
        for a in main.select("a[href]"):
            t = clean(a.get_text()); h = a["href"]
            if WIN.search(t) and "newsletter" not in h:
                link = h if h.startswith("http") else "https://www.visitisleofwight.co.uk" + h
                out.append(rec(title=t, promoter="Visit Isle of Wight", link=link, prize_desc=t, prize_value=prize_value_from_text(t),
                               entry_type="free", entry_note="Visit Isle of Wight (official tourism site) competition.", skey=link, tags=["iow"]))
                n["visitiow"] = n.get("visitiow", 0) + 1
    for k, v in n.items(): ctx.meta[k] = v
    # article closing dates ("closes at midnight on …")
    dates = detail_closing(ctx, [o["link"] for o in out], ctx.cap("iow_detail", 15))
    keep = []
    for o in out:
        d = dates.get(o["link"])
        if d:
            if d[0] < now(): continue
            o["closes_at"], o["closes_precision"] = d
        keep.append(o)
    return keep

def soup_text(html):
    return re.sub(r"<[^>]+>", " ", html or "").replace("&#8217;", "’").replace("&#8216;", "‘").replace("&#038;", "&").replace("&amp;", "&").replace("&#8211;", "–")

def _tag(xml, name):
    m = re.search(rf"<{name}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{name}>", xml, re.S)
    return m.group(1) if m else ""
