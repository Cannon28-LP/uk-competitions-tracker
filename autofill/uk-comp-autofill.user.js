// ==UserScript==
// @name         UK Competitions Tracker – autofill helper
// @namespace    https://github.com/Cannon28-LP/uk-competitions-tracker
// @version      1.0.0
// @description  Fills YOUR OWN saved details into competition entry forms you open from the tracker (or when you press Alt+Shift+F). Never submits, never ticks boxes, never touches captchas. Details stay in your browser.
// @author       Cannon28-LP
// @homepageURL  https://github.com/Cannon28-LP/uk-competitions-tracker/tree/main/autofill
// @license      MIT
// @match        *://*/*
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_deleteValue
// @grant        GM_registerMenuCommand
// @run-at       document-idle
// ==/UserScript==

/*
 * PRIVACY / SAFETY DESIGN (read this before installing)
 *  - Your details travel: tracker page --(window.postMessage, same tab, same origin)--> this script --> GM storage (this browser only).
 *    They are never sent over the network, never put in a URL, never logged. This script makes no network requests at all
 *    (it requests no @connect / GM_xmlhttpRequest permission).
 *  - On every other site the script does NOTHING until either
 *      (a) you opened that site through a card's "Enter" link on the tracker within the last 10 minutes ("quick enter"), or
 *      (b) you press Alt+Shift+F (a real key press) or use the userscript-manager menu item "Fill this page".
 *  - It only types into empty text-like fields (name, email, phone, address, postcode, date of birth) and selects a title.
 *    It never ticks/unticks a checkbox (marketing, newsletter, consent, terms), never clicks a button or submits, never
 *    touches captcha / password / card / promo-code / honeypot fields, and never overwrites something you already typed.
 *  - No auto-update URL is set on purpose: a script that handles personal data should only change when you reinstall it.
 */
