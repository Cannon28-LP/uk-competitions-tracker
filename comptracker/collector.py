import os, sys, json, sqlite3, time, re, traceback, logging, fcntl
from datetime import datetime, timedelta
from . import sources as S
from .util import Fetcher, now, LONDON, norm, norm_promoter, prize_value_from_text
from .classify import classify, prize_type
from . import safety

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("COMP_DB") or os.path.join(BASE, "data", "comps.db")
log = logging.getLogger("comp")

SRC_PRIORITY = ["Radio: Global (Heart, Capital, Smooth, Classic FM, Radio X…)", "Radio: Bauer / Hello Rayo (Kiss, Absolute, Hits, Magic, Jazz FM, Clyde…)", "Radio: talkSPORT", "ITV Win", "Dream Car Giveaways", "Omaze", "Nitrous Competitions", "Compete For Cars", "FindCompetitions", "Competition Showroom",
                "BOTB (via Showroom)", "7days Performance (via Showroom)", "Loquax Win-a-House", "ThePrizeFinder", "MSE Competitions Time",
                "Competitions Time", "Competitions Today", "olive magazine", "Latest Deals", "Loquax"]
PREC_RANK = {"exact": 0, "date": 1, "approx": 2, "": 3}

def connect():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB, timeout=60)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS raw(source TEXT, skey TEXT, data TEXT, first_seen TEXT, last_seen TEXT, PRIMARY KEY(source, skey));
    CREATE TABLE IF NOT EXISTS competitions(id TEXT PRIMARY KEY, data TEXT, first_seen TEXT, closes_at TEXT, last_seen TEXT);
    CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
    CREATE TABLE IF NOT EXISTS source_status(source TEXT PRIMARY KEY, kind TEXT, url TEXT, note TEXT, last_run TEXT, ok INTEGER, count INTEGER, errors TEXT, last_ok TEXT);
    CREATE TABLE IF NOT EXISTS cache(url TEXT PRIMARY KEY, data TEXT, fetched_at TEXT);
    CREATE TABLE IF NOT EXISTS sitecheck(domain TEXT PRIMARY KEY, data TEXT, fetched_at TEXT);
    """)
    return c

def iso(dt): return dt.isoformat(timespec="seconds") if dt else None

class Ctx:
    def __init__(self, name, fetcher, db, caps):
        self.name = name; self.f = fetcher; self.db = db; self.caps = caps; self.meta = {}
        self.errors = []; self._cache = {}
        self.used = {}
    def get(self, url):
        n0 = len(self.f.errors)
        r = self.f.get(url)
        if r is None: self.errors.extend(self.f.errors[n0:])
        return r
    def cap(self, k, default): return self.caps.get(k, default)
    def cache_get(self, url):
        if url in self._cache: return self._cache[url]
        row = self.db.execute("SELECT data FROM cache WHERE url=?", (url,)).fetchone()
        v = json.loads(row[0]) if row else None
        self._cache[url] = v
        return v
    def cache_put(self, url, data):
        self._cache[url] = data
        self.db.execute("INSERT OR REPLACE INTO cache VALUES(?,?,?)", (url, json.dumps(data), iso(now())))
        self.db.commit()
    def cache_age_hours(self, url):
        row = self.db.execute("SELECT fetched_at FROM cache WHERE url=?", (url,)).fetchone()
        if not row: return None
        return (now() - datetime.fromisoformat(row[0])).total_seconds() / 3600
    def cache_age(self, url):
        a = self.cache_age_hours(url)
        return -1 if a is None else (1e6 - a)  # uncached first, then oldest first

def serialise(rec_):
    d = dict(rec_)
    d["closes_at"] = iso(d["closes_at"]) if d.get("closes_at") else None
    return d

def run(only=None, caps=None):
    lock = open(os.path.join(os.path.dirname(DB), "collector.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log.warning("another run in progress; exiting"); return None
    db = connect()
    t0 = now()
    caps = caps or {}
    fetcher = Fetcher()
    first_run = db.execute("SELECT v FROM meta WHERE k='baseline_at'").fetchone() is None
    prev_run = db.execute("SELECT v FROM meta WHERE k='last_run_start'").fetchone()
    db.execute("INSERT OR REPLACE INTO meta VALUES('last_run_start',?)", (iso(t0),))
    db.execute("INSERT OR REPLACE INTO meta VALUES('prev_run_start',?)", (prev_run[0] if prev_run else "",))
    db.commit()
    summary = {}
    for name, spec in S.REGISTRY.items():
        if only and name not in only: continue
        ctx = Ctx(name, fetcher, db, caps)
        t1 = time.time()
        items = []; err = None
        try:
            items = spec["fn"](ctx) or []
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            log.error("source %s failed: %s\n%s", name, err, traceback.format_exc())
        errs = list(dict.fromkeys(ctx.errors))
        # normalise + drop blocked/scammy
        kept = []; blocked_n = 0
        for it in items:
            it["title"] = re.sub(r"\s+", " ", it["title"]).strip()
            if not it["title"]: continue
            why = safety.blocked(it)
            if why:
                blocked_n += 1; log.info("blocked [%s]: %s (%s)", name, it["title"], why); continue
            kept.append(it)
        # dedupe within source
        seenk = {}
        for it in kept: seenk[it["skey"]] = it
        kept = list(seenk.values())
        prev_count = db.execute("SELECT count(*) FROM raw WHERE source=?", (name,)).fetchone()[0]
        n = now()
        ok = err is None and len(kept) > 0
        partial = bool(errs)
        if kept and err is None:
            for it in kept:
                ser = serialise(it)
                row = db.execute("SELECT first_seen FROM raw WHERE source=? AND skey=?", (name, it["skey"])).fetchone()
                fs = row[0] if row else iso(n)
                db.execute("INSERT OR REPLACE INTO raw VALUES(?,?,?,?,?)", (name, it["skey"], json.dumps(ser), fs, iso(n)))
            # removal: items no longer at source -- only when the source fetched cleanly and didn't collapse
            if not partial and len(kept) >= 0.4 * prev_count:
                db.execute("DELETE FROM raw WHERE source=? AND last_seen<?", (name, iso(n)))
            else:
                log.warning("%s: skipping removal-from-source (partial=%s, kept=%d prev=%d)", name, partial, len(kept), prev_count)
        status_note = spec["note"]
        row = db.execute("SELECT last_ok FROM source_status WHERE source=?", (name,)).fetchone()
        last_ok = iso(n) if ok else (row[0] if row else None)
        db.execute("INSERT OR REPLACE INTO source_status VALUES(?,?,?,?,?,?,?,?,?)",
                   (name, spec["kind"], spec["url"], status_note, iso(n), 1 if ok else 0, len(kept),
                    json.dumps(([err] if err else []) + errs[:6] + ([f"{blocked_n} listing(s) excluded by safety filter"] if blocked_n else []) + [f"{k}={v}" for k, v in ctx.meta.items()]), last_ok))
        db.commit()
        summary[name] = dict(count=len(kept), ok=ok, errors=errs[:3] + ([err] if err else []), secs=round(time.time() - t1, 1))
        log.info("source %-34s items=%-4d ok=%s errs=%d %.1fs", name, len(kept), ok, len(errs), time.time() - t1)
    stats = merge_and_store(db, fetcher, t0)
    if first_run:  # items found by the very first full run are the baseline, not "new"
        db.execute("INSERT OR REPLACE INTO meta VALUES('baseline_at',?)", (iso(now()),)); db.commit()
    db.execute("INSERT OR REPLACE INTO meta VALUES('last_updated',?)", (iso(now()),))
    db.execute("INSERT OR REPLACE INTO meta VALUES('last_run_stats',?)", (json.dumps(dict(stats, sources=summary, requests=fetcher.count)),))
    db.commit()
    return stats

# ------------------------------------------------------------------ merge
def _prio(src):
    return SRC_PRIORITY.index(src) if src in SRC_PRIORITY else 99

def merge_and_store(db, fetcher, t0):
    n = now()
    rows = db.execute("SELECT source, skey, data, first_seen FROM raw").fetchall()
    recs = []; expired = 0
    for r in rows:
        d = json.loads(r["data"]); d["source"] = r["source"]; d["raw_first_seen"] = r["first_seen"]
        if d.get("closes_at") and datetime.fromisoformat(d["closes_at"]) < n:
            db.execute("DELETE FROM raw WHERE source=? AND skey=?", (r["source"], r["skey"])); expired += 1; continue
        recs.append(d)
    # cluster across sources
    recs.sort(key=lambda d: (_prio(d["source"]), d["title"]))
    clusters = []   # list of dict: key, members
    index = {}
    for d in recs:
        key = norm(d["title"])
        pn = norm_promoter(d.get("promoter"))
        placed = False
        for c in index.get(key, []):
            if d["source"] in {m["source"] for m in c["members"]}: continue
            cpn = c["pn"]
            if pn and cpn and pn != cpn and pn not in cpn and cpn not in pn: continue
            ca = [m.get("entry_cost") for m in c["members"] if m.get("entry_cost") is not None]
            if d.get("entry_cost") is not None and ca and all(abs(d["entry_cost"] - x) > 0.006 for x in ca): continue
            c["members"].append(d); c["pn"] = c["pn"] or pn; placed = True; break
        if not placed:
            c = {"key": key, "pn": pn, "members": [d]}
            clusters.append(c); index.setdefault(key, []).append(c)
    out = []
    for c in clusters:
        ms = c["members"]
        m0 = ms[0]
        item = {"title": m0["title"], "sources": [m["source"] for m in ms]}
        def first(field, cond=lambda v: v not in (None, "")):
            for m in ms:
                if cond(m.get(field)): return m[field]
            return None if field not in ("promoter", "entry_note", "entry_cost_text", "prize_desc") else ""
        item["promoter"] = first("promoter") or ""
        item["prize_desc"] = first("prize_desc") or m0["title"]
        item["prize_value"] = first("prize_value")
        item["image"] = first("image") or ""   # prize picture, hot-linked from the source; the site shows a placeholder when absent
        # link preference: operator-direct > any non-aggregator > aggregator
        links = []
        for m in ms:
            if m.get("link"):
                d = safety.domain(m["link"])
                links.append((0 if not safety.is_aggregator_domain(d) else 1, _prio(m["source"]), m["link"]))
        links.sort()
        item["link"] = links[0][2] if links else ""
        item["source_links"] = {m["source"]: m["link"] for m in ms if m.get("link")}
        et = [m.get("entry_type") for m in ms if m.get("entry_type")]
        item["entry_type"] = "paid" if "paid" in et else ("free" if "free" in et else "")
        # paid wins over free only if cost info says so; a FREE-priced record from operator beats aggregator 'free' default
        costs = [m for m in ms if m.get("entry_cost") is not None]
        if costs:
            item["entry_cost"] = costs[0]["entry_cost"]; item["entry_cost_text"] = costs[0].get("entry_cost_text", "")
            item["entry_type"] = "free" if costs[0]["entry_cost"] == 0 else "paid"
        else:
            item["entry_cost"] = None; item["entry_cost_text"] = ""
        # closing: best precision
        cl = [m for m in ms if m.get("closes_at")]
        cl.sort(key=lambda m: (PREC_RANK.get(m.get("closes_precision", ""), 3), _prio(m["source"])))
        item["closes_at"] = cl[0]["closes_at"] if cl else None
        item["closes_precision"] = cl[0].get("closes_precision", "") if cl else ""
        ts = [m for m in ms if m.get("tickets_sold") is not None]
        if ts:
            item["tickets_sold"] = ts[0]["tickets_sold"]; item["tickets_total"] = ts[0].get("tickets_total") or first("tickets_total")
        else:
            item["tickets_sold"] = None; item["tickets_total"] = first("tickets_total")
        item["pct_sold"] = first("pct_sold")
        if item["pct_sold"] is None and item["tickets_sold"] is not None and item["tickets_total"]:
            item["pct_sold"] = round(100.0 * item["tickets_sold"] / item["tickets_total"], 1)
        notes = []
        for m in ms:
            if m.get("entry_note") and m["entry_note"] not in notes: notes.append(m["entry_note"])
        item["entry_note"] = " | ".join(notes[:3])
        extra = {}
        for m in ms:
            for k, v in (m.get("extra") or {}).items():
                if v: extra[k] = v
        item["extra"] = extra
        item["station"] = ", ".join(dict.fromkeys(x.strip() for m in ms for x in (m.get("station") or "").split(",") if x.strip()))
        tags = sorted({t for m in ms for t in (m.get("tags") or [])})
        item["tags"] = tags
        if item["prize_value"] is None:
            item["prize_value"] = prize_value_from_text(item["title"])
        item["category"] = classify(item["title"], item["prize_desc"] if item["prize_desc"] != item["title"] else "")
        item["prize_type"] = prize_type(item["category"])
        item["first_seen"] = min(m["raw_first_seen"] for m in ms)
        item["source"] = ms[0]["source"]
        item["id"] = __import__("hashlib").sha1((c["key"] + "|" + (c["pn"] or "") + "|" + ms[0]["source"] + "|" + ms[0].get("skey", "")).encode()).hexdigest()[:16]
        out.append(item)
    # site checks (T&Cs / company no / free route) for paid items on operator domains
    sitechecks = check_sites(db, fetcher, [it for it in out if it["entry_type"] == "paid"])
    for it in out:
        d = safety.domain(it["link"])
        it["domain"] = d
        site = sitechecks.get(d)
        it["safety"] = safety.assess(it, site)
        if site:
            it["terms_url"] = site.get("terms") or ""
            it["company_no"] = site.get("company") or ""
    # persist (replace table => deletes anything no longer in raw/expired)
    db.execute("DELETE FROM competitions")
    for it in out:
        db.execute("INSERT INTO competitions VALUES(?,?,?,?,?)", (it["id"], json.dumps(it), it["first_seen"], it["closes_at"], iso(n)))
    prev_ids = set()
    db.commit()
    brow = db.execute("SELECT v FROM meta WHERE k='baseline_at'").fetchone()
    baseline = brow[0] if brow else None
    new_this_run = sum(1 for it in out if it["first_seen"] >= iso(t0))
    stats = dict(total=len(out), new_this_run=new_this_run, expired_removed=expired, baseline_run=(baseline is None))
    log.info("merged: %s", stats)
    return stats

def check_sites(db, fetcher, items, cap=30):
    doms = {}
    for it in items:
        d = safety.domain(it["link"])
        if d and not safety.is_aggregator_domain(d) and "/" not in d:
            doms.setdefault(d, it["link"])
    res = {}
    todo = []
    for d, link in doms.items():
        row = db.execute("SELECT data, fetched_at FROM sitecheck WHERE domain=?", (d,)).fetchone()
        if row and (now() - datetime.fromisoformat(row[1])).days < 7:
            res[d] = json.loads(row[0])
        else:
            todo.append((d, link))
    for d, link in todo[:cap]:
        data = {"checked": False}
        base = re.match(r"https?://[^/]+", link).group(0)
        r = fetcher.get(base + "/")
        if r is not None:
            from bs4 import BeautifulSoup
            s = BeautifulSoup(r.text, "lxml")
            data["checked"] = True
            terms = ""
            for a in s.select("a[href]"):
                t = (a.get_text(" ", strip=True) + " " + a["href"]).lower()
                if re.search(r"terms|t&c|t&amp;c|conditions|rules", t) and not terms:
                    terms = a["href"] if a["href"].startswith("http") else base + "/" + a["href"].lstrip("/")
            data["terms"] = terms
            txt = s.get_text(" ", strip=True)
            m = re.search(r"(?:company|registration|reg\.?)\s*(?:no\.?|number|#)?\s*:?\s*(?:SC|NI)?(\d{6,8})", txt, re.I)
            data["company"] = m.group(1) if m else ""
            data["free_route"] = bool(re.search(r"free (?:postal )?entry|postal entry|no purchase necessary|free route", txt + " " + r.text[:200000], re.I))
        db.execute("INSERT OR REPLACE INTO sitecheck VALUES(?,?,?)", (d, json.dumps(data), iso(now())))
        res[d] = data
    db.commit()
    return res

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    only = sys.argv[1:] or None
    print(json.dumps(run(only), indent=1))
