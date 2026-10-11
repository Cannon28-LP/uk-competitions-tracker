"""End-to-end test of the 'My details' panel + userscript, DUMMY DATA ONLY ('Test User').

Needs:  pip install playwright   and a system Chrome/Chromium (set CHROME=/path if not /usr/bin/google-chrome)
Run:    python tests/autofill/run_autofill_test.py [path/to/competitions.json]

How it works: a throw-away local server serves web/index.html + a one-item competitions.json whose 'Enter' link points at the sample
form on a *different origin* (localhost vs 127.0.0.1). The real userscript is injected with a tiny GM_* shim (storage kept by the test
server, only in this test) and its tracker origin pointed at the local server. Nothing leaves this machine."""
import json, os, sys, threading, http.server, socketserver, urllib.parse, pathlib, re
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
DUMMY = dict(title="Mrs", first="Test", last="User", email="test.user@example.invalid", phone="07000 000000", addr1="1 Test Street",
             addr2="Testville", town="Testtown", county="Testshire", postcode="TE1 1ST", dob="1990-02-03")

# ---------------------------------------------------------------- local server (static + GM shim storage)
GM = {}
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def translate_path(self, path):
        return str(SITE / urllib.parse.urlsplit(path).path.lstrip("/"))
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Access-Control-Allow-Headers", "*")
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        if u.path == "/__gm":
            k = urllib.parse.parse_qs(u.query).get("k", [""])[0]
            body = json.dumps({"v": GM.get(k, "")}).encode()
            self.send_response(200); self._cors(); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        return super().do_GET()
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); data = json.loads(self.rfile.read(n) or b"{}")
        if data.get("del"): GM.pop(data["k"], None)
        else: GM[data["k"]] = data["v"]
        self.send_response(200); self._cors(); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"{}")

import tempfile, shutil
SITE = pathlib.Path(tempfile.mkdtemp(prefix="ukct-test-"))

def build_site(src_json):
    d = json.load(open(src_json))
    it = dict(d["items"][0])
    FORM = "http://localhost:%d/sample-form.html"
    it.update(title="Win a dummy prize (test)", link=FORM % PORT, all_links=[], source_links={}, closes_at=None)
    d["items"] = [it]; d["total"] = 1
    json.dump(d, open(SITE / "competitions.json", "w"))
    shutil.copy(ROOT / "web" / "index.html", SITE / "index.html")
    for f in ("sample-form.html", "sample-form-b.html"):
        shutil.copy(ROOT / "tests" / "autofill" / f, SITE / f)

SHIM = """
(function(){
  var B = "http://127.0.0.1:%d/__gm";
  function x(m, u, b){ var r = new XMLHttpRequest(); r.open(m, u, false); if (b) r.setRequestHeader("Content-Type","text/plain"); r.send(b || null); return r.responseText; }
  window.GM_getValue = function(k, d){ try { var v = JSON.parse(x("GET", B + "?k=" + encodeURIComponent(k))).v; return v === "" || v == null ? d : v; } catch(e){ return d; } };
  window.GM_setValue = function(k, v){ x("POST", B, JSON.stringify({k:k, v:v})); };
  window.GM_deleteValue = function(k){ x("POST", B, JSON.stringify({k:k, del:true})); };
  window.GM_registerMenuCommand = function(){};
})();
"""

def userscript_for_test():
    s = (ROOT / "autofill" / "uk-comp-autofill.user.js").read_text()
    s = s.replace('"https://cannon28-lp.github.io"', '"http://127.0.0.1:%d"' % PORT).replace('"/uk-competitions-tracker/"', '"/"')
    assert "127.0.0.1" in s
    return SHIM % PORT + '\nwindow.addEventListener("load", function(){\n' + s + '\n});'

checks = []
def check(name, cond, extra=""):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ((" – " + str(extra)) if (extra and not cond) else ""))

def val(page, sel): return page.eval_on_selector(sel, "e => e.value")
def checked(page, sel): return page.eval_on_selector(sel, "e => e.checked")

