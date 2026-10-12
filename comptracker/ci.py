"""CI entry point: restore state.json -> run collector -> write competitions.json + state.json.

  python -m comptracker.ci --state STATE_JSON --out OUT_DIR [--only "Source name" ...]
  python -m comptracker.ci --import-db data/comps.db --state STATE_JSON      (one-off seeding from an existing sqlite db)

state.json holds what must persist between runs: raw items (with first_seen -> 'New' flags + dedupe),
the fetch cache, site checks, source status and meta. competitions.json is what the static site loads.
"""
import argparse, json, os, sqlite3, sys, tempfile, logging
from . import collector, sources, util, countries
from .classify import CATEGORIES, TAXONOMY
from .util import now
from datetime import timedelta, datetime

STATE_TABLES = {"raw": 5, "meta": 2, "source_status": 9, "cache": 3, "sitecheck": 3, "seen": 2}

def dump_state(db, path):
    st = {t: [list(r) for r in db.execute(f"SELECT * FROM {t} ORDER BY 1,2" if t in ("raw",) else f"SELECT * FROM {t} ORDER BY 1")] for t in STATE_TABLES}
    tmp = path + ".tmp"
    with open(tmp, "w") as f: json.dump(st, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)

def load_state(db, path):
    if not os.path.exists(path): return False
    st = json.load(open(path))
    for t, n in STATE_TABLES.items():
        rows = [r for r in st.get(t, []) if len(r) == n]     # tolerate state files written by older versions
        if rows: db.executemany(f"INSERT OR REPLACE INTO {t} VALUES({','.join('?' * n)})", rows)
    db.commit()
    return True

def source_state(s, run_info, now_):
    """ok | partial | stale (failing now, but last good data <24h old: still shown, flagged) | down (failing, nothing fresh is shown)."""
    if s["ok"]:
        return "partial" if run_info.get("partial") else "ok"
    if s["last_ok"]:
        age_h = (now_ - datetime.fromisoformat(s["last_ok"])).total_seconds() / 3600
        return "stale" if age_h <= collector.STALE_DROP_H else "down"
    return "down"

def build_site_json(db):
    items = [json.loads(r["data"]) for r in db.execute("SELECT data FROM competitions")]
    meta = {r["k"]: r["v"] for r in db.execute("SELECT * FROM meta")}
    cc = util.CUR["cc"]
    registry = {k for k, v in sources.REGISTRY.items() if v.get("country", "uk") == cc}
    srcs = [dict(r) for r in db.execute("SELECT * FROM source_status ORDER BY source") if r["source"] in registry]
    base = meta.get("baseline_at", "")
    n = now()
    cutoff = (n - timedelta(hours=24)).isoformat()
    for it in items:
        # NEW = first seen in the last 24h only (and only if we genuinely saw it appear: not a long-listed comp we just got round to)
        it["is_new"] = bool(base and it["first_seen"] > base and it["first_seen"] >= cutoff and it.get("new_ok", True))
    items.sort(key=lambda i: i["first_seen"], reverse=True)
    stats = {}
    try: stats = json.loads(meta.get("last_run_stats", "{}"))
    except Exception: pass
    per_run = stats.get("sources", {})
    by_src = {}
    for it in items:
        for s in it["sources"]: by_src[s] = by_src.get(s, 0) + 1
    out_srcs = []
    for s in srcs:
        ri = per_run.get(s["source"], {})
        st = source_state(s, ri, n)
        out_srcs.append(dict(s, errors=json.loads(s["errors"] or "[]"), status=st,
                             stale_since=(s["last_ok"] if st in ("stale", "down") else None),
                             dropped_stale=ri.get("dropped_stale", 0), shown=by_src.get(s["source"], 0)))
    excluded = [dict(source=k, reason=v) for k, v in sources.excluded_for(cc).items()]
    tax = TAXONOMY
    if cc != "uk":      # 'UK breaks' means domestic breaks: label it for this country
        local = "Breaks in " + countries.COUNTRIES[cc]["name"]
        tax = {k: [local if x == "UK breaks" else x for x in v] for k, v in TAXONOMY.items()}
        for it in items:
            if it.get("subcategory") == "UK breaks": it["subcategory"] = local
    return dict(last_updated=meta.get("last_updated"), last_run_start=meta.get("last_run_start"), baseline_at=base,
                country=countries.info(cc), categories=CATEGORIES, subcategories=tax, total=len(items), items=items, by_source=by_src,
                sources=out_srcs, excluded_sources=excluded, stale_after_hours=collector.STALE_DROP_H,
                run_stats={k: v for k, v in stats.items() if k != "sources"})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--country", default="uk", choices=countries.CODES)
    ap.add_argument("--out", help="directory to write competitions.json into")
    ap.add_argument("--import-db")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--cap", action="append", default=[], metavar="KEY=N", help="override a per-source fetch cap, e.g. tpf=20 (testing)")
    ap.add_argument("--min-ratio", type=float, default=0.4, help="abort (no output) if total < ratio * previous total")
    a = ap.parse_args()
    util.set_country(a.country)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    work = tempfile.mkdtemp(prefix="comp-")
    os.environ["COMP_DB"] = os.path.join(work, "comps.db")
    collector.DB = os.environ["COMP_DB"]
    if a.import_db:
        src = sqlite3.connect(f"file:{a.import_db}?mode=ro", uri=True); src.row_factory = sqlite3.Row
        db = collector.connect()
        for t, n in STATE_TABLES.items():
            rows = [list(r) for r in src.execute(f"SELECT * FROM {t}")]
            db.executemany(f"INSERT OR REPLACE INTO {t} VALUES({','.join('?' * n)})", rows)
        db.commit(); dump_state(db, a.state); print("state seeded", a.state); return 0
    db = collector.connect()
    restored = load_state(db, a.state)
    prev_total = db.execute("SELECT count(*) FROM raw").fetchone()[0]
    print(f"state restored={restored} raw_items={prev_total}", flush=True)
    db.close()
    stats = collector.run(a.only, caps={k: int(v) for k, v in (c.split('=', 1) for c in a.cap)})
    db = collector.connect()
    site = build_site_json(db)
    print(json.dumps(dict(stats or {}, sources={s["source"]: dict(count=s["count"], status=s["status"], shown=s["shown"]) for s in site["sources"]}), indent=1))
    if site["total"] == 0 or (prev_total and site["total"] < a.min_ratio * prev_total):
        print(f"ABORT: suspicious result total={site['total']} (prev raw={prev_total}); not publishing", file=sys.stderr); return 2
    dump_state(db, a.state)
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        names = [f"{a.country}.json"] + (["competitions.json"] if a.country == "uk" else [])   # competitions.json: UK, for old links
        for nm in names:
            with open(os.path.join(a.out, nm), "w") as f: json.dump(site, f, ensure_ascii=False, separators=(",", ":"))
    print(a.country, "competitions:", site["total"])
    return 0

if __name__ == "__main__":
    sys.exit(main())
