"""Per-country settings. The collector runs once per country (python -m comptracker.ci --country de ...);
everything country-specific that the *page* needs (currency, regulator, scam-reporting bodies, address format)
is emitted in that country's data file only, so a visitor's page never contains another country's list."""

COUNTRIES = {
    "uk": dict(name="United Kingdom", flag="🇬🇧", tz="Europe/London", currency="GBP", symbol="£", lang="en", locale="en-GB",
               decimal_comma=False, accept_language="en-GB,en;q=0.8"),
    "de": dict(name="Germany", flag="🇩🇪", tz="Europe/Berlin", currency="EUR", symbol="€", lang="de", locale="de-DE",
               decimal_comma=True, accept_language="de-DE,de;q=0.9,en;q=0.5"),
    "fr": dict(name="France", flag="🇫🇷", tz="Europe/Paris", currency="EUR", symbol="€", lang="fr", locale="fr-FR",
               decimal_comma=True, accept_language="fr-FR,fr;q=0.9,en;q=0.5"),
    "nl": dict(name="Netherlands", flag="🇳🇱", tz="Europe/Amsterdam", currency="EUR", symbol="€", lang="nl", locale="nl-NL",
               decimal_comma=True, accept_language="nl-NL,nl;q=0.9,en;q=0.5"),
    "ie": dict(name="Ireland", flag="🇮🇪", tz="Europe/Dublin", currency="EUR", symbol="€", lang="en", locale="en-IE",
               decimal_comma=False, accept_language="en-IE,en;q=0.9"),
    "it": dict(name="Italy", flag="🇮🇹", tz="Europe/Rome", currency="EUR", symbol="€", lang="it", locale="it-IT",
               decimal_comma=True, accept_language="it-IT,it;q=0.9,en;q=0.5"),
    "au": dict(name="Australia", flag="🇦🇺", tz="Australia/Sydney", currency="AUD", symbol="$", lang="en", locale="en-AU",
               decimal_comma=False, accept_language="en-AU,en;q=0.9"),
    "nz": dict(name="New Zealand", flag="🇳🇿", tz="Pacific/Auckland", currency="NZD", symbol="$", lang="en", locale="en-NZ",
               decimal_comma=False, accept_language="en-NZ,en;q=0.9"),
}
CODES = list(COUNTRIES)

