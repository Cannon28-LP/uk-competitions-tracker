"""Heuristic safety/trust layer. A guide, NOT a guarantee. Country-aware via util.CUR (brands, directories, regulator notes)."""
import re, urllib.parse
from . import util
from .countries import PAGE as _CPAGE

AGGREGATOR_DOMAINS = ("loquax.co.uk", "theprizefinder.com", "competitionshowroom.com", "moneysavingexpert.com", "competitions-time.co.uk",
                      "competitionstoday.co.uk", "findcompetitions.com", "latestdeals.co.uk",
                      # other countries' directories (their own listing pages are not the promoter)
                      "12gewinn.de", "gewinnhai.de", "jeu-concours.biz", "concours-du-net.com", "concours.fr", "prijsvragen.nl", "prijzenzolder.nl",
                      "winacties.nl", "competitions.ie", "fearlesscompetitions.com", "dimmicosacerchi.it", "salvadenari.com", "ozbargain.com.au",
                      "cheapies.nz", "competitions.com.au", "competitions.co.nz")
ESTABLISHED = ["botb", "best of the best", "omaze", "dream car giveaways", "dreamcargiveaways", "7 days performance", "7days performance", "7daysperformance",
               "elite competitions", "revcomps", "rev comps", "click competitions", "clickcompetitions", "raffall", "mckinney", "hittin it big"]
# Only the first few are 'long-running, large'; rest = well-known in the comping community (still check T&Cs!)
BIG_BRANDS = ["tesco", "sainsbury", "asda", "morrisons", "waitrose", "aldi", "lidl", "amazon", "currys", "argos", "john lewis", "marks & spencer", "m&s", "boots",
              "ikea", "itv", "bbc", "channel 4", "channel 5", "heart", "smooth radio", "global", "capital", "classic fm", "mumsnet", "which?", "dfs", "dyson", "samsung",
              "apple", "sony", "nintendo", "lego", "disney", "tui", "jet2", "marella", "p&o", "center parcs", "haven", "butlins", "premier inn", "pan macmillan", "penguin",
              "harpercollins", "hachette", "radio times", "olive magazine", "good housekeeping", "woman&home", "hello!", "the sun", "mirror", "express", "telegraph", "guardian", "times holidays",
              "british airways", "easyjet", "ryanair", "virgin", "heinz", "kellogg", "nestle", "cadbury", "walkers", "pepsi", "coca-cola", "unilever", "p&g", "loreal",
              "boohoo", "next", "asos", "very", "tombola", "nationwide", "which", "english heritage", "national trust", "love2shop", "buyagift"]
BIG_DOMAINS = ("makemeawinner.co.uk", "tesco.com", "sainsburys.co.uk", "asda.com", "amazon.co.uk", "currys.co.uk", "argos.co.uk", "johnlewis.com", "itv.com", "bbc.co.uk", "bbc.com",
               "channel4.com", "mumsnet.com", "dfs.co.uk", "dyson.co.uk", "samsung.com", "lego.com", "tui.co.uk", "jet2holidays.com", "radiotimes.com", "smoothradio.com",
               "heart.co.uk", "goodhousekeeping.com", "olivemagazine.com", "panmacmillan.com", "nationwide.co.uk", "ikea.com", "boots.com", "mandmdirect.com", "waitrose.com",
               # established UK golf publishers (company + competition T&Cs on own domain checked Oct 2026)
               "nationalclubgolfer.com", "northerngolfer.co.uk", "golfmonthly.com", "todays-golfer.com")
SCAM_TLDS = (".xyz", ".top", ".click", ".monster", ".icu", ".buzz", ".cyou", ".sbs", ".rest", ".cfd", ".gq", ".tk", ".ml", ".cf", ".ga", ".work", ".vip", ".bid", ".loan")
SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "cutt.ly", "rb.gy", "shorturl.at", "tiny.cc")
SCAM_WORDS = re.compile(r"(congratulations|you(?:'|’)?ve been selected|you have been selected|you(?:'|’)ve won|claim your prize (?:now|today)|act now|urgent|limited slots|"
                        r"guaranteed (?:win|winner)s? (?:every|for all)|100% (?:win|winner)|pay (?:a )?(?:small )?(?:fee|delivery|shipping|postage)|just pay (?:p&p|postage|shipping|delivery)|"
                        r"processing fee|admin fee|release fee|western union|gift ?card codes?|crypto|bitcoin|whatsapp (?:us|me)|telegram|dm to claim|"
                        r"free (?:iphone|ipad|ps5|macbook|samsung)s? (?:for all|to everyone))", re.I)
