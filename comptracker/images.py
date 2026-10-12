"""Prize pictures for items whose source gave none: the promoter page's og:image / twitter:image / main image.
Cached per link (`ogimg:<url>`; misses retried after 14 days), new lookups limited by a per-run budget.
Pages that redirect to a login/sign-in page are never used. (Screenshot fallback: comptracker/shots.py, run in CI.)"""
import re, time
from datetime import datetime
from urllib.parse import urljoin
from .util import now
from . import safety, qa

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
    """One cached read of the promoter page per item: og:image (when the source had no picture) and the entry question
    (comptracker.qa; when the source gave none). Cache 'page:<url>' (misses re-read after RETRY_DAYS)."""
    st = dict(had=0, cached=0, found=0, none=0, pending=0, qa=0); t_end = time.time() + budget_s; new = 0
    for it in items:
        need_img = not it.get("image"); need_qa = not it.get("qa")
        if not need_img: st["had"] += 1
        link = it.get("link") or ""
        if not (need_img or need_qa) or not it.get("direct") or not link.startswith("http") or safety.is_aggregator_domain(safety.domain(link)): continue
        key = "page:" + link; c = ctx.cache_get(key)
        if c is None and need_img and not need_qa:
            old = ctx.cache_get("ogimg:" + link)
            if old and old.get("img"): it["image"] = old["img"]; st["cached"] += 1; continue
        if c is None or (not c.get("img") and not c.get("qa") and (now() - datetime.fromisoformat(c["at"])).days >= RETRY_DAYS):
            if time.time() > t_end or new >= max_new: st["pending"] += 1; continue
            new += 1; img = ""; qa_d = None; r = None
            try:
                r = ctx.get(link)
                if r is not None and not LOGIN.search(getattr(r, "url", "") or ""):
                    html = r.text or ""
                    img = og_image(html, getattr(r, "url", link) or link)
                    qa_d = qa.from_page(html)
            except Exception:
                r = None
            if r is None: st["pending"] += 1; continue
            c = dict(img=img, qa=qa_d, at=now().isoformat(timespec="seconds")); ctx.cache_put(key, c)
        if need_img and c.get("img"): it["image"] = c["img"]; st["found"] += 1
        cq = c.get("qa")
        if cq and cq.get("q") and not qa._quizlike(cq["q"]): cq = None          # cached by an older, looser parser
        if need_qa and cq: it["qa"] = cq; st["qa"] += 1
    return st
