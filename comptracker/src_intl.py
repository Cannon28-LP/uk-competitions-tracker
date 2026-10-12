"""Sources for countries other than the UK (pluggable, one @source per site; `country=` picks the collector run).
Same rules as the UK sources: public listing pages only, robots.txt respected by the Fetcher, polite per-host delay,
no logins, capped page counts, no fetching of outbound redirect (/go, /goto, /exit) URLs."""
import re, csv, io, urllib.parse
from datetime import datetime, timedelta
from .sources import source, rec, soup, clean, img_url, approx_from_left, detail_closing
from . import util
from .util import now, money, prize_value_from_text, dmy, infer_year, local_named_date, closing_from_text, MONTHS

def _abs(base, href):
    return urllib.parse.urljoin(base, href or "")

def _pages(ctx, urls):
    """Fetch listing pages in order; stops at the first failure. A 404 on a later page just means 'no more pages'
    (not an error), so the source isn't reported as partial when a site has fewer pages than our cap."""
    for i, u in enumerate(urls):
        if i == 0:
            r = ctx.get(u)
        else:
            n0 = len(ctx.f.errors)
            r = ctx.f.get(u) if not (ctx.deadline and __import__("time").time() > ctx.deadline) else None
            if r is None:
                new = ctx.f.errors[n0:]
                if all(e.startswith(("HTTP 404", "HTTP 410")) for e in new):
                    del ctx.f.errors[n0:]; ctx.meta["last_page"] = i; return
                ctx.errors.extend(new)
        if not r: return
        yield u, soup(r)

def _title_case_win(t):
    return clean(t).strip(" -–:|")