CARD_FREE = re.compile(r"(card details|credit card|debit card|free trial|subscription|£\d+(?:\.\d+)? (?:p&p|postage|delivery|shipping))", re.I)
SPEND_TO_QUALIFY = re.compile(r"(must have spent|spend £\s?\d|spend \d|spent £\s?\d|deposit|wager|new customers only)", re.I)

# Editorially curated / community-moderated directories in the other countries (they state that they check listings)
DIRECTORIES_INTL = ("12Gewinn.de", "GewinnHai", "Jeu-concours.biz", "Concours du Net", "Concours.fr", "Prijsvragen.nl", "PrijzenZolder.nl", "WinActies.nl",
                    "Competitions.ie", "Fearless Competitions (ROI)", "DimmiCosaCerchi (gratuiti)", "Salvadenari", "OzBargain Competitions",
                    "Cheapies Competitions", "Competitions.com.au", "Competitions.co.nz")
INTERNATIONAL_BRANDS = ["amazon", "apple", "samsung", "sony", "nintendo", "lego", "disney", "ikea", "dyson", "coca-cola", "pepsi", "nestle", "nestlé", "heineken",
                        "l'oréal", "loreal", "unilever", "philips", "bosch", "lidl", "aldi", "spotify", "netflix", "red bull", "mcdonald", "burger king", "kellogg", "mars",
                        "ferrero", "kinder", "milka", "nivea", "garnier", "playmobil", "decathlon", "zalando", "tui", "booking.com", "airbnb", "volkswagen", "bmw", "mercedes",
                        "toyota", "hyundai", "kia", "vodafone", "carlsberg", "danone", "procter", "gillette", "oral-b", "braun", "tefal", "moulinex", "delonghi", "de'longhi"]
LOCAL_BRANDS = {
    "de": ["rewe", "edeka", "kaufland", "penny", "netto", "mediamarkt", "media markt", "saturn", "otto", "dm-drogerie", "dm ", "rossmann", "krombacher", "veltins",
           "bitburger", "warsteiner", "haribo", "ritter sport", "check24", "adac", "ard", "zdf", "rtl", "prosieben", "sat.1", "bild", "hörzu", "tchibo", "miele",
           "deutsche bahn", "lufthansa", "sparkasse", "volksbank", "aktion mensch", "telekom", "o2", "radio", "antenne", "schlager radio", "bayern 3", "swr", "ndr", "wdr", "mdr"],
    "fr": ["carrefour", "leclerc", "auchan", "intermarché", "monoprix", "fnac", "darty", "boulanger", "tf1", "m6", "france tv", "france télévisions", "club france tv",
           "rtl", "nrj", "europe 1", "fun radio", "nostalgie", "chérie fm", "20 minutes", "le parisien", "marie claire", "cosmopolitan", "notre temps", "femme actuelle",
           "sncf", "air france", "leroy merlin", "castorama", "seb", "crédit agricole", "la redoute", "cdiscount", "bonduelle", "lu ", "petit marseillais"],
    "nl": ["albert heijn", "jumbo", "bol.com", "coolblue", "hema", "kruidvat", "etos", "blokker", "rtl", "npo", "nu.nl", "telegraaf", "libelle", "margriet", "linda",
           "postcode loterij", "staatsloterij", "vriendenloterij", "efteling", "center parcs", "douwe egberts", "action", "praxis", "gamma", "anwb", "radio 538", "qmusic", "sky radio"],
    "ie": ["rté", "rte", "virgin media", "today fm", "fm104", "98fm", "spin 1038", "spin", "newstalk", "radio nova", "beat 102", "irish independent", "irish times",
           "thejournal", "the journal", "dunnes", "supervalu", "tesco", "centra", "spar", "eir", "three", "bord gáis", "electric ireland", "an post", "guinness",
           "tayto", "brennans", "penneys", "brown thomas", "arnotts", "harvey norman", "currys", "smyths", "movies.ie", "her.ie", "joe.ie", "lovin"],
    "it": ["esselunga", "conad", "coop", "carrefour", "mediaworld", "unieuro", "euronics", "barilla", "mulino bianco", "lavazza", "rai", "mediaset", "mondadori",
           "autogrill", "eni", "enel", "tim", "wind tre", "fiat", "nutella", "san pellegrino", "peroni", "galbani", "algida", "despar", "pam", "eurospin", "radio deejay", "rtl 102.5", "radio 105"],
    "au": ["woolworths", "coles", "jb hi-fi", "the good guys", "harvey norman", "bunnings", "kmart", "big w", "myer", "david jones", "qantas", "virgin australia",
           "nova", "kiis", "triple m", "hit network", "abc", "channel 7", "channel 9", "channel 10", "seven", "nine", "rsl art union", "mater", "yourtown",
           "endeavour foundation", "surf life saving", "telstra", "optus", "arnott", "cadbury", "uncle tobys", "iga"],
    "nz": ["countdown", "woolworths", "new world", "pak'nsave", "pak n save", "the warehouse", "noel leeming", "harvey norman", "air new zealand", "nzme", "the hits",
           "zm", "more fm", "the edge", "newstalk zb", "tvnz", "three", "stuff", "nz herald", "heart foundation", "spark", "one nz", "2degrees", "mitre 10",
           "bunnings", "farmers", "briscoes", "whittaker", "watties", "lotto nz"],
}
LOCAL_SCAM = re.compile(r"(bearbeitungsgebühr|gewinnbenachrichtigung|gebühr (?:zahlen|bezahlen|überweisen)|frais de dossier|frais de traitement|administratiekosten|"
                        r"betaal (?:eerst|de kosten)|spese di (?:gestione|spedizione) per (?:ritirare|ricevere) il premio|pagare per ricevere)", re.I)
