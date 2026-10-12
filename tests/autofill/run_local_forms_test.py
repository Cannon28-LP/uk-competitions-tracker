"""Autofill on German / French / Dutch / Italian / Australian style forms (DUMMY DATA ONLY). Same shim as run_autofill_test.py.
Run: python tests/autofill/run_local_forms_test.py"""
import json, sys, threading, socketserver, pathlib
import run_autofill_test as T
from playwright.sync_api import sync_playwright

FORMS = {
 "de": ("""<form><select name="anrede" aria-label="Anrede"><option value="">Bitte wählen</option><option>Herr</option><option>Frau</option></select>
  <label for="a">Vorname</label><input id="a" name="vorname"><label for="b">Name</label><input id="b" name="name">
  <label for="c">E-Mail-Adresse</label><input id="c" name="email"><label for="d">Straße</label><input id="d" name="strasse">
  <label for="e">Hausnummer</label><input id="e" name="hausnr"><label for="f">PLZ</label><input id="f" name="plz">
  <label for="g">Ort</label><input id="g" name="ort"><label for="h">Geburtsdatum (TT.MM.JJJJ)</label><input id="h" name="geburtsdatum">
  <label for="i">Firma</label><input id="i" name="firma"><label><input type="checkbox" id="nl"> Newsletter abonnieren</label></form>""",
  dict(title="Frau", first="Testa", last="Muster", email="t@example.invalid", addr1="Teststraße 12a", postcode="12345", town="Testort", dob="1990-02-03"),
  {"#a": "Testa", "#b": "Muster", "#c": "t@example.invalid", "#d": "Teststraße", "#e": "12a", "#f": "12345", "#g": "Testort", "#h": "03.02.1990", "#i": ""}, "select[name=anrede]", "Frau"),
 "fr": ("""<form><label><input type="radio" name="civilite" value="M"> M.</label><label><input type="radio" name="civilite" value="Mme"> Mme</label>
  <label for="a">Nom</label><input id="a" name="nom"><label for="b">Prénom</label><input id="b" name="prenom">
  <label for="c">Adresse</label><input id="c" name="adresse"><label for="d">Code postal</label><input id="d" name="cp">
  <label for="e">Ville</label><input id="e" name="ville"><label for="f">Téléphone portable</label><input id="f" name="tel">
  <fieldset><legend>Date de naissance</legend><select name="jour" aria-label="Jour"><option></option><option>3</option></select>
  <select name="mois" aria-label="Mois"><option></option><option value="01">janvier</option><option value="02">février</option></select>
  <select name="annee" aria-label="Année"><option></option><option>1990</option></select></fieldset></form>""",
  dict(title="Mme", first="Testine", last="Dupont", addr1="12 rue du Test", postcode="75001", town="Testville", phone="0600000000", dob="1990-02-03"),
  {"#a": "Dupont", "#b": "Testine", "#c": "12 rue du Test", "#d": "75001", "#e": "Testville", "#f": "0600000000"}, None, None),
 "nl": ("""<form><label for="a">Voornaam</label><input id="a"><label for="b">Achternaam</label><input id="b"><label for="c">Straat</label><input id="c">
  <label for="d">Huisnummer</label><input id="d"><label for="e">Postcode</label><input id="e"><label for="f">Woonplaats</label><input id="f">
  <label for="g">Geboortedatum (dd-mm-jjjj)</label><input id="g"></form>""",
  dict(first="Test", last="de Tester", addr1="Teststraat 5", postcode="1234 AB", town="Testdorp", dob="1990-02-03"),
  {"#a": "Test", "#b": "de Tester", "#c": "Teststraat", "#d": "5", "#e": "1234 AB", "#f": "Testdorp", "#g": "03-02-1990"}, None, None),
 "it": ("""<form><label for="a">Nome</label><input id="a"><label for="b">Cognome</label><input id="b"><label for="c">Indirizzo</label><input id="c">
  <label for="d">CAP</label><input id="d"><label for="e">Città</label><input id="e"><label for="f">Provincia</label><input id="f">
  <label for="g">Codice fiscale</label><input id="g"><label for="h">Data di nascita (gg/mm/aaaa)</label><input id="h"></form>""",
  dict(first="Prova", last="Rossi", addr1="Via Test 1", postcode="20100", town="Milano", county="MI", dob="1990-02-03"),
  {"#a": "Prova", "#b": "Rossi", "#c": "Via Test 1", "#d": "20100", "#e": "Milano", "#f": "MI", "#g": "", "#h": "03/02/1990"}, None, None),
 "au": ("""<form><label for="a">First name</label><input id="a"><label for="b">Last name</label><input id="b"><label for="c">Street address</label><input id="c">
  <label for="d">Suburb</label><input id="d"><label for="e">State</label><select id="e"><option value="">Select</option><option>New South Wales</option><option>Victoria</option></select>
  <label for="f">Postcode</label><input id="f"></form>""",
  dict(first="Test", last="User", addr1="1 Test St", town="Testburb", county="VIC", postcode="3000"),
  {"#a": "Test", "#b": "User", "#c": "1 Test St", "#d": "Testburb", "#e": "Victoria", "#f": "3000"}, None, None),
}

def main():
    srv = socketserver.ThreadingTCPServer(("0.0.0.0", 0), T.H); srv.daemon_threads = True
    T.PORT = srv.server_address[1]; threading.Thread(target=srv.serve_forever, daemon=True).start()
    for cc, (html, det, exp, tsel, twant) in FORMS.items():
        (T.SITE / f"form-{cc}.html").write_text(f'<!doctype html><meta charset="utf-8"><body>{html}</body>')
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=T.CHROME, headless=True, args=["--no-sandbox"])
        for cc, (html, det, exp, tsel, twant) in FORMS.items():
            T.GM.clear(); T.GM["ukct_details_v1"] = json.dumps(det)
            ctx = br.new_context(); ctx.add_init_script(T.userscript_for_test()); pg = ctx.new_page()
            pg.goto(f"http://localhost:{T.PORT}/form-{cc}.html"); pg.wait_for_timeout(400)
            pg.click("body"); pg.keyboard.press("Alt+Shift+F"); pg.wait_for_timeout(500)
            for sel, want in exp.items():
                got = pg.eval_on_selector(sel, "e => e.tagName === 'SELECT' ? e.options[e.selectedIndex].text : e.value")
                T.check(f"{cc}: {sel} = {want!r}", got == want, got)
            if tsel: T.check(f"{cc}: title select", pg.eval_on_selector(tsel, "e => e.options[e.selectedIndex].text") == twant)
            if cc == "de": T.check("de: newsletter box NOT ticked", not pg.eval_on_selector("#nl", "e => e.checked"))
            if cc == "fr":
                T.check("fr: civilité radio Mme", pg.eval_on_selector("input[value=Mme]", "e => e.checked"))
                T.check("fr: DOB month = février", pg.eval_on_selector("[name=mois]", "e => e.options[e.selectedIndex].text") == "février")
            ctx.close()
        br.close()
    n = sum(ok for _, ok in T.checks); print(f"\n{n}/{len(T.checks)} checks passed"); sys.exit(0 if n == len(T.checks) else 1)

if __name__ == "__main__": main()