(function () {
  "use strict";

  // The tracker this script talks to. (Only this exact origin + path can hand it details or "enter" notices.)
  var TRACKER_ORIGIN = "https://cannon28-lp.github.io";
  var TRACKER_PATH = "/uk-competitions-tracker/";
  var VERSION = "1.0.0";

  var K_DETAILS = "ukct_details_v1";
  var K_PENDING = "ukct_pending_v1";
  var PENDING_TTL = 10 * 60 * 1000;   // a quick-enter notice is valid for 10 minutes
  var MAX_HOPS = 2;                   // follow at most 2 outbound clicks from the page you opened (aggregator -> promoter)
  var WATCH_MS = 25000;               // keep looking for late-rendered form fields for this long on a quick-enter page
  var FIELDS = ["title", "first", "last", "email", "phone", "addr1", "addr2", "town", "county", "postcode", "dob"];

  var isTop = false;
  try { isTop = window.top === window; } catch (e) { isTop = false; }

  /* ------------------------------------------------------------------ storage helpers (GM storage = this browser only) */
  function gmGet(k) { try { return GM_getValue(k, ""); } catch (e) { return ""; } }
  function gmSet(k, v) { try { GM_setValue(k, v); } catch (e) { /* ignore */ } }
  function gmDel(k) { try { GM_deleteValue(k); } catch (e) { /* ignore */ } }

  function sanitize(d) {
    var out = {};
    if (!d || typeof d !== "object") return out;
    FIELDS.forEach(function (k) {
      var v = d[k];
      if (typeof v === "string") { v = v.replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, 200); if (v) out[k] = v; }
    });
    if (out.dob && !/^\d{4}-\d{2}-\d{2}$/.test(out.dob)) delete out.dob;
    return out;
  }
  function loadDetails() { try { return sanitize(JSON.parse(gmGet(K_DETAILS) || "{}")); } catch (e) { return {}; } }

  function hostKey(u) {
    try {
      var x = new URL(u, location.href);
      if (x.protocol !== "http:" && x.protocol !== "https:") return "";
      return x.hostname.toLowerCase().replace(/^www\./, "");
    } catch (e) { return ""; }
  }
  function loadPending() {
    var p = {};
    try { p = JSON.parse(gmGet(K_PENDING) || "{}") || {}; } catch (e) { p = {}; }
    var now = Date.now(), out = {};
    Object.keys(p).forEach(function (h) { if (p[h] && p[h].exp > now) out[h] = p[h]; });
    return out;
  }
  function addPending(url, hops, exp) {
    var h = hostKey(url);
    if (!h) return false;
    var p = loadPending();
    var e = exp || Date.now() + PENDING_TTL;
    if (p[h] && p[h].exp >= e && p[h].hops <= hops) return true;
    p[h] = { exp: e, hops: hops };
    gmSet(K_PENDING, JSON.stringify(p));
    return true;
  }
  function pendingFor(host) {
    var p = loadPending(), best = null;
    Object.keys(p).forEach(function (h) {
      if (host === h || host.slice(-(h.length + 1)) === "." + h || h.slice(-(host.length + 1)) === "." + host) {
        if (!best || p[h].hops < best.hops) best = p[h];
      }
    });
    return best;
  }

  /* ================================================================== A. bridge: runs only on the tracker page itself */
  if (location.origin === TRACKER_ORIGIN && location.pathname.indexOf(TRACKER_PATH) === 0) {
    if (!isTop) return;
    document.documentElement.setAttribute("data-ukct-autofill", VERSION);
    var reply = function (type, extra) {
      var m = { ukct: "v1", from: "script", type: type, version: VERSION };
      if (extra) for (var k in extra) m[k] = extra[k];
      window.postMessage(m, TRACKER_ORIGIN);
    };
    window.addEventListener("message", function (e) {
      if (e.source !== window || e.origin !== TRACKER_ORIGIN) return;
      var d = e.data;
      if (!d || d.ukct !== "v1" || d.from !== "page") return;
      if (d.type === "ping") { reply("hello"); return; }
      if (d.type === "details") {
        var s = sanitize(d.details);
        if (Object.keys(s).length) gmSet(K_DETAILS, JSON.stringify(s)); else gmDel(K_DETAILS);
        reply("ack", { for: "details", count: Object.keys(s).length });
        return;
      }
      if (d.type === "enter") {
        var ok = typeof d.url === "string" && addPending(d.url, 0, 0);
        reply("ack", { for: "enter", ok: !!ok, host: ok ? hostKey(d.url) : "" });
        return;
      }
      if (d.type === "clear") { gmDel(K_DETAILS); gmDel(K_PENDING); reply("ack", { for: "clear", count: 0 }); }
    });
    reply("hello");
    return;
  }

  /* ================================================================== B. everywhere else: dormant unless armed or asked */
  var BANNER_ID = "ukct-autofill-banner";
  var filledSet = typeof WeakSet === "function" ? new WeakSet() : { _a: [], add: function (x) { this._a.push(x); }, has: function (x) { return this._a.indexOf(x) >= 0; } };
  var totalFilled = 0;
  var bannerHost = null;

  /* ---------- text helpers */
  function norm(s) {
    return String(s || "").replace(/([a-z])([A-Z])/g, "$1 $2").replace(/[_\-.\[\]\/:()*]+/g, " ").replace(/\s+/g, " ").trim().toLowerCase();
  }
  function textOf(n) { return n ? (n.textContent || "") : ""; }

  function labelTexts(el) {
    var out = [];
    try { if (el.labels) for (var i = 0; i < el.labels.length; i++) out.push(textOf(el.labels[i])); } catch (e) { /* ignore */ }
    var lb = el.getAttribute("aria-labelledby");
    if (lb) lb.split(/\s+/).forEach(function (id) { var n = el.getRootNode().getElementById ? el.getRootNode().getElementById(id) : null; if (n) out.push(textOf(n)); });
    var w = el.closest && el.closest("label");
    if (w) out.push(textOf(w));
    if (!out.length) {   // fall back to short text right before the field
      var p = el.previousElementSibling;
      if (p && !/^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(p.tagName) && textOf(p).length <= 60) out.push(textOf(p));
      else if (el.parentElement) {
        var pp = el.parentElement.previousElementSibling;
        if (pp && !pp.querySelector("input,select,textarea") && textOf(pp).length <= 60) out.push(textOf(pp));
      }
    }
    return out.map(function (t) { return norm(t.slice(0, 120)); }).filter(Boolean);
  }
  function signalsOf(el) {
    var s = [norm(el.getAttribute("name")), norm(el.id), norm(el.getAttribute("placeholder")), norm(el.getAttribute("aria-label")), norm(el.getAttribute("title"))];
    labelTexts(el).forEach(function (t) { s.push(t); });
    return s.filter(Boolean);
  }
  function groupText(el) {   // text of the nearest few ancestors, to recognise a "Date of birth" group
    var t = "", n = el, i = 0;
    while (n && i < 4) {
      n = n.parentElement; i++;
      if (!n) break;
      var lg = n.querySelector && n.querySelector(":scope > legend, :scope > label, :scope > .label, :scope > h3, :scope > h4, :scope > span");
      if (lg) t += " " + textOf(lg).slice(0, 80);
      if (n.tagName === "FIELDSET") break;
    }
    return norm(t);
  }

  /* ---------- which fields may we touch? */
  var SKIP_TYPES = /^(hidden|password|checkbox|radio|file|submit|button|image|reset|color|range|search|number|url|month|week|time|datetime-local)$/;
  var NEG = /(captcha|recaptcha|hcaptcha|honey|\bhp\b|bot trap|spam|coupon|promo|voucher|password|passcode|username|user name|login|log in|referr|friend|recipient|sender|company|organi[sz]ation|business|\bvat\b|\bcard\b|credit card|cvv|cvc|iban|sort code|account number|search|comment|message|answer|tie ?break|slogan|in (?:25|50|\d+) words|reason|why |describe|description|how did you hear|\botp\b|verification code|security code|confirmation code|sms code|2fa|\bpin\b|favourite|favorite|\bpets?\b|\bchild|spouse|partner|\bgift\b|team name|nickname|display name|instagram|twitter|facebook|tiktok|handle|social)/;

  function visible(el) {
    if (!el.getClientRects().length) return false;
    var cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none" || parseFloat(cs.opacity) === 0) return false;
    var r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return false;
    if (r.right < 0 || r.bottom < -50 || r.left > innerWidth + 50) return false;   // parked off-screen (honeypots)
    if (el.getAttribute("aria-hidden") === "true" || el.tabIndex === -1 && cs.position === "absolute") return false;
    return true;
  }
  function fillable(el) {
    var tag = el.tagName;
    if (tag === "INPUT") { var t = (el.getAttribute("type") || "text").toLowerCase(); if (SKIP_TYPES.test(t)) return false; }
    if (el.disabled || el.readOnly) return false;
    if (!visible(el)) return false;
    var sig = [el.getAttribute("name"), el.id, el.className && typeof el.className === "string" ? el.className : ""].join(" ");
    if (/honey|honeypot|trap|nospam|bot[-_ ]?field|captcha/i.test(sig)) return false;
    return true;
  }
  function collect(root, out) {
    var els = root.querySelectorAll("input,select,textarea,*");
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (el.shadowRoot) collect(el.shadowRoot, out);   // open shadow roots only
      if (/^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName)) out.push(el);
    }
    return out;
  }

  /* ---------- classify one field -> key in FIELDS (or a split-DOB key) */
  var AC = { "given-name": "first", "family-name": "last", "name": "full", "email": "email", "tel": "phone", "tel-national": "phone",
    "street-address": "street", "address-line1": "addr1", "address-line2": "addr2", "address-level2": "town", "address-level1": "county",
    "postal-code": "postcode", "bday": "dob", "bday-day": "dobd", "bday-month": "dobm", "bday-year": "doby", "honorific-prefix": "title" };

  function classify(el) {
    var tag = el.tagName, type = tag === "INPUT" ? (el.getAttribute("type") || "text").toLowerCase() : tag.toLowerCase();
    var sig = signalsOf(el), all = sig.join(" | ");
    var acs = (el.getAttribute("autocomplete") || "").toLowerCase().split(/\s+/);
    var ac = ""; for (var i = acs.length - 1; i >= 0; i--) if (AC[acs[i]]) { ac = AC[acs[i]]; break; }
    if (NEG.test(all) && !ac) return "";
    if (ac) return ac;
    var any = function (re) { return sig.some(function (s) { return re.test(s); }); };
    var grp = (/birth|dob/.test(groupText(el))) ? "birth" : "";
    // split date of birth (three selects / inputs)
    if (any(/(birth|dob|born)/) || grp) {
      if (type === "date") return "dob";
      if (any(/\b(dd|mm)\b.*\b(mm|yyyy|yy)\b|\b(yyyy|yy)\b.*\b(mm|dd)\b/)) return "dob";   // one box showing a full date format
      if (any(/\b(day|dd|d)\b/) && !any(/\b(month|year)\b/)) return "dobd";
      if (any(/\b(month|mm|mon)\b/)) return "dobm";
      if (any(/\b(year|yyyy|yy)\b/)) return "doby";
      return any(/(birth|dob|born)/) ? "dob" : "";
    }
    if (type === "email" || any(/e ?mail/)) return "email";
    if (type === "tel" || any(/\b(phone|mobile|telephone|tel|contact number|cell)\b/)) return "phone";
    if (any(/(post ?code|postal code|zip|\bpcode\b)/)) return "postcode";
    if (any(/(first ?name|fore ?name|given name|\bfname\b|christian name)/)) return "first";
    if (any(/(last ?name|sur ?name|family name|\blname\b|second name)/)) return "last";
    if (tag === "SELECT" && any(/\b(title|salutation|honorific|prefix)\b/) && !any(/(job|position|role)/)) return "title";
    if (any(/(address ?(line)? ?(2|two)\b|address ?2|addr ?2|line 2|\b(apartment|flat|suite|unit)\b)/)) return "addr2";
    if (any(/(address ?(line)? ?(1|one)\b|address ?1|addr ?1|line 1|street|house (number|name)|building)/)) return "addr1";
    if (any(/\b(town|city|locality|post town)\b/)) return "town";
    if (any(/\b(county|state|province|region)\b/)) return "county";
    if (any(/\baddress\b/) && !any(/(e ?mail|ip |web)/)) return tag === "TEXTAREA" ? "addrblock" : "addr1";
    if (any(/^(your |full |contact |entrant |customer |first and last )?name$/) || any(/\b(full name|your name)\b/)) return "full";
    return "";
  }

  /* ---------- value setting (works with React/Vue style listeners) */
  function setNative(el, v) {
    var proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : el.tagName === "SELECT" ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    var d = Object.getOwnPropertyDescriptor(proto, "value");
    if (d && d.set) d.set.call(el, v); else el.value = v;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }
  var MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"];
  function selectOption(sel, wanted) {   // wanted: array of acceptable strings (lowercase)
    var cur = sel.options[sel.selectedIndex];
    if (cur && cur.value !== "" && !/(select|choose|please|^-+$|—|pick)/i.test(cur.text) && sel.selectedIndex > 0) return false;   // user/page already chose something
    for (var i = 0; i < sel.options.length; i++) {
      var o = sel.options[i], tv = o.value.trim().toLowerCase(), tt = o.text.trim().toLowerCase().replace(/\.$/, "");
      if (wanted.indexOf(tv) >= 0 || wanted.indexOf(tt) >= 0) { sel.selectedIndex = i; sel.dispatchEvent(new Event("input", { bubbles: true })); sel.dispatchEvent(new Event("change", { bubbles: true })); return true; }
    }
    return false;
  }
  function mark(el) {
    filledSet.add(el);
    el.setAttribute("data-ukct-filled", "1");
    el.style.setProperty("outline", "2px solid #2f9e44", "important");
    el.style.setProperty("outline-offset", "1px", "important");
    var clear = function (ev) { if (ev.isTrusted) { el.style.removeProperty("outline"); el.style.removeProperty("outline-offset"); el.removeEventListener("input", clear); } };
    el.addEventListener("input", clear);
  }
  function fitLen(el, v) {
    var m = el.maxLength;
    if (m > 0 && v.length > m) { v = v.replace(/\s+/g, ""); if (v.length > m) return ""; }
    return v;
  }
  function dobParts(iso) { var p = iso.split("-"); return { y: p[0], m: p[1], d: p[2] }; }
  function dobText(el, iso) {
    var q = dobParts(iso), ph = (el.getAttribute("placeholder") || "").toLowerCase();
    var sep = /[-.]/.test(ph.replace(/[a-z]/g, "")) ? ph.replace(/[a-z]/g, "").charAt(0) : "/";
    if (/^m+[\/.-]d+/.test(ph)) return q.m + sep + q.d + sep + q.y;
    if (/^y+[\/.-]/.test(ph)) return q.y + sep + q.m + sep + q.d;
    if (/yy$/.test(ph) && !/yyyy$/.test(ph)) return q.d + sep + q.m + sep + q.y.slice(2);
    return q.d + sep + q.m + sep + q.y;
  }

  function fillOne(el, kind, D) {
    if (filledSet.has(el)) return false;
    var tag = el.tagName, type = tag === "INPUT" ? (el.getAttribute("type") || "text").toLowerCase() : "";
    var isSel = tag === "SELECT";
    if (!isSel && String(el.value || "").trim() !== "") return false;      // never overwrite what's there
    var v = "";
    switch (kind) {
      case "title": if (!D.title) return false;
        if (isSel) { var t = D.title.toLowerCase().replace(/\.$/, ""); if (!selectOption(el, [t, t + "."])) return false; mark(el); return true; }
        v = D.title; break;
      case "first": v = D.first; break;
      case "last": v = D.last; break;
      case "full": v = [D.first, D.last].filter(Boolean).join(" "); break;
      case "email": v = D.email; break;
      case "phone": v = D.phone; break;
      case "postcode": v = D.postcode ? D.postcode.toUpperCase() : ""; break;
      case "addr1": v = D.addr1; break;
      case "addr2": v = D.addr2; break;
      case "town": v = D.town; break;
      case "county":
        if (isSel) { if (!D.county) return false; if (!selectOption(el, [D.county.toLowerCase()])) return false; mark(el); return true; }
        v = D.county; break;
      case "street": v = [D.addr1, D.addr2].filter(Boolean).join(", "); break;
      case "addrblock": v = [D.addr1, D.addr2, D.town, D.county, D.postcode && D.postcode.toUpperCase()].filter(Boolean).join("\n"); break;
      case "dob": if (!D.dob) return false;
        if (type === "date") v = D.dob; else if (isSel) return false; else v = dobText(el, D.dob);
        break;
      case "dobd": case "dobm": case "doby": {
        if (!D.dob) return false;
        var q = dobParts(D.dob), wanted;
        if (kind === "dobd") wanted = [String(+q.d), q.d];
        else if (kind === "dobm") { var mn = MONTHS[+q.m - 1]; wanted = [String(+q.m), q.m, mn, mn.slice(0, 3)]; }
        else wanted = [q.y, q.y.slice(2)];
        if (isSel) { if (!selectOption(el, wanted)) return false; mark(el); return true; }
        v = wanted[kind === "dobm" ? 1 : 0]; if (kind === "doby" && el.maxLength === 2) v = q.y.slice(2);
        break;
      }
      default: return false;
    }
    if (!v) return false;
    v = fitLen(el, v);
    if (!v) return false;
    setNative(el, v);
    mark(el);
    return true;
  }

  /* title given as radio buttons (Mr / Mrs / Miss…): the one place we select a radio, and only for the title group */
  function fillTitleRadios(D) {
    if (!D.title) return 0;
    var want = D.title.toLowerCase().replace(/\.$/, ""), n = 0, groups = {};
    var rs = document.querySelectorAll("input[type=radio]");
    for (var i = 0; i < rs.length; i++) {
      var r = rs[i];
      if (r.disabled || !r.name || !visible(r)) continue;
      var nm = norm(r.name + " " + (r.getAttribute("autocomplete") || ""));
      if (!/\b(title|salutation|honorific|prefix)\b/.test(nm) || /(job|position|role)/.test(nm)) continue;
      (groups[r.name] = groups[r.name] || []).push(r);
    }
    Object.keys(groups).forEach(function (g) {
      var grp = groups[g];
      if (grp.some(function (r) { return r.checked; })) return;
      for (var j = 0; j < grp.length; j++) {
        var lab = (labelTexts(grp[j])[0] || norm(grp[j].value)).replace(/\./g, "").trim();
        if (lab === want || norm(grp[j].value) === want) { grp[j].click(); mark(grp[j]); n++; break; }
      }
    });
    return n;
  }

  function fillPage() {
    var D = loadDetails();
    if (!Object.keys(D).length) return { n: 0, noDetails: true };
    var n = 0, els = collect(document, []);
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (!fillable(el) || filledSet.has(el)) continue;
      var kind = classify(el);
      if (kind && fillOne(el, kind, D)) n++;
    }
    n += fillTitleRadios(D);
    totalFilled += n;
    return { n: n, noDetails: false };
  }

  /* ---------- banner (shadow DOM so the page's CSS can't touch it; contains no personal data) */
  function showBanner(state) {
    if (!bannerHost) {
      bannerHost = document.createElement("div");
      bannerHost.id = BANNER_ID;
      bannerHost.style.cssText = "all:initial;position:fixed;z-index:2147483647;left:12px;bottom:12px;max-width:min(420px,calc(100vw - 24px))";
      var root = bannerHost.attachShadow({ mode: "open" });
      root.innerHTML = '<style>.b{font:13px/1.45 system-ui,Segoe UI,Roboto,sans-serif;background:#10231a;color:#eaf7ef;border:1px solid #2f9e44;border-radius:12px;padding:10px 12px;box-shadow:0 6px 24px rgba(0,0,0,.35)}' +
        '.h{font-weight:700;margin-bottom:3px}.s{opacity:.85;font-size:12px;margin-top:5px}.r{display:flex;gap:8px;margin-top:8px}' +
        'button{font:inherit;font-size:12.5px;border-radius:8px;border:1px solid #4cc46a;background:#1d4a2c;color:#fff;padding:4px 10px;cursor:pointer}button.g{background:transparent;border-color:#6b7f73}</style>' +
        '<div class="b" role="status"><div class="h"></div><div class="m"></div><div class="s">Some competitions ban third-party or automated entry tools – check the terms before using this.</div>' +
        '<div class="r"><button type="button" id="f">Fill form</button><button type="button" class="g" id="x">Hide</button></div></div>';
      root.getElementById("f").addEventListener("click", function (e) { if (e.isTrusted) run(true); });
      root.getElementById("x").addEventListener("click", function (e) { if (e.isTrusted) { bannerHost.remove(); bannerHost = null; } });
      (document.body || document.documentElement).appendChild(bannerHost);
    }
    var r = bannerHost.shadowRoot;
    r.querySelector(".h").textContent = "UK Competitions Tracker – autofill";
    var msg;
    if (state.noDetails) msg = "No details saved yet. Open the tracker, click “My details”, fill them in, then try again.";
    else if (state.total > 0) msg = "Filled " + state.total + " field" + (state.total === 1 ? "" : "s") + " (outlined in green). Check marketing boxes, read terms, then submit yourself. Nothing has been ticked or submitted.";
    else msg = "No matching empty fields found on this page yet. If the form is in a frame or loads later, click in the form and press Alt+Shift+F. Check marketing boxes and terms, then submit yourself.";
    r.querySelector(".m").textContent = msg;
  }

  /* ---------- running */
  function run(userAction) {
    var res = fillPage();
    if (userAction || totalFilled > 0 || res.noDetails) showBanner({ total: totalFilled, noDetails: res.noDetails });
    return res;
  }

  var watching = false;
  function armed() {   // opened through the tracker: fill now, and again as late fields appear
    if (watching) return; watching = true;
    var res = run(false);
    if (res.noDetails) return;
    if (!totalFilled) showBanner({ total: 0, noDetails: false });
    var t0 = Date.now(), timer = null;
    var mo = new MutationObserver(function () {
      if (Date.now() - t0 > WATCH_MS) { mo.disconnect(); return; }
      clearTimeout(timer);
      timer = setTimeout(function () { var r = fillPage(); if (r.n) showBanner({ total: totalFilled, noDetails: false }); }, 400);
    });
    try { mo.observe(document.documentElement, { childList: true, subtree: true }); } catch (e) { /* ignore */ }
    setTimeout(function () { mo.disconnect(); }, WATCH_MS);
    [1500, 4000].forEach(function (ms) { setTimeout(function () { var r = fillPage(); if (r.n) showBanner({ total: totalFilled, noDetails: false }); }, ms); });
  }

  // hotkey: Alt+Shift+F, real key presses only (a web page can't fake it)
  window.addEventListener("keydown", function (e) {
    if (e.isTrusted && e.altKey && e.shiftKey && !e.ctrlKey && !e.metaKey && e.code === "KeyF") { e.preventDefault(); run(true); }
  }, true);

  if (typeof GM_registerMenuCommand === "function") {
    try {
      GM_registerMenuCommand("Fill this page (UK Competitions autofill)", function () { run(true); });
      if (isTop) GM_registerMenuCommand("Forget my saved details", function () { gmDel(K_DETAILS); gmDel(K_PENDING); });
    } catch (e) { /* ignore */ }
  }

  // quick enter: only the top page, only if the user opened this site through the tracker moments ago
  if (isTop) {
    var host = hostKey(location.href), pend = host ? pendingFor(host) : null;
    if (pend) {
      armed();
      // aggregator -> promoter: a real click on an outbound link from an armed page arms the next site too (max 2 hops)
      if (pend.hops < MAX_HOPS) {
        document.addEventListener("click", function (e) {
          if (!e.isTrusted) return;
          var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
          if (!a) return;
          var h2 = hostKey(a.href);
          if (h2 && h2 !== host) addPending(a.href, pend.hops + 1, pend.exp);
        }, true);
      }
    }
  }
})();
