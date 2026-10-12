"""Isle of Wight local competitions (UK sources tagged 'iow'). Public pages only, no Facebook, no logins.
Checked Oct 2026: isleofwightradio.com is a parked domain (the station is iwradio.co.uk, which has no competitions page);
Wightlink / Red Funnel / Hovertravel / IOW Festival have no public competitions page (their giveaways run on social media);
Island Echo's search/API is behind a Cloudflare challenge (its public RSS feed is used)."""
import re
from datetime import timedelta, datetime
from .sources import source, rec, soup, clean, img_url, detail_closing
from .util import now, prize_value_from_text, closing_from_text, parse_date

IOW_RX = re.compile(r"(isle of wight|\bI\.?o\.?W\b|wightlink|red funnel|hovertravel|\bventnor\b|\bshanklin\b|\bsandown\b(?! park)|\bryde\b|\bcowes\b|"
                    r"robin hill|blackgang|the needles (?:landmark|attraction|park)|osborne house|tapnell|monkey haven|garlic farm|\bbembridge\b|"
                    r"\bgodshill\b|\bseaview hotel|\bwight\b|\bislanders?\b.*\bwight)", re.I)

def is_iow(it):
    return bool(IOW_RX.search(" ".join([it.get("title") or "", it.get("prize_desc") or "", it.get("promoter") or "", it.get("link") or ""])))

CP = "https://www.countypress.co.uk"

def _newsquest(ctx, base, paper, tag):
    r = ctx.get(base + "/competitions/")
    if not r: return []
    out = []
    for card in soup(r).select(".omnicompetitioncard"):
        a = card.select_one('a[href*="/competitions/"]'); h3 = card.select_one("h3")
        if not a or not h3: continue
        link = a["href"] if a["href"].startswith("http") else base + a["href"]
        title = clean(h3.get_text()); desc = clean((card.select_one(".metadata-container p") or h3).get_text())
        ban = clean((card.select_one(".banner") or card).get_text())
        cl = closing_from_text(ban) if "closing" in ban.lower() else None
        out.append(rec(title=title, promoter="Newsquest Media Group", link=link, prize_desc=desc, prize_value=prize_value_from_text(title + " " + desc),
                       entry_type="free", entry_note=f"{paper} competition (Newsquest; UK residents 18+).",
                       closes_at=cl[0] if cl else None, closes_precision=cl[1] if cl else "", skey=link, image=img_url(card, base + "/"), tags=[tag]))
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
                     entry_note=f"{paper} digital subscribers only (subscription needed to enter).")
    return [o for o in out if not o["closes_at"] or o["closes_at"] > now()]

@source("Isle of Wight County Press", "publisher", CP + "/competitions/",
        "The Island's newspaper (Newsquest). Its competitions page; many are open to digital subscribers only (flagged as paid entry).", direct=True)
def county_press(ctx):
    return _newsquest(ctx, CP, "Isle of Wight County Press", "iow")

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


# ================================================================ Hampshire (UK, tagged 'hampshire')
HANTS_RX = re.compile(r"(hampshire|\bhants\b|southampton|portsmouth|winchester|basingstoke|andover|\bromsey\b|new forest|lymington|\bfareham\b|"
                      r"\bgosport\b|\beastleigh\b|\bhavant\b|\bpetersfield\b|\balton\b(?![\s-]towers)|\bfleet\b,? hants|\bringwood\b|\bbrockenhurst\b|"
                      r"paultons|peppa pig world|marwell|beaulieu|spinnaker tower|historic dockyard|mary rose|exbury|mayflower theatre|"
                      r"wave 105|radio solent|st mary'?s stadium|fratton park|\bthe saints\b|pompey\b)", re.I)

def is_hants(it):
    return bool(HANTS_RX.search(" ".join([it.get("title") or "", it.get("prize_desc") or "", it.get("promoter") or "", it.get("link") or ""])))

NQ_HANTS = [("https://www.dailyecho.co.uk", "Southern Daily Echo"), ("https://www.hampshirechronicle.co.uk", "Hampshire Chronicle"),
            ("https://www.basingstokegazette.co.uk", "Basingstoke Gazette"), ("https://www.andoveradvertiser.co.uk", "Andover Advertiser"),
            ("https://www.romseyadvertiser.co.uk", "Romsey Advertiser")]

