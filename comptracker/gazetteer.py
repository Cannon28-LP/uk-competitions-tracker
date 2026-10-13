"""UK area tagging from comptracker/data/gazetteer.json (cities + sensible regions).
Terms are proper names matched case-sensitively on word boundaries (ALL-CAPS titles are title-cased first), so 'reading a book'
or 'a bubble bath' never match; per-area 'neg' patterns reject look-alikes (Perth WA, New York, Duke of Edinburgh...), and
ambiguous names (Bath, Wells, Ely, Newport, Bangor, Stoke, Hull...) also need a 'ctx' pattern (e.g. 'in Wells', 'Wells Cathedral')."""
import json, os, re

_P = os.path.join(os.path.dirname(__file__), "data", "gazetteer.json")
AREAS = json.load(open(_P, encoding="utf-8"))["areas"]
for a in AREAS:
    a["_rx"] = re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(t) for t in sorted(a["terms"], key=len, reverse=True)) + r")(?![\w-])")
    a["_neg"] = re.compile(a["neg"], re.I) if a.get("neg") else None
    a["_ctx"] = re.compile(a["ctx"], re.I) if a.get("ctx") else None

def _text(it):
    parts = [it.get("title") or "", it.get("prize_desc") or "", it.get("promoter") or "", it.get("station") or ""]
    out = []
    for p in parts:
        letters = [c for c in p if c.isalpha()]
        if letters and sum(c.isupper() for c in letters) / len(letters) > 0.6: p = p.title().replace("'S ", "'s ")
        out.append(p)
    return " | ".join(out)

def areas(it):
    t = _text(it); hit = []
    for a in AREAS:
        if not a["_rx"].search(t): continue
        if a["_ctx"] and not a["_ctx"].search(t): continue
        if a["_neg"]:
            # reject only if every occurrence is explained by the look-alike
            if a["_neg"].search(t) and not a["_rx"].search(a["_neg"].sub(" ", t)): continue
        hit.append(a["id"])
    return hit

def index():
    """For the page: id -> name, nation, region, kind."""
    return [{k: a[k] for k in ("id", "name", "nation", "region", "kind")} for a in AREAS]
