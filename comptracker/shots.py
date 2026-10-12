"""Screenshot thumbnails for live items that still have no prize picture (run in CI, publish job).

  python -m comptracker.shots <data-branch dir> <site dir> [--budget N] [--minutes M]

* only items with a direct promoter link and no image; robots.txt checked (same rules/UA as the collector)
* never pages that are, or redirect to, a login / sign-in / account page, or that show a password field
* cookie banners: clicks a visible 'Reject all' / 'Decline' / 'Only necessary' button if there is one (never 'Accept'),
  never touches any form, checkbox or submit button
* 1200x800 viewport, top of the page only, resized to 600px wide, WebP under ~60 KB
* cached per link in <data>/shots/<key>.webp (+ index.json); only new items are shot, at most N per run;
  files for items that are no longer live are deleted. Stored on the `data` branch (one squashed commit), never on main.
"""
import sys, os, re, json, time, hashlib, io, argparse
from datetime import datetime, timezone
from .util import Fetcher
from . import safety

LOGIN = re.compile(r"/(log-?in|sign-?in|signin|account|my-account|auth|sso|oauth|register|checkout|basket|cart)(/|\?|#|$)", re.I)
REJECT = ["Reject all", "Reject All", "Reject", "Decline", "Decline all", "Only necessary", "Necessary only", "Use necessary cookies only",
          "Continue without accepting", "Refuse all", "Alle ablehnen", "Ablehnen", "Tout refuser", "Refuser", "Alles weigeren", "Weigeren",
          "Rifiuta tutto", "Rifiuta"]
RETRY_DAYS = 7
CMP = ["iframe[id^=sp_message_iframe]", "[id^=sp_message_container]", "#onetrust-banner-sdk", "#onetrust-consent-sdk .ot-sdk-container",
       ".fc-consent-root", "#qc-cmp2-container", "#didomi-popup", "#usercentrics-root", "#CybotCookiebotDialog", ".cmp-root", "#cmpbox",
       "[aria-modal=true][role=dialog]", "[class*=consent-wall]", "[id*=consent-wall]"]

def key(link): return hashlib.sha1(link.encode()).hexdigest()[:16]