@source("Hampshire newspapers (Daily Echo, Hampshire Chronicle, Basingstoke Gazette, Andover & Romsey Advertiser)", "publisher",
        "https://www.dailyecho.co.uk/competitions/",
        "Newsquest's Hampshire titles share one competitions system (often the same network-wide prizes; merged as duplicates). "
        "Many are digital-subscriber only. The News Portsmouth has no public competitions page.", direct=True)
def hants_papers(ctx):
    out = []
    byid = {}
    for base, paper in NQ_HANTS:
        got = _newsquest(ctx, base, paper, "hampshire"); ctx.meta[paper.split()[0].lower()] = len(got)
        for o in got:      # the papers share one system: competition 227 on the Echo is competition 227 on the Chronicle
            cid = re.search(r"/competitions/(\d+)\.", o["link"]); k = cid.group(1) if cid else o["link"]
            if k in byid: byid[k]["entry_note"] += f" Also on {paper}."
            else: byid[k] = o
    return list(byid.values())

@source("Hampshire: Visit Hampshire & Hampshire Life", "publisher", "https://www.visit-hampshire.co.uk/visitor-information/competitions",
        "Visit Hampshire (official tourism site) competitions and Hampshire Life magazine giveaways ('Win …' articles).", direct=True, allow_empty=True)
def hants_tourism(ctx):
    out = []
    r = ctx.get("https://www.visit-hampshire.co.uk/visitor-information/competitions")
    if r:
        seen = set()
        for a in soup(r).select('a[href*="/visitor-information/competitions/"]'):
            t = clean(a.get_text()); h = a["href"]
            if not WIN.search(t) or h in seen: continue
            seen.add(h); link = h if h.startswith("http") else "https://www.visit-hampshire.co.uk" + h
            out.append(rec(title=t, promoter="Visit Hampshire", link=link, prize_desc=t, prize_value=prize_value_from_text(t), entry_type="free",
                           entry_note="Visit Hampshire (official tourism site) competition.", skey=link, tags=["hampshire"]))
        ctx.meta["visit_hampshire"] = len(seen)
    r = ctx.get("https://www.hampshire-life.co.uk/competitions/")
    if r:
        seen = set()
        for a in soup(r).select("a[href]"):
            t = clean(a.get_text()); h = a["href"]
            if not re.search(r"/\d+\.win-", h): continue
            if len(t) < 12:      # image/short link: title from the slug
                t = "Win " + re.sub(r"^\d+\.win-", "", h.rstrip("/").rsplit("/", 1)[-1]).replace("-", " ")
            if not WIN.search(t) or h in seen: continue
            seen.add(h); link = h if h.startswith("http") else "https://www.hampshire-life.co.uk" + h
            out.append(rec(title=t, promoter="Hampshire Life", link=link, prize_desc=t, prize_value=prize_value_from_text(t), entry_type="free",
                           entry_note="Hampshire Life magazine giveaway; closing date in the article.", skey=link, tags=["hampshire"]))
        ctx.meta["hampshire_life"] = len(seen)
    dates = detail_closing(ctx, [o["link"] for o in out], ctx.cap("hants_detail", 15))
    keep = []
    for o in out:
        d = dates.get(o["link"])
        if d:
            if d[0] < now(): continue
            o["closes_at"], o["closes_precision"] = d
        keep.append(o)
    return keep

GHRSC = "https://www.hellorayo.co.uk/greatest-hits/south-coast/win"

@source("Radio: Greatest Hits Radio South Coast (formerly Wave 105)", "radio", GHRSC,
        "Bauer's Hampshire/Dorset station; its public win page (Bauer competition terms apply). Heart South / Capital South have no "
        "separate public win page (Global's national pages are already collected); BBC Radio Solent lists no competitions.", direct=True, allow_empty=True)
def ghr_south_coast(ctx):
    r = ctx.get(GHRSC)
    if not r: return []
    out = []; seen = set()
    for a in soup(r).select('a[href*="/greatest-hits/south-coast/win/"]'):
        t = clean(a.get_text()); h = a["href"]
        if not t or not WIN.search(t) or h in seen: continue
        seen.add(h); link = h if h.startswith("http") else "https://www.hellorayo.co.uk" + h
        out.append(rec(title=t, promoter="Greatest Hits Radio South Coast", link=link, prize_desc=t, prize_value=prize_value_from_text(t),
                       entry_type="free", entry_note="Bauer radio competition (Bauer competition terms).", station="Greatest Hits Radio South Coast",
                       skey=link, tags=["radio", "hampshire"]))
    return out

