"""Heuristic safety/trust layer. A guide, NOT a guarantee."""
import re, urllib.parse

AGGREGATOR_DOMAINS = ("loquax.co.uk", "theprizefinder.com", "competitionshowroom.com", "moneysavingexpert.com", "competitions-time.co.uk",
                      "competitionstoday.co.uk", "findcompetitions.com")
ESTABLISHED = ["botb", "best of the best", "omaze", "dream car giveaways", "dreamcargiveaways", "7 days performance", "7days performance", "7daysperformance",
               "elite competitions", "revcomps", "rev comps", "click competitions", "clickcompetitions", "raffall", "mckinney", "hittin it big"]
# Only the first few are 'long-running, large'; rest = well-known in the comping community (still check T&Cs!)
BIG_BRANDS = ["tesco", "sainsbury", "asda", "morrisons", "waitrose", "aldi", "lidl", "amazon", "currys", "argos", "john lewis", "marks & spencer", "m&s", "boots",
              "ikea", "itv", "bbc", "channel 4", "channel 5", "heart", "smooth radio", "global", "capital", "classic fm", "mumsnet", "which?", "dfs", "dyson", "samsung",
              "apple", "sony", "nintendo", "lego", "disney", "tui", "jet2", "marella", "p&o", "center parcs", "haven", "butlins", "premier inn", "pan macmillan", "penguin",
              "harpercollins", "hachette", "radio times", "good housekeeping", "woman&home", "hello!", "the sun", "mirror", "express", "telegraph", "guardian", "times holidays",
              "british airways", "easyjet", "ryanair", "virgin", "heinz", "kellogg", "nestle", "cadbury", "walkers", "pepsi", "coca-cola", "unilever", "p&g", "loreal",
              "boohoo", "next", "asos", "very", "tombola", "nationwide", "which", "english heritage", "national trust", "love2shop", "buyagift"]
BIG_DOMAINS = ("tesco.com", "sainsburys.co.uk", "asda.com", "amazon.co.uk", "currys.co.uk", "argos.co.uk", "johnlewis.com", "itv.com", "bbc.co.uk", "bbc.com",
               "channel4.com", "mumsnet.com", "dfs.co.uk", "dyson.co.uk", "samsung.com", "lego.com", "tui.co.uk", "jet2holidays.com", "radiotimes.com", "smoothradio.com",
               "heart.co.uk", "goodhousekeeping.com", "panmacmillan.com", "nationwide.co.uk", "ikea.com", "boots.com", "mandmdirect.com", "waitrose.com")
SCAM_TLDS = (".xyz", ".top", ".click", ".monster", ".icu", ".buzz", ".cyou", ".sbs", ".rest", ".cfd", ".gq", ".tk", ".ml", ".cf", ".ga", ".work", ".vip", ".bid", ".loan")
SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "cutt.ly", "rb.gy", "shorturl.at", "tiny.cc")
SCAM_WORDS = re.compile(r"(congratulations|you(?:'|’)?ve been selected|you have been selected|you(?:'|’)ve won|claim your prize (?:now|today)|act now|urgent|limited slots|"
                        r"guaranteed (?:win|winner)s? (?:every|for all)|100% (?:win|winner)|pay (?:a )?(?:small )?(?:fee|delivery|shipping|postage)|just pay (?:p&p|postage|shipping|delivery)|"
                        r"processing fee|admin fee|release fee|western union|gift ?card codes?|crypto|bitcoin|whatsapp (?:us|me)|telegram|dm to claim|"
                        r"free (?:iphone|ipad|ps5|macbook|samsung)s? (?:for all|to everyone))", re.I)
CARD_FREE = re.compile(r"(card details|credit card|debit card|free trial|subscription|£\d+(?:\.\d+)? (?:p&p|postage|delivery|shipping))", re.I)
SPEND_TO_QUALIFY = re.compile(r"(must have spent|spend £\s?\d|spend \d|spent £\s?\d|deposit|wager|new customers only)", re.I)

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
    elif _has(prom, BIG_BRANDS) or any(d.endswith(b) for b in BIG_DOMAINS) or _has(title, BIG_BRANDS[:60]) and not paid:
        score += 3; pos.append("Recognised big brand / publisher.")
    if "radio" in (item.get("tags") or []) and item.get("entry_type") != "paid":
        score += 3; pos.append("Run by an established UK radio broadcaster (check the station's competition T&Cs for entry rules).")
    if "MSE Competitions Time" in srcs:
        score += 3; pos.append("Listed in MoneySavingExpert's moderated Competitions Time forum.")
    if any(s in srcs for s in ("Competitions Time", "Competitions Today", "ThePrizeFinder", "Loquax", "Loquax Win-a-House")):
        score += 2; pos.append("Listed on a curated comping directory that screens submissions.")
    if extra.get("vcode"):
        score += 3; pos.append("Operator is a signatory of the UK Voluntary Code of Good Practice for Prize Draw Operators.")
    if extra.get("fc_trust") in ("Verified", "Trusted"):
        score += 3; pos.append(f"FindCompetitions rates operator '{extra['fc_trust']}'.")
    if "Competition Showroom" in srcs or "FindCompetitions" in srcs:
        score += 1; pos.append("Operator tracked by a comparison site (published ticket counts).")
    if prom: score += 1
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
    if paid and not free_route:
        flag("medium", "Paid draw and I couldn't confirm a free (postal) entry route – UK law normally requires one or a genuine skill test.")
    if site and site.get("checked") and not site.get("terms") and paid:
        flag("medium", "No Terms & Conditions link found on the operator's website.")
    if any(d.endswith(t) for t in SCAM_TLDS) or d in SHORTENERS:
        flag("high", f"Suspicious web address ({d}).")
    text = f"{title} {item.get('prize_desc','')} {item.get('entry_note','')}"
    if SCAM_WORDS.search(title + " " + item.get("prize_desc", "")):
        flag("high", "Scam-style/urgent wording (e.g. 'claim now', fees to claim, 'you've been selected').")
    if item.get("entry_type") == "free" and CARD_FREE.search(title + " " + item.get("prize_desc", "") + " " + (item.get("entry_note") or "")):
        flag("high", "Labelled free but mentions card details / trial / postage fee – check you won't be charged.")
    if SPEND_TO_QUALIFY.search(title):
        flag("medium", "Described as free but title says you need to spend/deposit/be a (new) customer to qualify.")
    if item.get("entry_type") == "paid" and item.get("entry_cost") is not None and item["entry_cost"] >= 20:
        flag("low", "High per-ticket cost – check your £30/month budget.")
    if item.get("prize_value") and item.get("entry_cost") and item.get("tickets_total"):
        rev = item["entry_cost"] * item["tickets_total"]
        if rev > 4 * item["prize_value"] and item["prize_value"] >= 500:
            flag("low", f"Ticket revenue if sold out (~£{rev:,.0f}) is far above the stated prize value – poor value.")
    if paid:
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
    return {"badge": badge, "score": score, "positives": pos, "flags": flags}
