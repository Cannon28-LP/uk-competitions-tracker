"""Prize pictures for items whose source gave none: the promoter page's og:image / twitter:image / main image.
Cached per link (`ogimg:<url>`; misses retried after 14 days), new lookups limited by a per-run budget.
Pages that redirect to a login/sign-in page are never used. (Screenshot fallback: comptracker/shots.py, run in CI.)"""
import re, time
from datetime import datetime
from urllib.parse import urljoin
from .util import now
from . import safety

RETRY_DAYS = 14
RUN = {}   # per-run shared time budget across sources
LOGIN = re.compile(r"/(log-?in|sign-?in|signin|account|auth|sso|oauth|register)(/|\?|$)", re.I)
JUNK = re.compile(r"(logo|favicon|icon|sprite|placeholder|default[-_]?share|og-default|1x1|\.svg(\?|$))", re.I)

def og_image(html, base):
    for pat in (r'<meta[^>]+(?:property|name)=["\'](?:og:image(?::secure_url)?|twitter:image(?::src)?)["\'][^>]*content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\'](?:og:image|twitter:image)["\']',
                r'<link[^>]+rel=["\']image_src["\'][^>]*href=["\']([^"\']+)'):
        for u in re.findall(pat, html[:300000], re.I):
            u = urljoin(base, u.strip().replace("&amp;", "&"))
            if u.startswith("https://") and not JUNK.search(u): return u
    return ""

def apply(ctx, items, budget_s=120, max_new=120):
    st = dict(had=0, cached=0, found=0, none=0, pending=0); t_end = time.time() + budget_s; new = 0
    for it in items:
        if it.get("image"): st["had"] += 1; continue
        link = it.get("link") or ""
        if not it.get("direct") or not link.startswith("http") or safety.is_aggregator_domain(safety.domain(link)): continue
        key = "ogimg:" + link; c = ctx.cache_get(key)
        if c and (c.get("img") or (now() - datetime.fromisoformat(c["at"])).days < RETRY_DAYS):
            if c.get("img"): it["image"] = c["img"]; st["cached"] += 1
            continue
        if time.time() > t_end or new >= max_new: st["pending"] += 1; continue
        new += 1; img = ""
        try:
            r = ctx.get(link)
            if r is not None and not LOGIN.search(getattr(r, "url", "") or ""):
                img = og_image(r.text or "", getattr(r, "url", link) or link)
        except Exception:
            r = None
        if r is None: st["pending"] += 1; continue
        ctx.cache_put(key, dict(img=img, at=now().isoformat(timespec="seconds")))
        if img: it["image"] = img; st["found"] += 1
        else: st["none"] += 1
    return st