# ================================================================ Bauer regional stations (Hits Radio / Greatest Hits Radio areas)
BAUER_REGIONS = [("hits-radio", "Hits Radio", r) for r in ("manchester", "birmingham", "liverpool", "coventry", "east-midlands", "lancashire",
                 "staffordshire", "teesside", "bristol", "oxfordshire", "cambridgeshire", "south-coast")] + \
                [("greatest-hits", "Greatest Hits Radio", r) for r in ("manchester", "lancashire", "west-midlands", "north-east", "teesside",
                 "bristol", "kent", "oxfordshire", "cambridgeshire", "glasgow", "edinburgh")]

MONTHS = ["january","february","march","april","may","june","july","august","september","october","november","december"]

def _region_name(r): return r.replace("-", " ").title()

@source("Radio: Bauer regional stations (Hits Radio & Greatest Hits Radio areas)", "radio", "https://www.hellorayo.co.uk/hits-radio/manchester/win",
        "Bauer's regional win pages (23 areas, e.g. Hits Radio Manchester, Greatest Hits Radio Kent/Glasgow); local prizes not on the national pages. "
        "Greatest Hits Radio South Coast is its own source (Hampshire).", direct=True, allow_empty=True)
def radio_bauer_regional(ctx):
    byslug = {}
    for brand, bname, reg in BAUER_REGIONS:
        base = f"https://www.hellorayo.co.uk/{brand}/{reg}/win"
        r = ctx.get(base)
        if not r: continue
        for a in soup(r).select(f'a[href*="/{brand}/{reg}/win/"]'):
            h = a["href"]; m = re.search(r"/win/([a-z0-9-]+)", h)
            t = clean(a.get_text())
            if not m: continue
            if len(t) < 8: t = m.group(1).replace("-", " ").replace("pound", "£").capitalize()
            if not WIN.search(t) or re.search(r"(terms|t-cs|ts-and-cs|privacy)", h): continue
            my = re.search(r"(" + "|".join(MONTHS) + r")-?(20\d\d)", m.group(1))
            if my and (int(my.group(2)), MONTHS.index(my.group(1)) + 1) < (now().year, now().month): continue   # e.g. '...-june2026-sponsored'
            st = f"{bname} {_region_name(reg)}"
            c = byslug.setdefault(m.group(1), dict(t=t, link=h if h.startswith("http") else "https://www.hellorayo.co.uk" + h, st=[], reg=[]))
            if st not in c["st"]: c["st"].append(st); c["reg"].append(_region_name(reg))
    out = []
    for cs, c in byslug.items():
        if "/greatest-hits/south-coast/" in c["link"]: continue
        tags = ["radio"] + (["hampshire"] if "South Coast" in c["reg"] else [])
        out.append(rec(title=c["t"], promoter=c["st"][0], link=c["link"], prize_desc=c["t"], prize_value=prize_value_from_text(c["t"]),
                       entry_type="free", entry_note="Bauer regional radio competition (Bauer competition terms); region: " + ", ".join(c["reg"]) + ".",
                       station=", ".join(c["st"][:4]), skey=c["link"], tags=tags))
    ctx.meta["regional_comps"] = len(out)
    return out

# ================================================================ Metro Competitions (DMG's paid prize draws, linked from metro.co.uk)
MC = "https://metrocompetitions.com"

@source("Metro Competitions", "operator", MC + "/competitions",
        "Metro's own prize-draw site (DMG Media), linked from metro.co.uk/competitions: paid tickets (typically 10p-£1) with a free postal entry route.", direct=True)
def metro_comps(ctx):
    r = ctx.get(MC + "/competitions")
    if not r: return []
    out = []; seen = set()
    for a in soup(r).select('a[href^="/competitions/"]'):
        h = a["href"]
        if h.count("/") < 3 or h in seen: continue
        h3 = a.select_one("h3")
        if not h3: continue
        seen.add(h); t = clean(h3.get_text()); sub = a.select_one("h3 + p"); sub = clean(sub.get_text()) if sub else ""
        txt = clean(a.get_text(" "))
        pm = re.search(r"(£\s?\d+(?:\.\d\d)?|\d+p)\s*per ticket", txt)
        cost = None
        if pm:
            v = pm.group(1).replace(" ", ""); cost = float(v[1:]) if v.startswith("£") else int(v[:-1]) / 100
        pct = re.search(r"(\d{1,3})\s*%\s*sold", txt)
        title = t + (f" ({sub})" if sub else "")
        out.append(rec(title="Win " + title if not t.lower().startswith("win") else title, promoter="Metro Competitions (DMG Media)",
                       link=MC + h, prize_desc=title, prize_value=prize_value_from_text(title), entry_type="paid", entry_cost=cost,
                       entry_cost_text=(pm.group(1) + " per ticket") if pm else "", pct_sold=int(pct.group(1)) if pct else None,
                       entry_note="Paid prize draw" + ("; free postal entry available" if "postal" in txt.lower() else "") + ".",
                       image=img_url(a, MC), skey=MC + h))
    return out

