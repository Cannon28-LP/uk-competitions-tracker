# 🎟️ UK Prize Competition Tracker

A public, static listing of live UK prize competitions and draws (cash, cars, holidays, tech, radio contests and more), collected from public pages and rebuilt **every hour** by GitHub Actions – no server needed.

**Live site:** https://cannon28-lp.github.io/uk-competitions-tracker/

## Features
- Prize pictures on every card (taken from the source listing; a category placeholder is shown when a source has none or blocks the image).
- **My details + autofill helper** (optional): a panel to keep your name/address/DOB in *your browser only* (copy buttons, copy all, clear), plus a Tampermonkey/Violentmonkey userscript that fills the entry form on the competition page when you ask – never submits, never ticks boxes. See [`autofill/README.md`](autofill/README.md).
- Two-level prize taxonomy: 16 main categories (+ Other), each with specific sub-categories (e.g. Cars → Supercars/Performance, Luxury, Electric/Hybrid…). Picking a main category chip reveals its sub-category chips with live counts. Classification is keyword/rule based and lives in `comptracker/classify.py` (`TAXONOMY`, ordered rules, tests in `tests/`); anything that can't be placed stays in Other.
- Search, Free / Paid switch, prize categories with live counts, quick toggles (new today, ends within 24h, radio, has picture), safety and source filters – all client-side.
- Price filters: a prize-value range (e.g. £1 – £1,000) and an "entry up to £…" limit (0 = free only).
- Sort by newest, ending soonest, biggest prize, cheapest entry or fewest entries so far. The current filters are kept in the address bar, so a view can be bookmarked or shared.
- Live countdowns to closing time (UK time), tickets-sold bars, and a "Details" panel per card with how to enter, the £30/month budget helper and why it got its safety badge.
- Per-listing **safety badge** (Verified / Unverified / Caution) with a one-line reason (e.g. “Unknown promoter – no T&Cs found” vs “Aggregator-listed, promoter unverified”); serious warnings are shown on the card itself.
- Expired and CLOSED competitions disappear automatically; **NEW** means first seen by the tracker in the last 24 hours (nothing older); repeat copies of the same competition – including near-identical titles from different sources – are merged into one card that keeps every source link.
- Listings with no stated prize value say **Value unknown** (and stay in results when a prize range is set – untick “incl. unknown value” to hide them); implausible headline figures (e.g. “Win £1.4M+ Prize Every Time”) are shown as **Unverified**, not as the prize value.
- Source health is shown in the footer table and in a header warning: each source's last successful run, “stale since …” when it is failing, and data from a source that hasn't been confirmed for 24h is dropped.
- Light and dark themes, phone-friendly layout, and cards load 48 at a time as you scroll so the page stays fast.

## How it works
1. `.github/workflows/update.yml` runs hourly (cron `17 * * * *`) and on demand (`workflow_dispatch`).
2. `python -m comptracker.ci` restores the persisted state, runs every source in `comptracker/sources.py` (polite fetching: robots.txt respected, per-host delay, no logins; timeouts and exponential-backoff retries for timeouts/5xx/429/HTTP 202; a host that keeps answering 403 is skipped for the rest of the run), de-duplicates across sources (exact + conservative fuzzy title match), classifies and safety-scores each item, then writes `competitions.json`.
   Each listing remembers when its source last confirmed it: after 3h unconfirmed it is flagged *stale* on the page, after 24h it is dropped.
3. State needed for "New" flags, de-duplication and fetch caching (`state.json`) plus the latest `competitions.json` live on the orphan **`data`** branch, which is force-pushed as one squashed commit each run so the repository doesn't grow without bound.
4. `web/index.html` + `competitions.json` are deployed to GitHub Pages (Pages source: *GitHub Actions*).

Run locally: `pip install -r requirements.txt && python -m comptracker.ci --state /tmp/state.json --out /tmp/site` (first run with an empty state is a slow baseline run; nothing is flagged "New" for it), then serve `web/index.html` next to `/tmp/site/competitions.json` (e.g. copy both into one folder and `python -m http.server`).

Add a source: write a function in `comptracker/sources.py` decorated with `@source(...)`; it is picked up automatically.