def main():
    global PORT
    srv = socketserver.ThreadingTCPServer(("0.0.0.0", 0), H); srv.daemon_threads = True
    PORT = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    src = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "tests" / "autofill" / "competitions.sample.json")
    build_site(src)
    base = "http://127.0.0.1:%d" % PORT
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox", "--disable-gpu"])
        ctx = br.new_context(permissions=["clipboard-read", "clipboard-write"], base_url=base)
        ctx.add_init_script(userscript_for_test())
        leaked = []
        def watch(req):
            if "/__gm" in req.url: return
            blob = req.url + " " + (req.post_data or "")
            if re.search(r"Test|User|example\.invalid|TE1|Testtown|07000", blob):
                leaked.append(req.url)
        ctx.on("request", watch)

        # ---------- 1. tracker page: panel is empty by default, then save dummy details
        page = ctx.new_page(); errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(base + "/index.html"); page.wait_for_selector(".card", timeout=15000)
        check("page loads with a card and no JS errors", not errs, errs)
        check("userscript announces itself to the page", page.eval_on_selector("html", "e => !!e.getAttribute('data-ukct-autofill')"))
        page.click("#mdBtn"); page.wait_for_selector("dialog#md[open]")
        empty = page.eval_on_selector_all("#mdRows input, #mdRows select", "els => els.every(e => e.value === '')")
        check("My details panel is EMPTY by default", empty)
        check("localStorage has no details before the user types", page.evaluate("localStorage.getItem('ukct.details.v1')") is None)
        check("privacy note is shown", "never sent to our server" in page.inner_text("dialog#md .priv"))
        page.wait_for_function("document.querySelector('#mdUs').textContent.includes('detected')", timeout=5000)
        check("panel shows userscript detected", "detected" in page.inner_text("#mdUs"))
        for k, v in DUMMY.items():
            if k == "title": page.select_option("#md_title", v)
            else: page.fill("#md_" + k, v)
        page.wait_for_timeout(700)
        stored = json.loads(page.evaluate("localStorage.getItem('ukct.details.v1')"))
        check("details saved in localStorage", stored.get("first") == "Test" and stored.get("postcode") == "TE1 1ST")
        gm = json.loads(GM.get("ukct_details_v1", "{}"))
        check("details synced to the userscript store (not to the web)", gm.get("email") == DUMMY["email"] and gm.get("dob") == DUMMY["dob"])
        # copy buttons
        page.click('[data-copy="email"]'); page.wait_for_timeout(200)
        check("per-field copy works", page.evaluate("navigator.clipboard.readText()") == DUMMY["email"])
        page.click("#mdCopyAll"); page.wait_for_timeout(200)
        allc = page.evaluate("navigator.clipboard.readText()")
        check("copy all works (labelled lines)", "First name: Test" in allc and "Postcode: TE1 1ST" in allc and allc.count("\n") == 10, allc)
        page.keyboard.press("Escape")

        # ---------- 2. quick enter: click the card's Enter button -> new tab on ANOTHER origin gets filled
        with ctx.expect_page() as pi:
            page.click(".card .btn[data-enter]")
        fp = pi.value; fp.wait_for_load_state("load"); fp.wait_for_selector("#fn")
        fp.wait_for_function("document.querySelectorAll('[data-ukct-filled]').length >= 8", timeout=8000)
        check("form opened on a different origin", "localhost" in fp.url)
        exp = {"#fn": "Test", "#ln": "User", "#em": DUMMY["email"], "#em2": DUMMY["email"], "#ph": DUMMY["phone"], "#a1": "1 Test Street",
               "#a2": "Testville", "#tw": "Testtown", "#co": "Testshire", "#pc": "TE1 1ST"}
        for sel, want in exp.items(): check(f"filled {sel}", val(fp, sel) == want, val(fp, sel))
        check("title select = Mrs", val(fp, "#t") == "Mrs" or fp.eval_on_selector("#t", "e => e.options[e.selectedIndex].text") == "Mrs")
        check("DOB selects = 3 Feb 1990", fp.eval_on_selector("[name=dob_day]", "e=>e.options[e.selectedIndex].text") == "3" and
              fp.eval_on_selector("[name=dob_month]", "e=>e.options[e.selectedIndex].text") == "February" and fp.eval_on_selector("[name=dob_year]", "e=>e.options[e.selectedIndex].text") == "1990")
        check("honeypot untouched", val(fp, "#hpf") == "")
        check("captcha field untouched", val(fp, "#cap") == "")
        check("tie-breaker textarea untouched", val(fp, "#ans") == "")
        check("promo code untouched", val(fp, "#promo") == "")
        check("marketing checkbox NOT ticked", checked(fp, "#news") is False)
        check("terms checkbox NOT ticked", checked(fp, "#terms") is False)
        check("form was NOT submitted", fp.evaluate("!window.__submitted"))
        check("filled fields are highlighted", fp.eval_on_selector("#fn", "e => getComputedStyle(e).outlineStyle") == "solid")
        banner = fp.evaluate("(document.getElementById('ukct-autofill-banner')||{}).shadowRoot ? document.getElementById('ukct-autofill-banner').shadowRoot.textContent : ''")
        check("banner shown with reminder", "Check marketing boxes, read terms, then submit yourself" in banner and "ban third-party" in banner)

        # ---------- 3. form B (placeholders, radios, address textarea, single DOB box, pre-ticked box, existing value)
        fp.goto("http://localhost:%d/sample-form-b.html" % PORT)   # same host => still armed (10-minute window)
        fp.wait_for_function("document.querySelectorAll('[data-ukct-filled]').length >= 4", timeout=8000)
        check("B: name placeholder -> 'Test User'", val(fp, "[name=x1]") == "Test User")
        check("B: email / phone", val(fp, "[name=x2]") == DUMMY["email"] and val(fp, "[name=x3]") == DUMMY["phone"])
        check("B: address textarea gets full block", val(fp, "[name=x4]") == "1 Test Street\nTestville\nTesttown\nTestshire\nTE1 1ST", val(fp, "[name=x4]"))
        check("B: single DOB box = 03/02/1990", val(fp, "[name=x5]") == "03/02/1990", val(fp, "[name=x5]"))
        check("B: company / best-friend fields untouched", val(fp, "[name=x6]") == "" and val(fp, "[name=x7]") == "")
        check("B: existing value not overwritten", val(fp, "[name=x8]") == "Already typed")
        check("B: title radio 'Mrs' selected", fp.eval_on_selector("input[value=Mrs]", "e => e.checked") is True)
        check("B: pre-ticked marketing box left exactly as the site had it (ticked)", checked(fp, "[name=optin]") is True)
        check("B: not submitted", fp.evaluate("!window.__submitted"))
        fp.close()

        # ---------- 4. an unrelated site (different host, not opened via tracker): totally dormant
        un = ctx.new_page(); un.goto("http://127.0.0.2:%d/sample-form.html" % PORT); un.wait_for_selector("#fn"); un.wait_for_timeout(2500)
        check("unrelated site: nothing filled", val(un, "#fn") == "" and val(un, "#em") == "")
        check("unrelated site: no banner, no highlight", un.evaluate("!document.getElementById('ukct-autofill-banner') && !document.querySelector('[data-ukct-filled]')"))
        # a hostile page cannot fake the hotkey
        un.evaluate("window.dispatchEvent(new KeyboardEvent('keydown',{altKey:true,shiftKey:true,code:'KeyF',bubbles:true}))"); un.wait_for_timeout(500)
        check("synthetic (script-generated) hotkey is ignored", val(un, "#fn") == "")
        # a hostile page cannot hand the userscript details or arm it either
        un.evaluate("window.postMessage({ukct:'v1',from:'page',type:'enter',url:location.href}, '*')"); un.wait_for_timeout(300)
        un.reload(); un.wait_for_selector("#fn"); un.wait_for_timeout(2500)
        check("a page cannot arm itself via postMessage", val(un, "#fn") == "")
        # the real hotkey, pressed by the user
        un.click("body"); un.keyboard.press("Alt+Shift+F"); un.wait_for_function("document.querySelector('#fn').value !== ''", timeout=5000)
        check("real Alt+Shift+F fills on demand", val(un, "#fn") == "Test" and val(un, "#pc") == "TE1 1ST")
        check("hotkey fill still leaves checkboxes alone", checked(un, "#news") is False and checked(un, "#terms") is False and un.evaluate("!window.__submitted"))
        un.close()

        # ---------- 5. Clear removes everything, everywhere
        page.bring_to_front(); page.click("#mdBtn")
        page.once("dialog", lambda d: d.accept())
        page.click("#mdClear"); page.wait_for_timeout(500)
        check("Clear empties localStorage", page.evaluate("localStorage.getItem('ukct.details.v1')") is None)
        check("Clear empties the userscript store", GM.get("ukct_details_v1", "") == "")
        check("Clear empties the form", page.eval_on_selector_all("#mdRows input, #mdRows select", "els => els.every(e => e.value === '')"))
        page.keyboard.press("Escape")
        n2 = ctx.new_page(); n2.goto("http://127.0.0.2:%d/sample-form.html" % PORT); n2.wait_for_selector("#fn"); n2.click("body"); n2.keyboard.press("Alt+Shift+F"); n2.wait_for_timeout(800)
        check("after Clear nothing is filled (banner says no details)", val(n2, "#fn") == "" and "No details saved" in n2.evaluate("document.getElementById('ukct-autofill-banner').shadowRoot.textContent"))
        check("no request carried the dummy details anywhere", not leaked, leaked)
        br.close()
    bad = [n for n, ok in checks if not ok]
    print(f"\n{len(checks) - len(bad)}/{len(checks)} checks passed")
    shutil.rmtree(SITE, ignore_errors=True)
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
