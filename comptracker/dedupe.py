"""Cross-source de-duplication: exact normalised-title matches (as before) plus a conservative fuzzy match on title tokens.

Two listings are merged only when ALL hold:
  * title tokens are very similar (Jaccard >= .72, or one title contained in the other with >= 3 shared tokens),
  * the £ amounts / other numbers in the titles are identical (so "£50 voucher" never merges with "£500 voucher"),
  * promoters do not clearly conflict, entry costs do not conflict, and closing dates are within ~3 days.
Members from one source are only merged when they are exact repeats (same normalised title) with the same close date."""
import re
from datetime import datetime
from .util import norm, norm_promoter

STOP = set("""win winning won this that a an the of to for your you in on at with and or by from into as is are be it its our
free entry enter entries competition competitions giveaway giveaways chance prize prizes draw draws worth value valued plus one
x get have has will can new now today only just up any all some every each their there tickets""".split())
_MONEY = re.compile(r"£\s?(\d[\d,]*(?:\.\d+)?)\s?(k|m|bn|million|thousand)?(?![\w&])", re.I)
_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")

def _money_tok(m):
    v = float(m.group(1).replace(",", "")); s = (m.group(2) or "").lower()
    v *= {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "bn": 1e9}.get(s, 1)
    return f"£{int(round(v))}"

def tokens(title):
    """-> (word_tokens:set, number_tokens:set)"""
    t = (title or "").lower().replace("&amp;", "&").replace("’", "'")
    t = re.sub(r"\b\d+\s+of\s+\d+\b", " ", t)               # "1 of 3" (number of winners) is not what's being won
    t = re.sub(r"\b(?:win|enter)\b[^a-z0-9£]*(?:\d+|a|an|the)?\s*x\s*\d+\b", " ", t)
    nums = set()
    def sub_money(m):
        nums.add(_money_tok(m)); return " "
    t = _MONEY.sub(sub_money, t)
    t = t.replace("'s", "")
    words = []
    for w in re.findall(r"[a-z0-9]+", t):
        if w in STOP: continue
        if w.isdigit() or re.fullmatch(r"\d+\.\d+", w):
            nums.add(w); continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"): w = w[:-1]
        words.append(w)
    return set(words), nums

def _pconflict(a, b):
    if not a or not b: return False
    if a == b or a in b or b in a: return False
    return True

def similar(d1, d2):
    """Return a score in (0,1] when the two raw records look like the same competition, else 0."""
    w1, n1 = d1["_tok"]; w2, n2 = d2["_tok"]
    if not w1 or not w2 or n1 != n2: return 0.0
    inter = len(w1 & w2)
    if not inter: return 0.0
    jac = inter / len(w1 | w2)
    cont = inter / min(len(w1), len(w2))
    exact = d1["_key"] == d2["_key"]
    if not (exact or jac >= 0.72 or (cont >= 0.999 and inter >= 3 and jac >= 0.5)): return 0.0
    if d1["source"] == d2["source"]:
        if not exact: return 0.0
        c1, c2 = d1.get("closes_at"), d2.get("closes_at")
        if (c1 or c2) and (c1 or "")[:10] != (c2 or "")[:10]: return 0.0
    if _pconflict(d1["_pn"], d2["_pn"]):
        # different promoters: only merge distinctive titles ("Win a beauty bundle" from two bloggers are two competitions)
        if len(w1 | w2) < 4 or not (exact or jac >= 0.9): return 0.0
    e1, e2 = d1.get("entry_cost"), d2.get("entry_cost")
    if e1 is not None and e2 is not None and abs(e1 - e2) > 0.006: return 0.0
    c1, c2 = d1.get("closes_at"), d2.get("closes_at")
    if c1 and c2:
        try:
            if abs((datetime.fromisoformat(c1) - datetime.fromisoformat(c2)).total_seconds()) > 3.5 * 86400: return 0.0
        except ValueError: pass
    return 1.0 if exact else max(jac, cont * 0.9)

def cluster(recs):
    """recs: raw dicts (already sorted by source priority). Returns list of clusters = {"key","pn","members"}."""
    for d in recs:
        d["_tok"] = tokens(d["title"]); d["_key"] = norm(d["title"]); d["_pn"] = norm_promoter(d.get("promoter"))
    clusters = []; idx = {}
    for d in recs:
        cands = {}
        for w in d["_tok"][0]:
            if len(w) < 4 and not any(len(x) >= 4 for x in d["_tok"][0]) or len(w) >= 4:
                for ci in idx.get(w, ()): cands[ci] = None
        best, bs = None, 0.0
        for ci in cands:
            c = clusters[ci]
            sc = max((similar(d, m) for m in c["members"]), default=0.0)
            # the members of a cluster must not come from the same source unless they are exact repeats (handled in similar)
            if sc > bs: best, bs = c, sc
        if best is not None:
            best["members"].append(d); best["pn"] = best["pn"] or d["_pn"]
        else:
            c = {"key": d["_key"], "pn": d["_pn"], "members": [d]}
            clusters.append(c)
            for w in d["_tok"][0]: idx.setdefault(w, []).append(len(clusters) - 1)
    return clusters