# ================================================================ London
LONDON_RX = re.compile(r"\blondon\b(?![\s-](?:road|street|colney|ontario))|\b(westminster|camden|islington|hackney|tower hamlets|southwark|lambeth|"
    r"wandsworth|hammersmith|fulham|kensington|chelsea|greenwich|lewisham|croydon|bromley|barnet|enfield|haringey|brent|ealing|hounslow|"
    r"richmond upon thames|kingston upon thames|merton|sutton|harrow|hillingdon|newham|redbridge|havering|bexley|barking|dagenham|waltham forest|"
    r"shoreditch|soho|covent garden|mayfair|notting hill|brixton|stratford|canary wharf|wimbledon|wembley|twickenham|west end|"
    r"the o2|o2 arena|southbank centre|barbican|royal albert hall|alexandra palace|ally pally|hyde park|regent'?s park|kew gardens|"
    r"tower of london|london eye|sea life london|madame tussauds|zsl|london zoo|natural history museum|science museum|v&a|tate modern|"
    r"british museum|shakespeare'?s globe|lyceum theatre|palladium|drury lane|sadler'?s wells|old vic|young vic|national theatre|"
    r"abba voyage|harry potter studios?|warner bros\.? studio tour|winter wonderland|ovo arena|copper box|olympia london|excel london)\b", re.I)

def is_london(it):
    t = " ".join([it.get("title") or "", it.get("prize_desc") or "", it.get("promoter") or ""])
    return bool(LONDON_RX.search(t)) and not re.search(r"\bnew london\b|\blondon,? (ontario|ohio|kentucky)\b", t, re.I)

def _reach(ctx, base, paper, tag, out, recent, metakey):
    """Reach plc local paper 'competitions' topic page: only articles published in the last 45 days (date from the article)."""
    r = ctx.get(base + "/all-about/competitions")
    if r:
        ss = soup(r); seen = {}
        for a in ss.find_all("a", href=True):
            h = a["href"]; m = re.search(r"-(\d{8})$", h)
            if not m or h in seen: continue
            slug = h.rstrip("/").rsplit("/", 1)[-1]
            if not re.search(r"(^win-|competition|giveaway|chance-win|could-win)", slug): continue
            seen[h] = int(m.group(1))
        fetched = 0; cutoff = now() - timedelta(days=45)
        for h, n in sorted(seen.items(), key=lambda x: -x[1]):
            link = h if h.startswith("http") else base + h
            c = ctx.cache_get("mlpub:" + link)
            if c is None:
                if fetched >= ctx.cap(metakey + "_detail", 20): continue
                fetched += 1; rr = ctx.get(link)
                if not rr: continue
                html = rr.text or ""
                tm = re.search(r"<title>(.*?)</title>", html, re.S); pm = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
                c = dict(t=clean(re.sub(r"\s+-\s+[^-]{2,40}$", "", tm.group(1))) if tm else "", pub=pm.group(1) if pm else "")
                ctx.cache_put("mlpub:" + link, c)
            try: pub = datetime.fromisoformat(c["pub"].replace("Z", "+00:00"))
            except Exception: continue
            if pub < cutoff: continue                       # older articles: the giveaway has almost always closed
            t = c.get("t") or ("Win " + re.sub(r"^win-", "", re.sub(r"-\d{8}$", "", link.rsplit("/", 1)[-1])).replace("-", " "))
            recent.add(link)
            out.append(rec(title=t, promoter=paper + " (Reach plc)", link=link, prize_desc=t, entry_type="free",
                           entry_note=paper + " giveaway; closing date and terms in the article.", skey=link, tags=[tag]))
        ctx.meta[metakey] = len(seen)