LOCAL_TRIAL = re.compile(r"(elk moment opzegbaar|gratis lot|gratis meespelen|proefabonnement|probeabo|kostenpflichtig\w* abo|testabo|essai gratuit|abonnement d'essai|prova gratuita|abbonamento di prova|free trial)", re.I)

def brands():
    cc = util.CUR["cc"]
    return BIG_BRANDS if cc == "uk" else LOCAL_BRANDS.get(cc, []) + INTERNATIONAL_BRANDS

DIRECTORIES = ("Competitions Time", "Competitions Today", "ThePrizeFinder", "Loquax", "Loquax Win-a-House", "MSE Competitions Time",
               "FindCompetitions", "Competition Showroom", "Latest Deals")
_DOMAINISH = re.compile(r"^(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.[a-z]{2,})(?:/.*)?$", re.I)

def promoter_domain(promoter):
    """Some aggregators give the promoter as its website ('panmacmillan.com'); return that domain, else ''."""
    m = _DOMAINISH.match((promoter or "").strip())
    return m.group(1).lower() if m else ""

def domain(url):
    try:
        h = urllib.parse.urlsplit(url).netloc.lower()
    except Exception:
        return ""
    return h[4:] if h.startswith("www.") else h

def is_aggregator_domain(d):
    return any(d == a or d.endswith("." + a) for a in AGGREGATOR_DOMAINS)

def blocked(item):
    """Return reason string if the listing should be excluded altogether."""
    d = domain(item.get("link", ""))
    for u in (item.get("link", ""),):
        if d in SHORTENERS: return "URL shortener link"
        if any(d.endswith(t) for t in SCAM_TLDS): return f"suspicious domain ({d})"
    t = item.get("title", "") + " " + item.get("prize_desc", "")
    if SCAM_WORDS.search(t) and not re.search(r"\b(radio|tv|itv|bbc)\b", t, re.I):
        return "scam-style wording"
    return ""

def _has(hay, words):
    h = hay.lower()
    return any(w in h for w in words)