# What the page shows for each country (English UI). Links are official bodies only.
PAGE = {
    "uk": dict(
        regulator="Paid prize draws are usually not regulated by the Gambling Commission (they rely on a free entry route or a skill question), so set a budget.",
        eligibility="UK residents (some promotions exclude Northern Ireland, the Channel Islands or the Isle of Man; check the terms).",
        tips=["Check the promoter is named and has Terms & Conditions, a UK address or company number, and a free postal entry route if tickets are sold.",
              "Real promoters never ask winners to pay a fee, give bank log-ins or buy something to claim a prize.",
              "Be wary of 'you've won' messages for competitions you don't remember entering."],
        report=[["Action Fraud: prize draw scams", "https://www.actionfraud.police.uk/a-z-of-fraud/prize-draw-scams"],
                ["Advertising Standards Authority: report a promotion", "https://www.asa.org.uk/make-a-complaint.html"],
                ["Gambling Commission", "https://www.gamblingcommission.gov.uk/"]],
        paid_note="Paid prize draws are usually not regulated by the Gambling Commission"),
    "de": dict(
        regulator="Free competitions (Gewinnspiele) must not require a stake. Paid lotteries need a German licence – licensed operators are on the GGL whitelist (Gemeinsame Glücksspielbehörde der Länder).",
        eligibility="Usually residents of Germany aged 18+ (some include Austria/Switzerland); check the Teilnahmebedingungen.",
        tips=["A genuine Gewinnspiel names the organiser (Impressum) and has Teilnahmebedingungen.",
              "You never pay a fee, call a premium-rate number (0137/0900) or give bank details to claim a prize. 'Gewinnbenachrichtigung' calls asking for money are scams.",
              "Paid lotteries are only legal with a German licence – check the GGL whitelist."],
        report=[["Verbraucherzentrale (consumer advice centres)", "https://www.verbraucherzentrale.de/"],
                ["Bundesnetzagentur: report phone/SMS spam", "https://www.bundesnetzagentur.de/"],
                ["GGL whitelist (licensed gambling operators)", "https://www.gluecksspiel-behoerde.de/de/fuer-spielende/uebersicht-erlaubter-anbieter-whitelist"]],
        paid_note="Paid lotteries in Germany need a licence (GGL whitelist)"),
    "fr": dict(
        regulator="Jeux-concours and loteries publicitaires must be free to enter (or the cost refundable) under the Code de la consommation. Gambling is regulated by the ANJ (Autorité nationale des jeux).",
        eligibility="Usually residents of metropolitan France aged 18+ (some include Belgium/Switzerland or the DROM); check the règlement.",
        tips=["A genuine jeu-concours names the organiser and has a règlement (rules) you can read.",
              "You never pay 'frais de dossier', call a surcharged number or give card details to claim a prize.",
              "Be careful with 'vous avez gagné' emails and SMS for games you didn't enter."],
        report=[["Signal Conso (DGCCRF)", "https://signal.conso.gouv.fr/"],
                ["Cybermalveillance.gouv.fr", "https://www.cybermalveillance.gouv.fr/"],
                ["33700: report spam SMS/calls", "https://www.33700.fr/"]],
        paid_note="Paid lotteries are restricted in France (ANJ)"),
    "nl": dict(
        regulator="Promotional games of chance (winacties) must follow the Kansspelautoriteit's Gedragscode Promotionele Kansspelen: free entry (at most normal postage/phone cost) and prize limits. Paid lotteries need a Ksa licence.",
        eligibility="Usually residents of the Netherlands aged 18+ (some include Belgium); check the actievoorwaarden.",
        tips=["A genuine winactie names the organiser and has actievoorwaarden (terms).",
              "'Free' lottery tickets (gratis lot) usually turn into a paid subscription – read the small print.",
              "You never pay to claim a prize or give your bank details for 'verification'."],
        report=[["Fraudehelpdesk", "https://www.fraudehelpdesk.nl/"],
                ["Kansspelautoriteit", "https://kansspelautoriteit.nl/"],
                ["ACM ConsuWijzer", "https://www.consuwijzer.nl/"]],
        paid_note="Paid lotteries in the Netherlands need a Kansspelautoriteit licence"),
    "ie": dict(
        regulator="Gambling and lotteries are licensed by the Gambling Regulatory Authority of Ireland (GRAI). Paid 'win a house/car' draws need a licence or must be genuine skill competitions – check before paying.",
        eligibility="Usually residents of the Republic of Ireland aged 18+ (some include Northern Ireland); check the terms.",
        tips=["Check the promoter is named and has terms and conditions with closing date and eligibility.",
              "Real promoters never ask winners to pay a fee or give bank log-ins to claim a prize.",
              "Be careful with paid prize draws: ask whether they are licensed by the GRAI."],
        report=[["CCPC: competitions and prize draws", "https://www.ccpc.ie/consumers/"],
                ["FraudSMART", "https://www.fraudsmart.ie/"],
                ["Gambling Regulatory Authority of Ireland", "https://www.grai.ie/"]],
        paid_note="Paid draws in Ireland need a GRAI licence or must be genuine skill competitions"),
    "it": dict(
        regulator="Concorsi a premio must be notified to the Ministero delle Imprese e del Made in Italy (DPR 430/2001) and have a regolamento. Gambling is regulated by ADM (Agenzia delle Dogane e dei Monopoli).",
        eligibility="Usually residents of Italy (often also San Marino) aged 18+; check the regolamento.",
        tips=["A genuine concorso names the società promotrice and publishes a regolamento.",
              "You never pay to receive a prize or give card details to 'confirm' a win.",
              "Many concorsi need a purchase (concorsi con acquisto) – keep your receipt (scontrino)."],
        report=[["Polizia Postale: report online fraud", "https://www.commissariatodips.it/"],
                ["AGCM (consumer protection)", "https://www.agcm.it/"],
                ["ADM (licensed gaming)", "https://www.adm.gov.it/"]],
        paid_note="Paid gambling in Italy needs an ADM licence"),
    "au": dict(
        regulator="Trade promotions are state-regulated – some states (e.g. SA, ACT) need a permit, shown as a permit number in the terms. Paid prize-home and charity lotteries are licensed by state regulators.",
        eligibility="Usually Australian residents aged 18+; some promotions are limited to one state; check the terms.",
        tips=["Check the promoter and permit numbers (where required) in the terms and conditions.",
              "You never pay a fee or give bank log-ins to claim a prize.",
              "Paid prize-home/charity lotteries should show a state licence or permit number."],
        report=[["Scamwatch (ACCC)", "https://www.scamwatch.gov.au/"],
                ["ReportCyber (ASD)", "https://www.cyber.gov.au/report-and-recover/report"],
                ["ACMA: report scam calls and spam", "https://www.acma.gov.au/"]],
        paid_note="Paid lotteries in Australia need a state licence or permit"),
    "nz": dict(
        regulator="Sales promotions are allowed under the Gambling Act 2003; paid lotteries and raffles are regulated by the Department of Internal Affairs (DIA).",
        eligibility="Usually New Zealand residents aged 18+; check the terms.",
        tips=["Check the promoter is named and the terms show the closing date and how winners are drawn.",
              "You never pay a fee or give bank log-ins to claim a prize.",
              "Paid lotteries and raffles should be run under DIA rules for authorised purposes."],
        report=[["Netsafe: report a scam", "https://netsafe.org.nz/"],
                ["NCSC (formerly CERT NZ)", "https://www.ncsc.govt.nz/"],
                ["Department of Internal Affairs: gambling", "https://www.dia.govt.nz/Gambling"]],
        paid_note="Paid lotteries in New Zealand are regulated by the DIA"),
}

def info(cc):
    c = dict(COUNTRIES[cc]); c.update(PAGE[cc]); c["code"] = cc
    c.pop("accept_language", None)
    return c
