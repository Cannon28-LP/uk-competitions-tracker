"""Festival & event-ticket sources (Oct 2026): publishers / a community radio station that regularly give away festival, gig,
theatre, show and days-out tickets on their OWN public pages (robots.txt allow, no login, no social/Gleam entry).
Each entry is kept only when its own page states a future closing date (util.closing_from_text via detail_closing).
Checked and NOT added: Time Out London (competitions page empty), Kerrang! (only years-old posts, no dates), Louder Than War
(HTTP 403 to automated requests), Marie Claire comps platform (account login needed to enter), festivals' own sites
(IoW Festival, Boomtown, Victorious, Camp Bestival, Download: giveaways run on social media or via partners only)."""
import re
from .sources import source, rec, soup, clean, img_url, detail_closing
from .util import now, prize_value_from_text

WINRX = re.compile(r"\bwin\b|giveaway|competition", re.I)

def _collect(ctx, base, pages, href_rx, promoter, note, cap_key, cap, tags=None, region_tags=None, title_from=None):
    """Generic magazine listing -> 'Win …' links -> keep those whose own page states a future closing date."""
    out, seen = [], set()
    for path in pages:
        r = ctx.get(base + path)
        if not r: continue
        for a in soup(r).select("a[href]"):
            h = a["href"].split("?")[0].split("#")[0]
            link = h if h.startswith("http") else base + h
            if not re.search(href_rx, link) or link in seen: continue
            title = clean(a.get_text(" "))
            title = re.sub(r"^(?:LATEST|News)\s+|\s*(?:\.\.\.\s*)?READ MORE$", "", title, flags=re.I)
            if len(title) < 12 or not WINRX.search(title): continue
            seen.add(link)
            tg = list(tags or []) + list((region_tags or {}).get(path, []))
            out.append(rec(title=title[:200], promoter=promoter, link=link, prize_desc=title, prize_value=prize_value_from_text(title),
                           entry_type="free", entry_cost=0, entry_cost_text="FREE", entry_note=note, skey=link,
                           image=img_url(a.parent or a, base + "/"), tags=tg or None))
    dates = detail_closing(ctx, [o["link"] for o in out], ctx.cap(cap_key, cap))
    keep = []
    for o in out:
        d = dates.get(o["link"])
        if d and d[0] >= now():
            o["closes_at"], o["closes_precision"] = d; keep.append(o)
    return keep

# ---------------------------------------------------------------- Primary Times (family events, festivals, days out, panto)
PT = "https://www.primarytimes.co.uk"
PT_REGIONS = ["hampshire", "dorset", "sussex", "kent", "essex", "oxfordshire", "devon", "cornwall", "birmingham", "edinburgh", "glasgow"]

@source("Primary Times (family events & days out)", "publisher", PT + "/competitions",
        "Primary Times Ltd (Co. no. 09512881): family what's-on magazine with national + regional (incl. Hampshire) competitions pages; "
        "lots of family festival, panto and attraction tickets. Online form; terms and closing date on each page.", direct=True, allow_empty=True)
def primary_times(ctx):
    pages = ["/competitions"] + [f"/{r}/competitions" for r in PT_REGIONS]
    rt = {"/hampshire/competitions": ["hampshire"]}
    return _collect(ctx, PT, pages, r"primarytimes\.co\.uk/(?:[a-z-]+/)?competitions/20\d\d/\d\d/\d+-", "Primary Times",
                    "Free family-magazine competition (online form; UK residents; Primary Times terms on the page).", "pt_detail", 30, region_tags=rt)

# ---------------------------------------------------------------- Express FM (Portsmouth community radio)
EFM = "https://www.expressfm.com"

@source("Radio: Express FM (Portsmouth)", "radio", EFM + "/win/",
        "Express FM (Portsmouth) Ltd (Co. no. 05265112), Portsmouth's community radio station; its public /win/ page (local gig, theatre, "
        "Guildhall, light-show and Pompey tickets). Entry by web form; most comps are limited to PO postcodes. robots.txt crawl-delay 8.",
        direct=True, allow_empty=True)
def express_fm(ctx):
    out = _collect(ctx, EFM, ["/win/"], r"expressfm\.com/win/[a-z0-9-]+/?$", "Express FM (Portsmouth)",
                   "Express FM competition: free web-form entry (an optional text route costs your standard network rate). "
                   "18+, usually PO-postcode residents only.", "efm_detail", 8, tags=["radio", "hampshire"])
    for o in out: o["station"] = "Express FM"
    return out

# ---------------------------------------------------------------- Oracle (Southend / Essex events)
ORA = "https://oraclepublications.co.uk"

