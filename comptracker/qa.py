"""Entry question + 'likely answer' for a competition page (heuristics only; no paid APIs, no LLM).

extract(html) -> {"q": question, "opts": [options], "hint": answer hint text} or None
likely(q, opts, page_text) -> (answer, method) or ("", "")
Never fills or submits anything: this only reads the public page HTML the collector already fetches.
"""
import re, operator
from bs4 import BeautifulSoup

QWORD = re.compile(r"^(what|which|who|where|when|how|in which|name|can you|true or false|is|are|does|do|complete|fill)\b", re.I)
HINT = re.compile(r"((?:answer\s+)?hint\s*[:\-–]\s*[^.\n]{5,160}|(?:the\s+)?answer (?:can be|is) found[^.\n]{0,140}|"
                  r"find the answer[^.\n]{0,140})", re.I)
BAD = re.compile(r"(cookie|newsletter|marketing|privacy|subscribe|password|email address|consent|captcha|are you (?:over|18)|"
                 r"how did you hear|would you like|agree|terms|do you want|robot)", re.I)

def _clean(t): return re.sub(r"\s+", " ", t or "").strip()

def extract(html):
    if not html or len(html) < 500: return None
    s = BeautifulSoup(html[:600000], "lxml")
    for x in s(["script", "style", "noscript", "svg"]): x.decompose()
    q = ""; opts = []
    # 1) radio groups: the question is the nearest preceding text ending in '?' (legend/label/heading/p)
    radios = s.select("input[type=radio]")
    groups = {}
    for r in radios:
        groups.setdefault(r.get("name") or "", []).append(r)
    for name, rs in groups.items():
        if len(rs) < 2 or len(rs) > 6 or BAD.search(name): continue
        labels = []
        for r in rs:
            lab = None
            if r.get("id"): lab = s.find("label", attrs={"for": r["id"]})
            if lab is None: lab = r.find_parent("label")
            t = _clean(lab.get_text(" ")) if lab else _clean(r.get("value"))
            if t: labels.append(t[:80])
        if len(labels) < 2 or any(BAD.search(l) for l in labels) or set(l.lower() for l in labels) <= {"yes", "no"}: continue
        node = rs[0]; cand = ""
        for prev in node.find_all_previous(string=True, limit=80):
            t = _clean(prev)
            if t.endswith("?") and 8 <= len(t) <= 220 and not BAD.search(t): cand = t; break
        if cand: q, opts = cand, labels; break
    # 2) select menus (WooCommerce 'answer' dropdowns)
    if not q:
        for sel in s.select("select"):
            nm = " ".join([sel.get("name") or "", sel.get("id") or ""]).lower()
            if not re.search(r"(answer|question|quiz|skill)", nm): continue
            o = [_clean(x.get_text()) for x in sel.select("option") if x.get("value") not in (None, "", "0")]
            o = [x for x in o if x and not re.match(r"^(choose|select|please)", x, re.I)]
            if 2 <= len(o) <= 6:
                for prev in sel.find_all_previous(string=True, limit=60):
                    t = _clean(prev)
                    if t.endswith("?") and 8 <= len(t) <= 220 and not BAD.search(t): q, opts = t, o[:6]; break
            if q: break
    text = _clean(s.get_text(" "))
    # 3) explicit 'Question:' / 'Q:' text (free-text answers)
    if not q:
        m = re.search(r"(?:\bQuestion\s*[:\-–]|\bQ\s*[:.])\s*([^?]{8,200}\?)", text)
        if m and not BAD.search(m.group(1)): q = _clean(m.group(1))
    hint = ""
    m = HINT.search(text)
    if m: hint = _clean(m.group(1))[:180]
    if not q: return None
    return {"q": q[:220], "opts": opts, "hint": hint, "_text": text}

_OPS = {"+": operator.add, "plus": operator.add, "-": operator.sub, "minus": operator.sub, "x": operator.mul, "×": operator.mul,
        "*": operator.mul, "times": operator.mul, "multiplied by": operator.mul, "/": operator.truediv, "÷": operator.truediv, "divided by": operator.truediv}