def shrink(png, max_kb=60):
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("RGB")
    im = im.resize((600, int(im.height * 600 / im.width)), Image.LANCZOS)
    for q in (72, 62, 52, 42, 34):
        b = io.BytesIO(); im.save(b, "WEBP", quality=q, method=6)
        if b.tell() <= max_kb * 1024: return b.getvalue()
    return b.getvalue() if b.tell() <= 90 * 1024 else None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("data"); ap.add_argument("site")
    ap.add_argument("--budget", type=int, default=40); ap.add_argument("--minutes", type=float, default=6)
    a = ap.parse_args()
    sd = os.path.join(a.data, "shots"); os.makedirs(sd, exist_ok=True)
    ip = os.path.join(sd, "index.json")
    idx = json.load(open(ip)) if os.path.exists(ip) else {}
    files = {}
    for fn in sorted(os.listdir(os.path.join(a.data, "data")), key=lambda x: (x != "uk.json", x)):   # UK first
        if fn.endswith(".json"): files[fn] = json.load(open(os.path.join(a.data, "data", fn)))
    want = {}      # key -> link, items without a picture
    before = after = total = 0
    for d in files.values():
        for it in d.get("items", []):
            total += 1
            if it.get("image") and not it["image"].startswith("shots/"): before += 1; continue
            it["image"] = ""
            link = it.get("link") or ""
            if it.get("direct") and link.startswith("http") and not LOGIN.search(link) and not safety.is_aggregator_domain(safety.domain(link)):
                want[key(link)] = link
    # drop screenshots of items that are gone
    for k in list(idx):
        if k not in want:
            idx.pop(k, None)
            try: os.remove(os.path.join(sd, k + ".webp"))
            except FileNotFoundError: pass
    for fn in os.listdir(sd):
        if fn.endswith(".webp") and fn[:-5] not in want: os.remove(os.path.join(sd, fn))
    now = datetime.now(timezone.utc)
    todo = [k for k in want if not os.path.exists(os.path.join(sd, k + ".webp")) and
            not (k in idx and (now - datetime.fromisoformat(idx[k]["at"])).days < RETRY_DAYS)]
    print(f"items {total}, with source/og image {before}, need picture {len(want)}, new to shoot {len(todo)} (budget {a.budget})")
    shot = failed = 0
    if todo and a.budget > 0:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("playwright not installed; skipping screenshots"); todo = []
        seen_h = {}; f = Fetcher(); t_end = time.time() + a.minutes * 60
        if todo:
          try:
            with sync_playwright() as p:
                br = p.chromium.launch()
                ctx = br.new_context(viewport={"width": 1200, "height": 800}, user_agent=f.s.headers["User-Agent"], java_script_enabled=True,
                                     locale="en-GB", ignore_https_errors=False)
                ctx.set_default_timeout(15000)
                for k in todo[:a.budget]:
                    if time.time() > t_end: break
                    link = want[k]; why = "ok"; data = None
                    if not f.allowed(link): why = "robots"
                    else:
                        pg = ctx.new_page()
                        try:
                            pg.goto(link, wait_until="domcontentloaded", timeout=20000)
                            pg.wait_for_timeout(2500)
                            if LOGIN.search(pg.url) or pg.locator("input[type=password]").count() > 0: why = "login"
                            else:
                                for fr in [pg.main_frame] + [x for x in pg.frames if x != pg.main_frame]:
                                    done = False
                                    for lbl in REJECT:
                                        try:
                                            b = fr.get_by_role("button", name=lbl, exact=True)
                                            if b.count() and b.first.is_visible():
                                                b.first.click(timeout=2000); pg.wait_for_timeout(1000); done = True; break
                                        except Exception: pass
                                    if done: break
                                if any(pg.locator(c).first.is_visible() for c in CMP if pg.locator(c).count()):
                                    raise RuntimeError("consent wall")      # no reject option: a picture of the banner is useless
                                data = shrink(pg.screenshot(clip={"x": 0, "y": 0, "width": 1200, "height": 800}, type="png"))
                                if not data: why = "too large"
                        except Exception as e:
                            why = str(e)[:40] if isinstance(e, RuntimeError) else type(e).__name__
                        finally:
                            pg.close()
                    h = hashlib.sha1(data).hexdigest() if data else ""
                    if data and h in seen_h:
                        try: os.remove(os.path.join(sd, seen_h[h] + ".webp"))
                        except FileNotFoundError: pass
                        data = None; why = "duplicate page"
                    if data: seen_h[h] = k
                    if data:
                        open(os.path.join(sd, k + ".webp"), "wb").write(data); shot += 1
                    else: failed += 1
                    idx[k] = {"link": link, "at": now.isoformat(timespec="seconds"), "why": why}
                br.close()
          except Exception as e:      # never break publishing over screenshots
            print(f"screenshot step stopped: {type(e).__name__}: {str(e)[:200]}")
    json.dump(idx, open(ip, "w"), indent=0, sort_keys=True)
    # point items at their thumbnails; write both the data-branch copy and the site copy
    os.makedirs(os.path.join(a.site, "shots"), exist_ok=True); os.makedirs(os.path.join(a.site, "data"), exist_ok=True)
    for fn, d in files.items():
        for it in d.get("items", []):
            if not it.get("image") and it.get("link"):
                k = key(it["link"])
                if os.path.exists(os.path.join(sd, k + ".webp")): it["image"] = f"shots/{k}.webp"; after += 1
            elif it.get("image"): after += 1
        s = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
        open(os.path.join(a.data, "data", fn), "w").write(s); open(os.path.join(a.site, "data", fn), "w").write(s)
    for fn in os.listdir(sd):
        if fn.endswith(".webp"):
            with open(os.path.join(sd, fn), "rb") as src, open(os.path.join(a.site, "shots", fn), "wb") as dst: dst.write(src.read())
    print(f"screenshots: {shot} new, {failed} failed/skipped; items with a picture: {before} -> {after} of {total}")

if __name__ == "__main__":
    main()