@source("Oracle Publications (Southend & Essex)", "publisher", ORA + "/competitions/",
        "Oracle Publications (UK) Ltd (Co. no. 06612831), Southend's free community magazine; regular gig, tribute-show, theatre and "
        "attraction ticket giveaways (online form, UK 18+).", direct=True, allow_empty=True)
def oracle(ctx):
    return _collect(ctx, ORA, ["/competitions/", "/category/competitions/"], r"oraclepublications\.co\.uk/competitions/[a-z0-9-]+/?$",
                    "Oracle Publications", "Free local-magazine competition (online form; UK residents 18+; terms on the page).", "ora_detail", 12)

# ---------------------------------------------------------------- Resident Magazine (Hampshire / Surrey / Sussex lifestyle)
RES = "https://residentmagazine.co.uk"

@source("Resident Magazine (Hampshire & South)", "publisher", RES + "/category/competitions/",
        "Independent south-of-England lifestyle magazine; event / festival / comedy ticket giveaways with an on-page form. "
        "Publisher company not shown on the site, so these are not brand-verified.", direct=True, allow_empty=True)
def resident(ctx):
    return _collect(ctx, RES, ["/category/competitions/"], r"residentmagazine\.co\.uk/win-[a-z0-9-]+/?$", "Resident Magazine",
                    "Free magazine competition (answer a question on the page's form).", "res_detail", 12)

# ---------------------------------------------------------------- Classic Pop (Anthem Publishing)
CPOP = "https://www.classicpopmag.com"

@source("Classic Pop magazine (Anthem Publishing)", "publisher", CPOP + "/competitions/",
        "Anthem Publishing Ltd (Co. no. 04542063) music magazine; gig / weekender-festival tickets as well as vinyl & box sets. "
        "Full T&Cs on Anthem's site.", direct=True, allow_empty=True)
def classic_pop(ctx):
    return _collect(ctx, CPOP, ["/competitions/"], r"classicpopmag\.com/competitions/[a-z0-9-]+/?$", "Classic Pop (Anthem Publishing)",
                    "Free music-magazine competition (answer + details on the page form; UK 18+, one entry each).", "cpop_detail", 12)

# ---------------------------------------------------------------- Red Funnel (Isle of Wight ferry) event competitions
RF = "https://www.redfunnel.co.uk"

@source("Red Funnel competitions (Isle of Wight events)", "operator", RF + "/sitemap.xml",
        "Red Funnel Ltd (Co. no. 10823670, Southampton): the Isle of Wight ferry runs free prize draws on standalone pages of its own site "
        "(IoW festival / event tickets + ferry travel, Southampton Boat Show…). Found via its public sitemap (robots allow); kept only "
        "while the page's form is open and it states a future closing date.", direct=True, allow_empty=True)
def red_funnel(ctx):
    r = ctx.get(RF + "/sitemap.xml")
    if not r: return []
    urls = sorted(set(u for u in re.findall(r"<loc>([^<]+)</loc>", r.text) if re.search(r"compet", u, re.I)))
    out = []
    for u in urls[:12]:
        c = ctx.cache_get("rf:" + u)
        if c is None or (ctx.cache_age_hours("rf:" + u) or 0) > 24:
            rr = ctx.get(u)
            if not rr: continue
            ss = soup(rr)
            h1 = ss.select_one("h1")
            for x in ss(["script", "style", "noscript"]): x.decompose()
            t = clean(ss.get_text(" "))
            from .util import closing_from_text
            cl = closing_from_text(t)
            c = {"title": clean(h1.get_text()) if h1 else "", "closed": bool(re.search(r"form is closed|competition closed", t, re.I)),
                 "closes": cl[0].isoformat() if cl else None, "prec": cl[1] if cl else ""}
            ctx.cache_put("rf:" + u, c)
        if c["closed"] or not c.get("closes"): continue
        from datetime import datetime
        cl = datetime.fromisoformat(c["closes"])
        if cl < now(): continue
        title = c["title"] or u.rsplit("/", 1)[-1].replace("-", " ")
        if not re.search(r"\bwin\b", title, re.I): title = "Win: " + title
        out.append(rec(title=title, promoter="Red Funnel", link=u, prize_desc=title, prize_value=prize_value_from_text(title),
                       entry_type="free", entry_cost=0, entry_cost_text="FREE", closes_at=cl, closes_precision=c["prec"] or "date",
                       entry_note="Free Red Funnel prize draw (online form; UK residents 18+, one entry each; Red Funnel T&Cs).",
                       skey=u, tags=["iow", "hampshire"]))
    return out
