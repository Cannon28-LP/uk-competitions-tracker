# Autofill helper (userscript)

Fills **your own** saved details into competition entry forms you open from the tracker – only when you ask it to. It never submits a form, never ticks a box and never touches captchas.

## Install (2 minutes)
1. Install a userscript manager: **Tampermonkey** or **Violentmonkey** (Chrome, Edge, Firefox, Safari, Brave…).
2. Open the script and press *Install*:
   - raw GitHub: <https://raw.githubusercontent.com/Cannon28-LP/uk-competitions-tracker/main/autofill/uk-comp-autofill.user.js>
   - or from the site: <https://cannon28-lp.github.io/uk-competitions-tracker/autofill/uk-comp-autofill.user.js>
   - (or the “Install userscript” button inside the tracker's **👤 My details** panel)
3. Open the tracker, click **👤 My details**, type your details. The panel should say “✔ Userscript detected”.
   (Chrome-based browsers: if Tampermonkey doesn't run, enable *Developer mode* / “Allow user scripts” for it in `chrome://extensions`.)

## Use
- **Quick enter:** click **Enter on site** on a card (leave “Quick enter” ticked in the panel). The competition opens in a new tab and the form is filled automatically; fields are outlined in green and a banner reminds you to check the marketing boxes, read the terms and submit yourself.
- **On demand:** on any competition page press **Alt+Shift+F** (click inside the form first if it's in an embedded frame), or use the userscript manager's menu item *Fill this page*.
- Forget everything: **Clear all** in the panel (wipes the browser copy *and* the userscript copy), or the manager menu item *Forget my saved details*.

## How your details are kept private
- Saved **only in this browser** (the tracker page's `localStorage`, and the userscript manager's own storage). The tracker has no server that receives them and nothing is stored in the repo – the panel is empty until you type.
- They travel from the tracker page to the userscript with `window.postMessage` inside the same tab – never in a URL, never over the network, never logged. The script makes **no network requests** and asks for no network permission.
- The “quick enter” notice carries no personal data: only the destination website name, valid for 10 minutes, so the script knows the page was opened via the tracker. Following one or two outbound links from that page (e.g. aggregator → promoter) keeps it armed.
- On every other site the script is dormant: it only reacts to a real key press (Alt+Shift+F – web pages can't fake it) or the manager menu.
- No auto-update URL is set on purpose; re-install to update. Read the (single, commented) file before you install – that is what a script handling personal data should allow.

## What it does and doesn't touch
| Fills (only if empty) | Never touches |
|---|---|
| title (dropdown or Mr/Mrs radios), first name, surname, full name, email (+ confirm), phone, address lines, town, county, postcode, date of birth (date box, single text box, or day/month/year dropdowns) | checkboxes (marketing, newsletter, consent, terms – ticked *or* unticked), buttons / submit, captchas, honeypots, passwords, card/payment, promo codes, tie-breaker answers, company / friend / recipient fields, anything you already typed |

Fields are recognised by `autocomplete`, `type`, `name`/`id`, placeholder and label text.

## Limitations
- Forms inside cross-origin iframes (Gleam, Typeform, Woobox…) and sites that render fields in closed shadow DOM or custom widgets may not be filled automatically – click in the form and press Alt+Shift+F, or use the **Copy** buttons in the panel.
- Many tracker links go to an aggregator's listing page, not the entry form itself; the script follows up to two outbound clicks, but you may still need the hotkey on the final page.
- Multi-step forms: later steps are filled if they appear within ~25 s of loading or after a page load while still armed (10 min).
- Some promoters' terms **ban third-party or automated entry tools** (and entering for you may breach them). Check the terms of each competition; you're responsible for what you submit. Fill, then check, tick/untick marketing boxes yourself, and press submit yourself.

## Test
`pip install playwright` then `python tests/autofill/run_autofill_test.py` – runs the real script against dummy forms (“Test User”) in headless Chrome: fills, never ticks, never submits, dormant elsewhere, Clear works, nothing sent over the network.
