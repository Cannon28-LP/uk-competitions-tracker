"""Test harness for per-country pages (TEST ONLY - the site itself has no country switcher or debug parameter).

Needs:  pip install playwright   and a system Chrome (CHROME=/path, default /usr/bin/google-chrome)
Run:    python tests/country/run_country_test.py DATA_DIR      (DATA_DIR holds uk.json, de.json, ... as the collector writes them)

Each country is simulated by emulating the browser's time zone and locale (what a real visitor's browser reports),
then the real web/index.html is loaded from a throw-away local server. Checks: the right list loads (and ONLY that
country's data file is requested), currency/time-zone labels, local tips and report links, address labels in 'My details'."""
import os, sys, pathlib, shutil, tempfile, threading, http.server, socketserver, json
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "_site" / "data")
SITE = pathlib.Path(tempfile.mkdtemp(prefix="ukct-cc-"))
(SITE / "data").mkdir()
for f in SRC.glob("*.json"):
    if len(f.stem) == 2: shutil.copy(f, SITE / "data" / f.name)
shutil.copy(ROOT / "web" / "index.html", SITE / "index.html")

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=str(SITE), **k)
    def log_message(self, *a): pass
srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H); PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

# (case, timezone, locale, expected country, expected symbol, an expected 'My details' label fragment)
CASES = [
    ("uk", "Europe/London", "en-GB", "uk", "£", "County"),
    ("de", "Europe/Berlin", "de-DE", "de", "€", "PLZ"),
    ("fr", "Europe/Paris", "fr-FR", "fr", "€", "code postal"),
    ("nl", "Europe/Amsterdam", "nl-NL", "nl", "€", "woonplaats"),
    ("ie", "Europe/Dublin", "en-IE", "ie", "€", "Eircode"),
    ("it", "Europe/Rome", "it-IT", "it", "€", "CAP"),
    ("au", "Australia/Perth", "en-AU", "au", "$", "State / territory"),
    ("nz", "Pacific/Auckland", "en-NZ", "nz", "$", "Suburb"),
    ("fallback: UTC zone + German locale", "UTC", "de-DE", "de", "€", "PLZ"),
    ("fallback: unknown zone (New York) -> UK", "America/New_York", "en-US", "uk", "£", "County"),
    ("traveller: German locale in London zone -> UK", "Europe/London", "de-DE", "uk", "£", "County"),
]
NAMES = {"uk": "UK Prize", "de": "Germany", "fr": "France", "nl": "Netherlands", "ie": "Ireland", "it": "Italy", "au": "Australia", "nz": "New Zealand"}
ok = bad = 0
def check(cond, msg):
    global ok, bad
    print(("PASS " if cond else "FAIL ") + msg); ok += bool(cond); bad += (not cond)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
    for name, tz, loc, cc, sym, lab in CASES:
        ctx = b.new_context(timezone_id=tz, locale=loc)
        pg = ctx.new_page(); reqs = []
        pg.on("request", lambda r: reqs.append(r.url))
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{PORT}/index.html")
        pg.wait_for_selector(".card", timeout=20000)
        exp = json.load(open(SITE / "data" / f"{cc}.json"))
        h1 = pg.inner_text("#h1"); count = pg.inner_text("#count"); upd = pg.inner_text("#stats")
        data_reqs = sorted({u.split("?")[0].rsplit("/", 1)[-1] for u in reqs if "/data/" in u or "competitions.json" in u})
        check(not errs, f"[{name}] no JS errors {errs[:1]}")
        check(NAMES[cc] in h1, f"[{name}] heading is {cc}: {h1!r}")
        check(data_reqs == [f"{cc}.json"], f"[{name}] only {cc}.json requested: {data_reqs}")
        live = pg.evaluate("ITEMS.length")
        check(live > 0 and abs(live - len(exp['items'])) <= len(exp['items']) * 0.2 + 2, f"[{name}] items loaded {live} (file {len(exp['items'])})")
        ndir = pg.evaluate("ITEMS.filter(i => !i._direct).length")
        shown_n = pg.evaluate("LIST.length")
        check(pg.evaluate("LIST.every(i => i._direct)"), f"[{name}] by default only direct promoter links are listed ({shown_n} shown, {ndir} hidden)")
        check(not pg.query_selector(".btn-via"), f"[{name}] no 'via listing site' buttons by default")
        if ndir:
            pg.check("#nd"); pg.wait_for_timeout(200)
            check(pg.evaluate("LIST.length") > shown_n and pg.evaluate("LIST.some(i => !i._direct) && card(LIST.find(i => !i._direct)).includes('via listing site')"), f"[{name}] toggle shows items without a direct link, labelled 'via listing site'")
            pg.uncheck("#nd"); pg.wait_for_timeout(100)
        iow = sum(1 for i in exp["items"] if "iow" in (i.get("tags") or []))
        hn = sum(1 for i in exp["items"] if "hampshire" in (i.get("tags") or []))
        check(pg.is_hidden("#hantsBtn") == (cc != "uk" or not hn), f"[{name}] Hampshire chip {'shown' if cc == 'uk' and hn else 'hidden'}")
        check(pg.is_hidden("#iowBtn") == (cc != "uk" or not iow), f"[{name}] Isle of Wight chip {'shown' if cc == 'uk' and iow else 'hidden'}")
        if pg.evaluate("LIST.length") == 0: pg.check("#nd"); pg.wait_for_timeout(200)
        txt = pg.inner_text("#grid")
        check(sym in txt and ((sym == "£") or "£" not in txt), f"[{name}] currency {sym} on cards (no £ outside UK)")
        check(sym in pg.inner_text("#prizeBox"), f"[{name}] prize filter shows {sym}")
        tips = pg.inner_html("#tips")
        if cc == "uk": check("actionfraud.police.uk" in tips, f"[{name}] UK keeps its original tips/links")
        for t, u in ([] if cc == "uk" else (exp.get("country") or {}).get("report", [])):
            check(u in tips, f"[{name}] report link {u}")
        cats = pg.evaluate("ITEMS.filter(i => i.category && i.category !== 'Other').length / Math.max(1, ITEMS.length)")
        check(cats >= 0.75, f"[{name}] classified (not 'Other'): {cats:.0%}")
        radios = pg.evaluate("ITEMS.some(i => i._radio)")
        check(pg.is_hidden("#radioBtn") != radios, f"[{name}] radio toggle {'shown' if radios else 'hidden'}")
        note = pg.inner_text("#ccNote")
        check("time zone" in note and "IP" in note, f"[{name}] privacy note shown")
        check(not pg.query_selector("select#country, [data-country-switch]") and "?cc=" not in pg.content(), f"[{name}] no country switcher")
        pg.click("#mdBtn")
        rows = pg.inner_text("#mdRows")
        check(lab in rows, f"[{name}] My details has local label {lab!r}")
        vals = pg.evaluate("[...document.querySelectorAll('#mdRows input, #mdRows select')].map(e => e.value).join('')")
        check(vals == "", f"[{name}] My details empty by default")
        # closing-time label uses the country's zone
        pg.keyboard.press("Escape")
        ctx.close()
    b.close()
print(f"\n{ok}/{ok + bad} checks passed")
sys.exit(1 if bad else 0)