Sources: Loquax (+ Win-a-House), ThePrizeFinder, Competition Showroom (+ BOTB and 7days pages), FindCompetitions, Competitions Time, Competitions Today, MSE Competitions Time, Latest Deals, Dream Car Giveaways, Omaze, Nitrous, Compete For Cars, ITV Win, olive magazine, and radio stations from Global and Bauer (Hello Rayo).

**Deliberately not collected:** talkSPORT (its robots.txt disallows automated access to its competitions pages). Sources that block the CI runners (e.g. FindCompetitions returns HTTP 403 from GitHub's IP ranges) are shown as stale/down on the page rather than silently served from old data (see below).

## Countries

Besides the UK, the tracker collects competitions for **Germany, France, the Netherlands, Ireland, Italy, Australia and New Zealand**
(the EU's biggest comping scenes, plus AU/NZ). Each country has its own sources (`comptracker/src_intl.py`), its own data file
(`data/uk.json`, `data/de.json`, …; `competitions.json` is still written for the UK), its own currency, time zone, regulator text,
safety tips, scam-reporting links and address format in *My details*. Titles stay in the original language; category matching uses an
internal glossary (`comptracker/gloss.py`).

**One country per visitor, no switcher.** The page picks the country **on the device** from the browser's time zone
(e.g. `Europe/Berlin` → Germany, any `Australia/*` → Australia); only if the zone is hidden (UTC) does it use the browser language's
region (`de-DE` → Germany). Anything else → UK. There is no IP lookup and nothing is sent anywhere. Limits: a VPN does not change it
(time zone is local), a traveller sees the list for the time zone their device is set to, and countries sharing a zone we don't
cover (e.g. Austria, Belgium) get the UK list.

**Testing other countries** (test-only; the site has no URL parameter or switcher): `python tests/country/run_country_test.py DATA_DIR`
emulates each country's time zone/locale in a headless Chrome and checks the right file loads. Local-language autofill:
`python tests/autofill/run_local_forms_test.py`.

The hourly workflow runs one collector job per country in parallel (matrix); a failed country keeps its previous file and doesn't block the others.

## Direct promoter links

Every card's **Enter** button goes to the promoter's own competition page. For listing sites (ThePrizeFinder, Loquax, MSE,
12gewinn, jeu-concours, competitions.ie …) the collector opens the listing's detail page, takes its *Enter / Visit / Participer /
Teilnehmen / Doe mee* link and follows the listing site's own redirect hop by hop (each hop checked against robots.txt, using
longest-match robots rules; the promoter page itself isn't fetched). Tracking/affiliate parameters (utm_*, fbclid, gclid, awc …)
are removed. Results are cached in the state file; new items are resolved within a per-run budget, so a backlog clears over a few
hourly runs (`comptracker/resolve.py`).

Not resolved, by design: links only behind a robots-disallowed redirect (Competitions Time `/redir/`, Competitions Today `/go.php`,
GewinnHai `/go/`), behind a sign-up wall (competitions.com.au / .co.nz), login-only forum threads, and affiliate/lead-generation
redirect networks. Such items are **hidden by default**; the "show items without a direct link" box shows them with an
"Enter via listing site" button.

## Isle of Wight

UK only: an **🏝️ Isle of Wight** chip filters local competitions – the Isle of Wight County Press competitions page, OnTheWight /
Island Echo / Visit Isle of Wight giveaways, and any UK listing that names an Island place, attraction or ferry operator.
No Facebook, no logins (`comptracker/src_iow.py`).

## ⚠️ Safety & disclaimer
- **18+ only.** Nothing here enters competitions for you.
- Paid prize competitions/draws are generally **not licensed or regulated by the Gambling Commission**. Play responsibly – set a budget; help is available from [BeGambleAware](https://www.begambleaware.org).
- The Verified / Caution / Unverified **badges are an automated heuristic guide, not a guarantee** that a competition is genuine or fair. Always read the promoter's own terms and conditions, and never pay to "claim" a prize.
- Prize values and closing times are as stated by the source (“~” = approximate); confirm on the promoter's page. This project is unaffiliated with any promoter listed.

**Keeping the schedule alive:** GitHub pauses scheduled workflows after 60 days without repository activity. The workflow therefore re-enables itself via the API on every run and, if `main` has had no commit for 30+ days, adds one tiny `.github/keepalive` commit (which does not trigger a run). The runner image is pinned to `ubuntu-24.04` and actions use their Node 24 releases. For debugging, *Run workflow* accepts an optional comma-separated list of exact source names to run only those.