@source("London local (MyLondon, Secret London)", "publisher", "https://www.mylondon.news/all-about/competitions",
        "London giveaways from MyLondon (Reach) and Secret London; only articles with a future closing date in the text, or published in the "
        "last 45 days. Time Out London (no current competitions), Evening Standard (no competitions page) and Londonist (no tag page) list none.",
        direct=True, allow_empty=True)
def london_local(ctx):
    out = []; recent = set()
    _reach(ctx, "https://www.mylondon.news", "MyLondon", "london", out, recent, "mylondon")
    after = (now() - timedelta(days=45)).strftime("%Y-%m-%dT00:00:00")
    r = ctx.get(f"https://secretldn.com/wp-json/wp/v2/posts?search=win&after={after}&per_page=50&_fields=link,title,date")
    if r:
        try: posts = r.json()
        except Exception: posts = []
        n_sl = 0
        for p in posts:
            link = p.get("link") or ""; t = clean(re.sub(r"<[^>]+>", "", (p.get("title") or {}).get("rendered", "")))
            if re.search(r"secretldn\.com/[a-z]{2}/", link) or not WIN.search(t): continue
            n_sl += 1; recent.add(link)
            out.append(rec(title=t, promoter="Secret London", link=link, prize_desc=t, prize_value=prize_value_from_text(t), entry_type="free",
                           entry_note="Secret London giveaway; closing date in the article.", skey=link, tags=["london"]))
        ctx.meta["secret_london"] = n_sl
    dates = detail_closing(ctx, [o["link"] for o in out], ctx.cap("london_detail", 25))
    keep = []
    for o in out:
        d = dates.get(o["link"])
        if d:
            if d[0] < now(): continue
            o["closes_at"], o["closes_precision"] = d
        elif o["link"] not in recent: continue       # old article with no stated closing date: most likely finished
        o["prize_value"] = o["prize_value"] or prize_value_from_text(o["title"])
        keep.append(o)
    return keep

# ================================================================ Birmingham / West Midlands
BRUM_RX = re.compile(r"\b(birmingham|brum|west midlands|solihull|sutton coldfield|wolverhampton|coventry|dudley|walsall|west bromwich|"
    r"sandwell|smethwick|halesowen|stourbridge|bournville|edgbaston|digbeth|selly oak|erdington|kings heath|moseley|harborne|"
    r"\bnec\b|utilita arena|bp pulse live|resorts world (?:arena|birmingham)|birmingham hippodrome|symphony hall|town hall birmingham|b:music|"
    r"cadbury world|drayton manor|sea ?life birmingham|national sea life centre|bullring|grand central birmingham|mailbox birmingham|"
    r"villa park|st andrews|the hawthorns|molineux|coventry building society arena|black country living museum|thinktank|"
    r"legoland discovery centre birmingham|alexandra theatre|the alexandra birmingham|o2 academy birmingham|warwick castle)\b", re.I)

def is_brum(it):
    t = " ".join([it.get("title") or "", it.get("prize_desc") or "", it.get("promoter") or "", it.get("station") or ""])
    return bool(BRUM_RX.search(t)) and not re.search(r"\bbirmingham,? (alabama|al|michigan)\b", t, re.I)

@source("Birmingham & West Midlands local (Birmingham Live, Coventry Live)", "publisher", "https://www.birminghammail.co.uk/all-about/competitions",
        "Reach's Birmingham Mail / Birmingham Live and Coventry Telegraph / Coventry Live giveaways; only articles from the last 45 days "
        "(or with a future closing date). Express & Star and Birmingham World have no competitions page; Hits Radio Birmingham and "
        "Greatest Hits Radio West Midlands come from the Bauer regional source.", direct=True, allow_empty=True)
def brum_local(ctx):
    out = []; recent = set()
    _reach(ctx, "https://www.birminghammail.co.uk", "Birmingham Live", "birmingham", out, recent, "birmingham_live")
    _reach(ctx, "https://www.coventrytelegraph.net", "Coventry Live", "birmingham", out, recent, "coventry_live")
    dates = detail_closing(ctx, [o["link"] for o in out], ctx.cap("brum_detail", 25))
    keep = []
    for o in out:
        d = dates.get(o["link"])
        if d:
            if d[0] < now(): continue
            o["closes_at"], o["closes_precision"] = d
        o["prize_value"] = o["prize_value"] or prize_value_from_text(o["title"])
        keep.append(o)
    return keep