FACTS = {  # tiny, uncontroversial general-knowledge table (keyword set -> answer)
    ("capital", "france"): "Paris", ("capital", "england"): "London", ("capital", "united kingdom"): "London", ("capital", "uk"): "London",
    ("capital", "germany"): "Berlin", ("capital", "italy"): "Rome", ("capital", "spain"): "Madrid", ("capital", "ireland"): "Dublin",
    ("capital", "scotland"): "Edinburgh", ("capital", "wales"): "Cardiff", ("capital", "netherlands"): "Amsterdam",
    ("capital", "australia"): "Canberra", ("capital", "new zealand"): "Wellington", ("capital", "japan"): "Tokyo",
    ("capital", "usa"): "Washington, D.C.", ("days", "week"): "7", ("months", "year"): "12", ("legs", "spider"): "8",
    ("wheels", "bicycle"): "2", ("wheels", "tricycle"): "3", ("wheels", "car"): "4", ("colour", "sky"): "Blue", ("color", "sky"): "Blue",
    ("colour", "grass"): "Green", ("planet", "red"): "Mars", ("largest", "planet"): "Jupiter", ("legs", "dog"): "4", ("legs", "cat"): "4",
    ("sides", "triangle"): "3", ("sides", "square"): "4", ("sides", "hexagon"): "6", ("sides", "pentagon"): "5", ("sides", "octagon"): "8",
    ("hours", "day"): "24", ("minutes", "hour"): "60", ("seconds", "minute"): "60", ("freezes", "water"): "0°C",
}
WORDNUM = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}

def _num(t):
    t = t.strip().lower()
    return float(t) if re.fullmatch(r"\d+(?:\.\d+)?", t) else WORDNUM.get(t)

def likely(q, opts, text=""):
    ql = q.lower()
    m = re.search(r"(\d+|\b(?:" + "|".join(WORDNUM) + r")\b)\s*(\+|-|x|×|\*|/|÷|plus|minus|times|multiplied by|divided by)\s*(\d+|\b(?:" + "|".join(WORDNUM) + r")\b)", ql)
    if m and _num(m.group(1)) is not None and _num(m.group(3)) is not None:
        try:
            v = _OPS[m.group(2)](_num(m.group(1)), _num(m.group(3))); v = int(v) if float(v).is_integer() else round(v, 2)
            ans = str(v)
            if opts:
                hit = [o for o in opts if re.search(r"(?<!\d)" + re.escape(ans) + r"(?!\d)", o) or (o.strip().lower() in WORDNUM and WORDNUM[o.strip().lower()] == v)]
                if len(hit) == 1: return hit[0], "arithmetic"
            else: return ans, "arithmetic"
        except Exception: pass
    for keys, ans in FACTS.items():
        if all(re.search(r"\b" + re.escape(k) + r"\b", ql) for k in keys):
            if opts:
                hit = [o for o in opts if o.strip().lower().startswith(ans.lower()) or ans.lower() in o.lower().split()]
                if len(hit) == 1: return hit[0], "general knowledge"
            else: return ans, "general knowledge"
    if opts and text:     # exactly one option is mentioned elsewhere on the page (e.g. in the prize description)
        body = text.lower().replace(q.lower(), " ")
        for o in opts: body = body.replace(o.lower(), "\x00" + o.lower(), 1) if False else body
        cnt = {o: len(re.findall(r"\b" + re.escape(o.lower()) + r"\b", body)) for o in opts if len(o) >= 3}
        # each option appears once inside the form itself; more mentions = mentioned in the description
        extra = [o for o, c in cnt.items() if c >= 2]
        if len(extra) == 1: return extra[0], "mentioned on the page"
    return "", ""

def from_listing(question="", answer_text="", instr="", src="", explicit=False):
    """Q&A as shown by a listing site. 'The answer is : X' (or an explicit 'Answer:' field) -> likely answer; other advice -> hint."""
    question = _clean(question); a = _clean(answer_text)
    if not question and not a: return None
    ans = hint = ""
    m = re.match(r"^(?:the\s+)?answers?\s+(?:is|are)\s*[:\-–]?\s*(.+)$", a, re.I)
    if m: ans = m.group(1).strip(" .")
    elif explicit and a: ans = a
    elif a and len(a) <= 40 and re.search(r"answer|question", instr or "", re.I) and not re.search(r"\b(enter|visit|like|follow|share|register|comment|tag|click|blog|website|site|facebook|instagram|twitter|tiktok|youtube|form|email|e-?mail|newsletter|daily|weekly|multiple|online|post|app|text|sms|phone|purchase|receipt|login|log in)\b", a, re.I):
        ans = a      # ThePrizeFinder 'Advice' on a question comp is usually the answer itself
    elif a: hint = a
    if not ans and not hint and not question: return None
    if not question and not ans: return None      # advice that is just entry tips: not a Q&A
    d = {"q": question[:220], "opts": [], "a": ans[:120], "hint": hint[:180], "method": f"given on {src}" if ans else "", "src": src}
    if question and not ans:
        g, meth = likely(question, [])
        if g: d.update(a=g, method=meth)
    return d

def from_page(html, src="promoter page"):
    x = extract(html)
    if not x: return None
    g, meth = likely(x["q"], x["opts"], x.get("_text", ""))
    return {"q": x["q"], "opts": x["opts"][:6], "a": g, "hint": x["hint"], "method": meth, "src": src}
