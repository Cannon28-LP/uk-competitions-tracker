# 🎟️ UK Prize Competition Tracker

A public, static listing of live UK prize competitions and draws (cash, cars, holidays, tech, radio contests and more), collected from public pages and rebuilt **every hour** by GitHub Actions – no server needed.

**Live site:** https://cannon28-lp.github.io/uk-competitions-tracker/

## Features
- Prize pictures on every card (taken from the source listing; a category placeholder is shown when a source has none or blocks the image).
- Search, Free / Paid switch, prize categories with live counts, quick toggles (new today, ends within 24h, radio, has picture), safety and source filters – all client-side.
- Sort by newest, ending soonest, biggest prize, cheapest entry or fewest entries so far. The current filters are kept in the address bar, so a view can be bookmarked or shared.
- Live countdowns to closing time (UK time), tickets-sold bars, and a "Details" panel per card with how to enter, the £30/month budget helper and why it got its safety badge.
- Per-listing **safety badge** (Verified / Unverified / Caution); serious warnings are shown on the card itself.
- Expired competitions disappear automatically; items first seen in the last 24h get a **NEW** flag; repeat copies of the same competition are shown once.
- Light and dark themes, phone-friendly layout, and cards load 48 at a time as you scroll so the page stays fast.

## How it works
1. `.github/workflows/update.yml` runs hourly (cron `17 * * * *`) and on demand (`workflow_dispatch`).
2. `python -m comptracker.ci` restores the persisted state, runs every source in `comptracker/sources.py` (polite fetching: robots.txt respected, per-host delay, no logins), de-duplicates across sources, classifies and safety-scores each item, then writes `competitions.json`.
3. State needed for "New" flags, de-duplication and fetch caching (`state.json`) plus the latest `competitions.json` live on the orphan **`data`** branch, which is force-pushed as one squashed commit each run so the repository doesn't grow without bound.
4. `web/index.html` + `competitions.json` are deployed to GitHub Pages (Pages source: *GitHub Actions*).

Run locally: `pip install -r requirements.txt && python -m comptracker.ci --state /tmp/state.json --out /tmp/site` (first run with an empty state is a slow baseline run; nothing is flagged "New" for it), then serve `web/index.html` next to `/tmp/site/competitions.json` (e.g. copy both into one folder and `python -m http.server`).

Add a source: write a function in `comptracker/sources.py` decorated with `@source(...)`; it is picked up automatically.

## ⚠️ Safety & disclaimer
- **18+ only.** Nothing here enters competitions for you.
- Paid prize competitions/draws are generally **not licensed or regulated by the Gambling Commission**. Play responsibly – set a budget; help is available from [BeGambleAware](https://www.begambleaware.org).
- The Verified / Caution / Unverified **badges are an automated heuristic guide, not a guarantee** that a competition is genuine or fair. Always read the promoter's own terms and conditions, and never pay to "claim" a prize.
- Prize values and closing times are as stated by the source (“~” = approximate); confirm on the promoter's page. This project is unaffiliated with any promoter listed.

Scheduled workflows are paused by GitHub after 60 days without repository activity; the hourly data pushes count as activity.