def assess(item, site=None):
    """item: merged competition dict. site: optional dict from domain check {terms, privacy, company, free_route, checked}."""
    pos, flags = [], []
    score = 0
    title = item.get("title", ""); prom = item.get("promoter", "")
    d = domain(item.get("link", ""))
    srcs = item.get("sources", [])
    hay = f"{prom} {d} {title}"
    extra = item.get("extra") or {}
    paid = item.get("entry_type") == "paid"

    # --- positives
    if _has(prom + " " + d, ESTABLISHED):
        score += 3; pos.append("Established, well-known operator (heuristic list).")
    elif _has(prom, brands()) or any(d.endswith(b) for b in BIG_DOMAINS) or _has(title, brands()[:60] if util.CUR["cc"] == "uk" else brands()) and not paid:
        score += 3; pos.append("Recognised big brand / publisher.")
    if "radio" in (item.get("tags") or []) and item.get("entry_type") != "paid":
        score += 3; pos.append(("Run by an established UK radio broadcaster" if util.CUR["cc"] == "uk" else "Run by an established radio broadcaster") + " (check the station's competition T&Cs for entry rules).")
    if "MSE Competitions Time" in srcs:
        score += 3; pos.append("Listed in MoneySavingExpert's moderated Competitions Time forum.")
    if any(s in srcs for s in ("Competitions Time", "Competitions Today", "ThePrizeFinder", "Loquax", "Loquax Win-a-House") + DIRECTORIES_INTL):
        score += 2; pos.append("Listed on a curated comping directory that screens submissions.")
    if extra.get("vcode"):
        score += 3; pos.append("Operator is a signatory of the UK Voluntary Code of Good Practice for Prize Draw Operators.")
    if extra.get("fc_trust") in ("Verified", "Trusted"):
        score += 3; pos.append(f"FindCompetitions rates operator '{extra['fc_trust']}'.")
    if "Competition Showroom" in srcs or "FindCompetitions" in srcs:
        score += 1; pos.append("Operator tracked by a comparison site (published ticket counts).")
    if prom: score += 1
    ndir = len([x for x in srcs if x in DIRECTORIES or x in DIRECTORIES_INTL])
    if ndir >= 2 and not paid:
        score += 1; pos.append(f"Cross-listed by {ndir} independent comping directories.")
    if site and site.get("terms"):
        score += 1; pos.append("Terms & Conditions page found on operator site.")
    if site and site.get("company"):
        score += 1; pos.append(f"Company number shown on site ({site['company']}).")
    free_route = False
    if paid:
        if site and site.get("free_route"): free_route = True
        if extra.get("free_route"): free_route = True
        if any(k in (item.get("entry_note") or "").lower() for k in ("free postal", "no purchase necessary", "free (usually postal)", "free entry route", "postal route")):
            free_route = True
        if free_route:
            score += 1; pos.append("A free (no-purchase) entry route is mentioned.")
    # --- red flags
    def flag(sev, text): flags.append({"sev": sev, "text": text})
    if not prom and not ("MSE Competitions Time" in srcs):
        flag("low", "No named promoter/company on the listing.")
    cc = util.CUR["cc"]
    tags = item.get("tags") or []
    if paid and not free_route and cc == "uk":
        flag("medium", "Paid draw and I couldn't confirm a free (postal) entry route – UK law normally requires one or a genuine skill test.")
    elif paid and cc != "uk" and "charity-lottery" not in tags:
        flag("medium", _CPAGE[cc]["paid_note"] + " – check the operator's licence before paying.")
    if "charity-lottery" in tags:
        flag("info", "Paid charity / prize-home lottery – check the licence or permit number in its terms. 18+ only.")
    elif "purchase" in tags:
        flag("info", "A purchase is required to enter (keep your receipt / proof of purchase).")
    big_site = any(d == b or d.endswith("." + b) for b in BIG_DOMAINS)   # big brands' home pages are often JS-built, so the link check misses their T&Cs
    if site and site.get("checked") and not site.get("terms") and paid and not big_site:
        flag("medium", "No Terms & Conditions link found on the operator's website.")
    if any(d.endswith(t) for t in SCAM_TLDS) or d in SHORTENERS:
        flag("high", f"Suspicious web address ({d}).")
    pd = promoter_domain(prom)
    if pd and (any(pd.endswith(t) for t in SCAM_TLDS) or pd in SHORTENERS):
        flag("high", f"Promoter's web address looks suspicious ({pd}).")
    text = f"{title} {item.get('prize_desc','')} {item.get('entry_note','')}"
    if SCAM_WORDS.search(title + " " + item.get("prize_desc", "")) or LOCAL_SCAM.search(title + " " + item.get("prize_desc", "")):
        flag("high", "Scam-style/urgent wording (e.g. 'claim now', fees to claim, 'you've been selected').")
    cf_text = re.sub(r"\b(?:e-?mail|newsletter|mailing list|youtube|channel|podcast)\s+subscri\w*", " ", title + " " + item.get("prize_desc", "") + " " + (item.get("entry_note") or ""), flags=re.I)
    if item.get("entry_type") == "free" and CARD_FREE.search(cf_text):
        flag("high", "Labelled free but mentions card details / trial / postage fee – check you won't be charged.")
    elif LOCAL_TRIAL.search(title + " " + item.get("prize_desc", "") + " " + (item.get("entry_note") or "")):
        flag("medium", "'Free' entry that signs you up for a trial or (lottery) subscription – it may become paid; read the small print.")
    if SPEND_TO_QUALIFY.search(title):
        flag("medium", "Described as free but title says you need to spend/deposit/be a (new) customer to qualify.")
    if item.get("entry_type") == "paid" and item.get("entry_cost") is not None and item["entry_cost"] >= 20:
        flag("low", f"High per-ticket cost – check your {util.CUR['symbol']}30/month budget.")
    if item.get("prize_value") and item.get("entry_cost") and item.get("tickets_total"):
        rev = item["entry_cost"] * item["tickets_total"]
        if rev > 4 * item["prize_value"] and item["prize_value"] >= 500:
            flag("low", f"Ticket revenue if sold out (~{util.CUR['symbol']}{rev:,.0f}) is far above the stated prize value – poor value.")
    if paid and cc == "uk":
        flag("info", "Paid prize competitions (skill-based draws) are generally NOT licensed or regulated by the Gambling Commission, so you have fewer protections than with licensed gambling. 18+ only.")
    sev = {f["sev"] for f in flags}
    if "high" in sev or "medium" in sev:
        badge = "Caution"
    elif score >= 4 and "low" not in sev:
        badge = "Verified"
    elif score >= 6:
        badge = "Verified"
    else:
        badge = "Unverified"
    reason, basis = _reason(badge, item, site, pos, flags, srcs, prom, paid, ndir, big_site)
    return {"badge": badge, "score": score, "positives": pos, "flags": flags, "reason": reason, "basis": basis}