def _left_to_date(txt):
    """'2 weeks left' / '4 days left' / 'Ends in 2 Days' / 'Ends Today' -> approx datetime"""
    t = (txt or "").lower()
    m = re.search(r"(\d+)\s*weeks?", t)
    if m: return now() + timedelta(days=7 * int(m.group(1)))
    m = re.search(r"(\d+)\s*months?", t)
    if m: return now() + timedelta(days=30 * int(m.group(1)))
    if re.search(r"\btoday\b|\bheute\b", t): return now().replace(hour=23, minute=59, second=0, microsecond=0)
    if re.search(r"\btomorrow\b|\bdemain\b|\bmorgen\b", t): return (now() + timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
    if re.search(r"\d+\s*(?:days?|d|hours?|hrs?|h)\b|\d+:\d\d", t): return approx_from_left(t)
    return None

# ================================================================== Germany
G12 = "https://www.12gewinn.de"

@source("12Gewinn.de", "aggregator", G12 + "/gewinnspiele", "German Gewinnspiel directory (first pages of the full list + newest).", country="de")
def de_12gewinn(ctx):
    out = []
    pages = ctx.cap("de12_pages", 15)
    urls = [G12 + "/neue-gewinnspiele", G12 + "/neue-gewinnspiele?seite=2", G12 + "/gewinnspiele"] + [G12 + f"/gewinnspiele?seite={i}" for i in range(2, pages + 1)]
    for u, s in _pages(ctx, urls):
        cards = s.select("article.contest-row")
        if not cards: break
        for a in cards:
            h = a.select_one("h2 a, h3 a")
            if not h: continue
            meta = {clean(d.select_one("dt").get_text()): d.select_one("dd") for d in a.select("dl.contest-meta > div") if d.select_one("dt") and d.select_one("dd")}
            prizes = [clean(li.get_text(" ")) for li in a.select("ul.contest-row__prizes li")]
            promoter = clean(meta["Veranstalter"].get_text(" ")) if "Veranstalter" in meta else ""
            val = money(clean(meta["Gewinnwert"].get_text(" "))) if "Gewinnwert" in meta else None
            closes = None
            if "Einsendeschluss" in meta:
                tm = meta["Einsendeschluss"].select_one("time[datetime]")
                closes = dmy(tm["datetime"] if tm else meta["Einsendeschluss"].get_text(" "))
            out.append(rec(title=clean(h.get_text(" ")), promoter=promoter, link=_abs(G12, h.get("href")),
                           prize_desc="; ".join(prizes)[:400] or clean(h.get_text(" ")), prize_value=val, entry_type="free",
                           closes_at=closes, closes_precision="date" if closes else "",
                           entry_note=("Main prize: " + clean(meta["Hauptgewinn"].get_text(" "))) if "Hauptgewinn" in meta else ""))
    return out

GH = "https://www.gewinnhai.de"

@source("GewinnHai", "aggregator", GH + "/gewinnspiele", "German Gewinnspiel directory (all listed pages, capped).", country="de")
def de_gewinnhai(ctx):
    out = []
    pages = ctx.cap("gh_pages", 40)
    urls = [GH + "/gewinnspiele"] + [GH + f"/gewinnspiele?page={i}" for i in range(2, pages + 1)]
    for u, s in _pages(ctx, urls):
        cards = s.select("article.card.item")
        if not cards: break
        for a in cards:
            h = a.select_one("h3.item-title")
            link = a.select_one("a.cta-btn[href]")
            if not h or not link: continue
            for r_ in h.select(".rank"): r_.decompose()
            meta = {clean(d.select_one("dt").get_text()): clean(d.select_one("dd").get_text(" ")) for d in a.select("dl.item-meta > div") if d.select_one("dt") and d.select_one("dd")}
            prizes = meta.get("Gewinne", "")
            pool = money(meta.get("Gewinnsumme", ""))
            title = clean(h.get_text(" "))
            # 'Gewinnsumme' is the whole prize pool; use it as the prize value only for a single-prize listing
            single = prizes and "·" not in prizes and not re.search(r"\b\d+\s*[x×]", prizes) and "weitere" not in prizes
            val = prize_value_from_text(title) or (pool if single else None)
            closes = dmy(meta.get("Enddatum", ""))
            img = img_url(a, GH)
            if "/assets/thumbs/" in img: img = ""     # generic category icons, not the prize
            out.append(rec(title=title, promoter=meta.get("Veranstalter", ""), link=_abs(GH, link["href"]), prize_desc=prizes[:400] or title,
                           prize_value=val, entry_type="free", closes_at=closes, closes_precision="date" if closes else "", image=img,
                           entry_note=(f"Total prize pool {pool:,.0f} €".replace(",", ".") if pool and not single else "")))
    return out

# ================================================================== France
JCB = "https://www.jeu-concours.biz"

def _jcb_cards(s, base):
    out = []
    for a in s.select("article.bloc-concours"):
        if "cloture" in (a.get("class") or []): continue
        org = a.select_one("a.concours-title-link")
        end = a.select_one("a.concours-end-link[href]")
        closes = None
        if end:
            m = re.search(r"(\d{2})-(\d{2})-(20\d\d)", end["href"])
            if m: closes = dmy(f"{m.group(1)}/{m.group(2)}/{m.group(3)}")
        cad = a.select_one(".concours-cadeaux")
        lots = [clean(x) for x in re.split(r"•", cad.get_text("\n")) if clean(x)] if cad else []
        if not org or not lots: continue
        principe = clean((a.select_one(".concours-principe") or a).get_text(" "))[:300] if a.select_one(".concours-principe") else ""
        pictos = [li.get("title", "") for li in a.select("ul.picto-bulle li[title]")]
        link = ""
        for x in a.select("a[href]"):
            if re.match(r"(?:/)?20\d\d/\d\d/\d\d/", x["href"]): link = _abs(base, x["href"]); break
        if not link:
            x = a.select_one("a.participate[href]"); link = _abs(base, x["href"]) if x else ""
        first = re.sub(r"\s*\|?\s*valeur\s.*$", "", lots[0], flags=re.I)
        purchase = any(re.search(r"achat", p, re.I) for p in pictos) or bool(re.search(r"obligation d'achat|preuve d'achat|ticket de caisse", principe, re.I))
        out.append(rec(title=f"{clean(org.get_text())} – {first}"[:160], promoter=clean(org.get_text()), link=link,
                       prize_desc=" • ".join(lots)[:500], prize_value=prize_value_from_text(" ".join(lots)), entry_type="free",
                       closes_at=closes, closes_precision="date" if closes else "",
                       entry_note="; ".join(x for x in [", ".join(pictos), principe, "Purchase required" if purchase else ""] if x)[:400],
                       tags=["purchase"] if purchase else None))
    return out

@source("Jeu-concours.biz", "aggregator", JCB + "/nouveaux-concours.html", "French jeux-concours directory (newest + closing soon).", country="fr")
def fr_jcb(ctx):
    out = []
    pages = ctx.cap("jcb_pages", 8)
    urls = [JCB + "/nouveaux-concours.html"] + [JCB + f"/nouveaux-concours.html?page={i}" for i in range(2, pages + 1)] + [JCB + "/concours-bientot-clos.html"]
    for u, s in _pages(ctx, urls):
        got = _jcb_cards(s, JCB + "/")
        out.extend(got)
    return out

CDN = "https://www.concours-du-net.com"

@source("Concours du Net", "aggregator", CDN + "/nouveaux-concours", "French jeux-concours directory (today's new + last chance).", country="fr")
def fr_cdn(ctx):
    out = []
    pages = ctx.cap("cdn_pages", 7)
    urls = [CDN + "/nouveaux-concours"] + [CDN + f"/nouveaux-concours?page={i}" for i in range(2, pages + 1)] + [CDN + "/derniere-chance"]
    for u, s in _pages(ctx, urls):
        cards = s.select("article.concours-card")
        if not cards: continue
        for a in cards:
            txt = clean(a.get_text(" | "))
            link = a.select_one('a[href^="/jeu-concours-"]')
            m = re.search(r"Lots à gagner[\s|]+(.+?)[\s|]+(?:Principe|Réponses|Publié)", txt)
            if not link or not m: continue
            oa = a.select_one('a[href^="/concours-organisateur-"]')
            org = clean(oa.get_text(" ")) if oa else clean(txt.strip(" |").split("|")[0])
            lots = re.sub(r"\s*\|\s*", " ", m.group(1)).strip(" |")
            pm = re.search(r"Principe \| (.+?) \| (?:Réponses|Publié)", txt)
            fm = re.search(r"Fin le (\d{2}/\d{2}/20\d\d)", txt)
            closes = dmy(fm.group(1)) if fm else None
            purchase = bool(re.search(r"obligation d'achat|achat obligatoire|preuve d'achat", txt, re.I))
            out.append(rec(title=f"{org} – {lots}"[:160].rstrip(". "), promoter=org, link=_abs(CDN, link["href"]), prize_desc=lots[:500],
                           prize_value=prize_value_from_text(lots), entry_type="free", closes_at=closes, closes_precision="date" if closes else "",
                           entry_note="; ".join(x for x in [pm.group(1) if pm else "", "Purchase required" if purchase else ""] if x)[:300],
                           image=img_url(a, CDN + "/"), tags=["purchase"] if purchase else None))
    return out

CFR = "https://www.concours.fr"

@source("Concours.fr", "aggregator", CFR + "/", "French free-competition blog; closing dates read from each post (cached).", country="fr")
def fr_concoursfr(ctx):
    out = []
    pages = ctx.cap("cfr_pages", 3)
    urls = [CFR + "/"] + [CFR + f"/page/{i}/" for i in range(2, pages + 1)]
    for u, s in _pages(ctx, urls):
        for a in s.select("div.rt-holder.tpg-post-holder"):
            h = a.select_one("h3.entry-title a[href]")
            if not h: continue
            title = clean(h.get_text(" "))
            if not re.match(r"(gagne[zr]|remporte[zr]|tentez|jeu|concours)", title, re.I): continue
            out.append(rec(title=title, link=h["href"], prize_desc=title, prize_value=prize_value_from_text(title), entry_type="free", image=img_url(a, CFR)))
    dates = detail_closing(ctx, [o["link"] for o in out], cap=ctx.cap("cfr_detail", 12))
    for o in out:
        if o["link"] in dates: o["closes_at"], o["closes_precision"] = dates[o["link"]]
    return out

# ================================================================== Netherlands
PV = "https://www.prijsvragen.nl"

@source("Prijsvragen.nl", "aggregator", PV + "/", "Dutch winacties/prijsvragen directory (no closing dates on the listing).", country="nl")
def nl_prijsvragen(ctx):
    r = ctx.get(PV + "/")
    if not r: return []
    s = soup(r); out = []
    for li in s.select("li.white, li.light-pink"):
        a = li.select_one('a[href^="/winactie/"]')
        if not a: continue
        title = clean(a.get_text(" "))
        first = li.select_one("div")
        dom = clean(first.get_text(" ").replace(title, "", 1)) if first else ""
        how = clean((li.select_one("div.alt p") or li).get_text(" ")) if li.select_one("div.alt p") else ""
        out.append(rec(title=title, promoter=dom, link=_abs(PV, a["href"]), prize_desc=title, prize_value=prize_value_from_text(title),
                       entry_type="free", entry_note=how[:300]))
    return out

PZ = "https://www.prijzenzolder.nl"

@source("PrijzenZolder.nl", "aggregator", PZ + "/", "Dutch prijsvragen directory (no closing dates on the listing).", country="nl")
def nl_prijzenzolder(ctx):
    out = []
    for u, s in _pages(ctx, [PZ + "/", PZ + "/facebookprijsvragen.html"]):
        for tr in s.select("table tr"):
            a = tr.select_one('a[href^="/win/"]')
            tds = tr.select("td")
            if not a or len(tds) < 2: continue
            cell = clean(tds[0].get_text(" "))
            m = re.match(r"(.+?)\s+([A-Za-z0-9.-]+\.(?:nl|com|be|eu)(?:/[^\s(]*)?)\s*\(", cell)
            title = clean(m.group(1)) if m else clean(a.get_text(" "))
            how = re.sub(r"^(Doe mee|Delen)\s*", "", clean(tds[1].get_text(" ")))
            out.append(rec(title=title, promoter=(m.group(2) if m else ""), link=_abs(PZ, a["href"]), prize_desc=title,
                           prize_value=prize_value_from_text(title), entry_type="free", entry_note=how[:300]))
    return out

WA = "https://winacties.nl"

@source("WinActies.nl", "aggregator", WA + "/", "Dutch winacties directory (no closing dates on the listing).", country="nl")
def nl_winacties(ctx):
    r = ctx.get(WA + "/")
    if not r: return []
    s = soup(r); out = []
    for c in s.select("div.card-productBox"):
        h = c.select_one("h3 a[href]")
        if not h: continue
        title = clean(h.get_text(" "))
        desc = clean((c.select_one("div.content > p") or c).get_text(" "))[:400] if c.select_one("div.content > p") else ""
        dom = ""
        for li in c.select("li"):
            t = clean(li.get_text(" "))
            if t.startswith("Winactie op:"): dom = clean(t.split(":", 1)[1])
        how = ""
        st = c.select_one("li strong")
        if st and "Wat moet je doen" in st.get_text(): how = clean(st.get_text(" ").split(":", 1)[1])
        out.append(rec(title=title, promoter=dom, link=_abs(WA, h["href"]), prize_desc=desc or title, prize_value=prize_value_from_text(title + " " + desc),
                       entry_type="free", entry_note=how[:200], image=img_url(c, WA)))
    return out

PG = "https://www.prijsvragengala.nl"

@source("PrijsvragenGala.nl", "aggregator", PG + "/", "Dutch winacties directory (no closing dates on the listing).", country="nl")
def nl_gala(ctx):
    r = ctx.get(PG + "/")
    if not r: return []
    s = soup(r); out = []
    for box in s.select("div.row.box, div.row.box_oneven"):
        col = box.parent
        t = col.select_one(".titel strong") if col else None
        a = box.select_one('a[href^="/bekijk/"]')
        if not t or not a: continue
        title = clean(t.get_text(" "))
        how = clean((box.select_one(".antwoord") or box).get_text(" ")).replace("Deelname info :", "").strip() if box.select_one(".antwoord") else ""
        dom = box.select_one("small strong")
        out.append(rec(title=title, promoter=clean(dom.get_text()) if dom else "", link=_abs(PG, a["href"]), prize_desc=title,
                       prize_value=prize_value_from_text(title), entry_type="free", entry_note=how[:200], image=img_url(box, PG)))
    return out

# ================================================================== Ireland
CIE = "https://competitions.ie"

def _cie_cards(s, station=""):
    out = []
    for c in s.select("div.border-muted-foreground"):
        a = c.select_one('a[href^="/competition/"]')
        if not a: continue
        txt = clean(c.get_text(" | "))
        title_el = None
        for x in c.select('a[href^="/competition/"]'):
            if clean(x.get_text()) and len(clean(x.get_text())) > 8: title_el = x; break
        title = clean(title_el.get_text(" ")) if title_el else ""
        if not title: continue
        cat = c.select_one('a[href^="/competition-category/"]')
        left = re.search(r"(\d+\s*(?:weeks?|days?|hours?|months?)\s*left|ends? today|ends? tomorrow)", txt, re.I)
        closes = _left_to_date(left.group(1)) if left else None
        parts = [p.strip() for p in txt.split("|")]
        desc = parts[-1] if parts and len(parts[-1]) > 30 else ""
        href = re.sub(r"\?src=listing$", "", a["href"])
        out.append(rec(title=title, link=_abs(CIE, href), prize_desc=desc[:400] or title, prize_value=prize_value_from_text(title + " " + desc),
                       entry_type="free", closes_at=closes, closes_precision="approx" if closes else "", station=station,
                       entry_note=("Category: " + clean(cat.get_text())) if cat else "", image=img_url(c, CIE)))
    return out

@source("Competitions.ie", "aggregator", CIE + "/new-competitions", "Irish competitions directory (new + radio pages).", country="ie")
def ie_competitions(ctx):
    out = []
    pages = ctx.cap("cie_pages", 8)
    urls = [CIE + "/new-competitions"] + [CIE + f"/new-competitions/{i}" for i in range(2, pages + 1)]
    for u, s in _pages(ctx, urls):
        got = _cie_cards(s)
        if not got: break
        out.extend(got)
    extra = ["/competitions-ending-soon"] + [f"/competition-category/{c}" for c in ("cash", "travel-and-hotels", "tickets", "food-and-drink",
             "books-and-magazines", "special-occasions", "sports-and-leisure", "toys-and-games")] + ["/win-a-car", "/win-a-holiday", "/win-cash"]
    for u, s in _pages(ctx, [CIE + e for e in extra]):
        out.extend(_cie_cards(s))
    return out

FB = "https://freebie.ie"

@source("Freebie.ie", "aggregator", FB + "/", "Irish free-competitions directory (competition listings only; free events are ignored).", country="ie")
def ie_freebie(ctx):
    r = ctx.get(FB + "/")
    if not r: return []
    s = soup(r); out = []
    for c in s.select("article.card"):
        a = c.select_one('a[href^="/free-competitions/"]')
        if not a: continue
        h = c.select_one("h2, h3")
        title = clean(h.get_text(" ")) if h else clean(a.get_text(" "))
        txt = clean(c.get_text(" | "))
        if "REPUBLIC OF IRELAND" not in txt.upper() and "IRELAND" not in txt.upper(): continue
        m = re.search(r"Closes: \| (?:\w+day )?(\d{1,2} \w+ 20\d\d)", txt)
        closes = util.parse_date(m.group(1)) if m else None
        prize = ""
        parts = [p.strip() for p in txt.split("|")]
        if title in parts and parts.index(title) + 1 < len(parts): prize = parts[parts.index(title) + 1]
        who = re.search(r"Who can enter: \| ([^|]+)", txt)
        out.append(rec(title=title, link=_abs(FB, a["href"]), prize_desc=prize[:400] or title, prize_value=prize_value_from_text(title + " " + prize),
                       entry_type="free", closes_at=closes, closes_precision="date" if closes else "", image=img_url(c, FB),
                       entry_note=("Eligibility: " + clean(who.group(1))) if who else ""))
    return out

FC = "https://fearlesscompetitions.com"

@source("Fearless Competitions (ROI)", "aggregator", FC + "/ireland-competitions/", "Competitions marked open to Republic of Ireland entrants only.", country="ie")
def ie_fearless(ctx):
    out = []
    pages = ctx.cap("fc_pages", 4)
    urls = [FC + "/ireland-competitions/"] + [FC + f"/ireland-competitions/page/{i}/" for i in range(2, pages + 1)]
    for u, s in _pages(ctx, urls):
        cards = s.select("article.fd-card")
        if not cards: break
        for c in cards:
            if c.get("data-market-roi") != "1": continue
            a = c.select_one('a[href*="/competition/"]')
            if not a: continue
            title = clean(a.get("aria-label", "").replace("View ", "", 1)) or clean(a.get_text(" "))
            brand = c.select_one('a[href*="/brand/"]')
            txt = clean(c.get_text(" | "))
            paid = c.get("data-purchase") == "1" or "Purchase" in txt
            nimg = c.select_one("noscript img")
            out.append(rec(title=title, promoter=clean(brand.get_text(" ")) if brand else "", link=a["href"], prize_desc=title,
                           prize_value=prize_value_from_text(title), entry_type="free", image=(nimg.get("src") if nimg else img_url(c, FC)),
                           entry_note=("Purchase required" if paid else ""), tags=["purchase"] if paid else None))
    return out

# ================================================================== Italy
DCC = "https://www.dimmicosacerchi.it"

@source("DimmiCosaCerchi (gratuiti)", "aggregator", DCC + "/concorsi-a-premi/gratuiti", "Italian free concorsi a premio; closing dates read from each article (cached).", country="it")
def it_dcc(ctx):
    out = []
    pages = ctx.cap("dcc_pages", 6)
    urls = [DCC + "/concorsi-a-premi/gratuiti"] + [DCC + f"/concorsi-a-premi/gratuiti/page/{i}" for i in range(2, pages + 1)]
    for u, s in _pages(ctx, urls):
        cards = s.select("div.p-wrap")
        if not cards: break
        for c in cards:
            h = c.select_one(".entry-title a[href]")
            if not h: continue
            title = clean(h.get_text(" "))
            tm = c.select_one("time[datetime]")
            pub = tm["datetime"] if tm else ""
            if pub:
                try:
                    if (now() - datetime.fromisoformat(pub)).days > 75: continue    # old article, very likely closed
                except ValueError: pass
            ex = c.select_one(".entry-summary, p")
            desc = clean(ex.get_text(" "))[:400] if ex else ""
            out.append(rec(title=title, link=h["href"], prize_desc=desc or title, prize_value=prize_value_from_text(title + " " + desc),
                           entry_type="free", image=img_url(c, DCC), extra={"published": pub}))
    seen = {}
    for o in out: seen.setdefault(o["link"], o)
    out = list(seen.values())
    dates = detail_closing(ctx, [o["link"] for o in out], cap=ctx.cap("dcc_detail", 20))
    keep = []
    for o in out:
        if o["link"] in dates: o["closes_at"], o["closes_precision"] = dates[o["link"]]
        elif o["extra"].get("published"):
            try:
                if (now() - datetime.fromisoformat(o["extra"]["published"])).days > 40: continue   # no stated date and >40 days old: don't guess it's open
            except ValueError: pass
        keep.append(o)
    return keep

SALVA_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ9YU2F0rx0zZu8u0-vEdFu9tlJ1jBTsclB88REu0EYxeH_NEDfKFlDF4glmYjV-_45lmzsXEhYHrGz/pub?gid=903982968&single=true&output=csv"

@source("Salvadenari", "aggregator", "https://www.salvadenari.com/lista-concorsi-promo/", "Italian concorsi list (the site's own published sheet); expired ones removed by the site.", country="it")
def it_salvadenari(ctx):
    r = ctx.get(SALVA_CSV)
    if not r: return []
    r.encoding = "utf-8"
    out = []
    for row in csv.DictReader(io.StringIO(r.text)):
        tipo = (row.get("Tipo Concorso") or "").strip()
        if not re.search(r"instant|estrazione|concorso|giveaway|vinci", tipo, re.I): continue   # skip omaggi / cashback / product tests
        premio = clean(row.get("Premio"))
        brand = clean(row.get("Brand"))
        if not premio: continue
        closes = dmy(row.get("Data Scadenza") or "")
        acq = clean(row.get("Acquisto"))
        purchase = bool(acq) and not re.search(r"nessun acquisto|non (?:è )?richiest|gratuit", acq, re.I)
        req = clean(row.get("Requisiti"))
        out.append(rec(title=f"{brand}: {premio}"[:170], promoter=brand, link=(row.get("Link") or "").strip(), prize_desc=premio[:500],
                       prize_value=prize_value_from_text(premio), entry_type="free", closes_at=closes, closes_precision="date" if closes else "",
                       image=(row.get("Immagine Copertina") or "").strip(), entry_note="; ".join(x for x in [tipo, "Purchase required: " + acq[:160] if purchase else "", req[:200]] if x),
                       tags=["purchase"] if purchase else None))
    return out

# ================================================================== Australia / New Zealand: OzBargain & Cheapies, competitions.com.au/.co.nz
_SHORT_MON = {m: i for m, i in MONTHS.items()}

def _ozb_expiry(t):
    t = clean(t)
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(20\d\d)", t)
    if m and m.group(2)[:3].lower() in _SHORT_MON:
        try: return datetime(int(m.group(3)), _SHORT_MON[m.group(2)[:3].lower()], int(m.group(1)), 23, 59, tzinfo=util.TZ), "date"
        except ValueError: return None, ""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*(?:\s+(\d{1,2})(?::(\d\d))?\s*(am|pm))?", t)
    if m and m.group(2)[:3].lower() in _SHORT_MON:
        h, mi = 23, 59; prec = "date"
        if m.group(3):
            h = int(m.group(3)) % 12 + (12 if m.group(5).lower() == "pm" else 0); mi = int(m.group(4) or 0); prec = "exact"
        d = infer_year(int(m.group(1)), _SHORT_MON[m.group(2)[:3].lower()], h, mi)
        return d, (prec if d else "")
    return None, ""

def _ozb(ctx, base, pages):
    out = []
    urls = [base + "/competition"] + [base + f"/competition?page={i}" for i in range(1, pages)]
    for u, s in _pages(ctx, urls):
        nodes = s.select("div.node-competition")
        if not nodes: break
        for n in nodes:
            h = n.select_one("h2.title")
            a = h.select_one("a[href]") if h else None
            if not a: continue
            title = clean(h.get("data-title") or a.get_text(" "))
            go = n.select_one('a[href^="/goto/"][title^="Go to "]')
            direct = go["title"][6:].strip() if go else ""
            meta = {}
            for sp in n.select("ul.competition-list-meta span[title]"): meta[sp["title"]] = clean(sp.get_text(" "))
            ex = n.select_one(".nodeexpiry")
            if ex and ex.select_one(".marker") and re.search(r"expired", ex.get_text(), re.I): continue
            closes, prec = _ozb_expiry(ex.get_text(" ")) if ex else (None, "")
            tags = [clean(x.get_text()) for x in n.select(".tag a")]
            pool = money(meta.get("Total prize pool", ""))
            via = n.select_one(".via a")
            note = "; ".join(x for x in [("Open to: " + meta["Open to"]) if meta.get("Open to") else "", ("Entry: " + meta["Entry methods"]) if meta.get("Entry methods") else "",
                                         ("Requires: " + meta["Entry requirements"]) if meta.get("Entry requirements") else "", ", ".join(tags)] if x)
            paid = bool(re.search(r"purchase", meta.get("Entry requirements", ""), re.I))
            out.append(rec(title=title, promoter=clean(via.get_text()) if via else "", link=(direct if direct.startswith("http") else _abs(base, a["href"])),
                           prize_desc=title, prize_value=prize_value_from_text(title) or pool, entry_type="free",
                           closes_at=closes, closes_precision=prec, entry_note=note[:300], image=img_url(n.select_one(".foxshot-container"), base),
                           tags=(["purchase"] if paid else None), extra={"listing": _abs(base, a["href"])}))
    return out

@source("OzBargain Competitions", "aggregator", "https://www.ozbargain.com.au/competition", "Community-posted Australian competitions (open listings, first pages).", country="au")
def au_ozb(ctx):
    return _ozb(ctx, "https://www.ozbargain.com.au", ctx.cap("ozb_pages", 6))

@source("Cheapies Competitions", "aggregator", "https://www.cheapies.nz/competition", "Community-posted New Zealand competitions (open listings, first pages).", country="nz")
def nz_cheapies(ctx):
    return _ozb(ctx, "https://www.cheapies.nz", ctx.cap("chp_pages", 4))

def _ends(txt):
    t = clean(txt)
    m = re.search(r"Ends\s+([A-Za-z]{3})[a-z]*\s+(\d{1,2})(?:,?\s+(20\d\d))?", t)
    if m and m.group(1)[:3].lower() in _SHORT_MON:
        mon = _SHORT_MON[m.group(1)[:3].lower()]
        if m.group(3):
            try: return datetime(int(m.group(3)), mon, int(m.group(2)), 23, 59, tzinfo=util.TZ), "date"
            except ValueError: return None, ""
        d = infer_year(int(m.group(2)), mon)
        return d, ("date" if d else "")
    m = re.search(r"Ends\s+(in\s+\d+\s+\w+|today|tomorrow)", t, re.I)
    if m:
        d = _left_to_date(m.group(1)); return d, ("approx" if d else "")
    return None, ""

def _compsite(ctx, base, pages):
    out = []
    urls = [base + "/"] + [base + f"/?page={i}" for i in range(2, pages + 1)]
    for u, s in _pages(ctx, urls):
        cards = s.select("article.competition-card")
        if not cards: break
        live = 0
        for c in cards:
            if c.get("data-expired") == "true": continue
            live += 1
            h = c.select_one("h3")
            if not h: continue
            title = clean(h.get("title") or h.get_text(" "))
            det = None
            for a in c.select("a[href]"):
                if re.match(r"^/win-[^/]+/\d+/$|^/[a-z0-9-]+/\d+/$", a["href"]) and not a["href"].startswith("/exit/"): det = a["href"]; break
            brand = c.select_one('a[href^="/brands/"]')
            txt = clean(c.get_text(" | "))
            val = None
            vb = c.select_one("span.bg-green-700")
            if vb: val = money(vb.get_text())
            closes, prec = _ends(txt)
            paid = c.get("data-free") == "false" or "Purchase Required" in txt
            cats = [clean(a.get_text()) for a in c.select('div.hidden a[href$="-competitions/"], div.hidden a[href^="/win-a-"]')]
            out.append(rec(title=title, promoter=clean(brand.get_text()) if brand else "", link=_abs(base, det) if det else "", prize_desc=title,
                           prize_value=val or prize_value_from_text(title), entry_type="free", closes_at=closes, closes_precision=prec,
                           image=img_url(c, base), entry_note="; ".join(x for x in ["Purchase required" if paid else "", ", ".join(dict.fromkeys(cats))] if x),
                           tags=(["purchase"] if paid else None) if "Charity" not in cats else ["purchase", "charity-lottery"]))
        if live == 0: break
    return [o for o in out if o["link"]]

@source("Competitions.com.au", "aggregator", "https://www.competitions.com.au/", "Australian competitions directory (current listings, capped pages).", country="au")
def au_comps(ctx):
    return _compsite(ctx, "https://www.competitions.com.au", ctx.cap("cau_pages", 10))

@source("Competitions.co.nz", "aggregator", "https://www.competitions.co.nz/", "New Zealand competitions directory (current listings, capped pages).", country="nz")
def nz_comps(ctx):
    return _compsite(ctx, "https://www.competitions.co.nz", ctx.cap("cnz_pages", 6))