def _reason(badge, item, site, pos, flags, srcs, prom, paid, ndir, big_site):
    """One short, honest line saying WHY the badge is what it is. 'Verified' is never absolute; 'Unverified' says what is missing."""
    checked = bool(site and site.get("checked"))
    has_terms = bool(site and site.get("terms"))
    serious = [f for f in flags if f["sev"] in ("high", "medium")]
    if badge == "Caution":
        return serious[0]["text"], "flagged"
    if badge == "Verified":
        if any("Established" in p for p in pos): return "Established operator on our heuristic list – still read its T&Cs", "established"
        if any("big brand" in p for p in pos): return "Recognised brand/publisher – still read its T&Cs", "brand"
        if any("radio broadcaster" in p for p in pos): return ("Run by an established UK radio broadcaster" if util.CUR["cc"] == "uk" else "Run by an established radio broadcaster"), "radio"
        if any("MoneySavingExpert" in p for p in pos): return "Listed in MoneySavingExpert's moderated forum, promoter named", "mse"
        if has_terms: return "Promoter named, T&Cs found on its site, listed by a curated directory", "terms"
        return "Several independent signals (curated listing, named promoter) – not a guarantee", "signals"
    # Unverified
    dirs = [x for x in srcs if x in DIRECTORIES or x in DIRECTORIES_INTL]
    if not prom:
        if checked and not has_terms: return "Unknown promoter – no T&Cs found", "unknown-no-terms"
        if dirs: return "Unknown promoter – listed by " + (dirs[0] if len(dirs) == 1 else f"{len(dirs)} directories") + " but not identified", "unknown-promoter"
        return "Unknown promoter – no T&Cs found", "unknown-no-terms"
    if checked and not has_terms and not big_site:
        return "Promoter named, but no T&Cs link found on its website", "named-no-terms"
    if checked and has_terms:
        return "Promoter named, T&Cs found – not enough other signals to verify", "named-terms"
    if dirs and not paid:
        return "Aggregator-listed, promoter unverified" + (f" (on {ndir} directories)" if ndir > 1 else ""), "aggregator"
    if paid:
        return "Paid draw by a promoter we couldn't verify – check T&Cs and free-entry route", "paid-unverified"
    if dirs: return "Aggregator-listed, promoter unverified", "aggregator"
    return "Promoter named, not independently verified", "named"
