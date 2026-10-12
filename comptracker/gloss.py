"""Keyword glossary used ONLY for classification of non-English listings: local prize words are mapped to the
English keywords the classifier understands ('Gutschein' -> 'voucher', 'Kreuzfahrt' -> 'cruise'), and local
currency amounts are normalised so the cash rules see one format. The result is never shown to visitors
(titles are always shown in their original language)."""
import re
from . import util

def _c(pairs, compound=False):
    out = []
    for pat, en in pairs:
        if compound:   # German compounds: match inside words ('Reisegutschein', 'Elektroauto'), not only whole words
            rx = re.compile(pat, re.I)
        else:
            rx = re.compile(r"(?<![\w])(?:" + pat + r")(?![\w])", re.I)
        out.append((rx, en))
    return out

DE = _c([
    (r"gutschein\w*|wertgutschein|einkaufsgutschein|geschenkkarte|einkaufskarte|shoppinggutschein", " voucher "),
    (r"reisegutschein|urlaubsgutschein|hotelgutschein", " travel holiday voucher "),
    (r"(?<!p)reisen?(?!d)|urlaub\w*|ferien(?!wohnung)\w*|kurzurlaub|städtereise|wochenende|kurztrip", " holiday trip "),
    (r"kreuzfahrt\w*", " cruise "), (r"hotelaufenthalt|übernachtung\w*|hotel", " hotel stay "), (r"ferienwohnung|ferienhaus", " holiday villa "),
    (r"wellness\w*", " spa wellness break "), (r"flug|flüge", " flights "),
    (r"bargeld|geldpreis\w*|geldgewinn\w*|cash|euro bar", " cash "), (r"monatlich|jeden monat|pro monat|im monat", " a month "), (r"lebenslang|ein leben lang|rente", " for life "),
    (r"elektroauto|e-auto|elektrofahrzeug", " electric car "), (r"wohnmobil\w*|camper\w*|wohnwagen", " motorhome "), (r"(?<![a-z])auto(?:s)?(?![a-z])|pkw|neuwagen|fahrzeug", " car "),
    (r"motorrad\w*", " motorbike "), (r"roller(?![a-z]*blade)", " scooter "), (r"e-bike|pedelec|elektrofahrrad", " e-bike "), (r"fahrrad\w*|rad(?![a-z])|fahrräder", " bicycle "),
    (r"boot(?:e)?(?![a-z])|segelboot|motorboot|yacht", " boat "), (r"haus(?![a-z]*halt)|eigenheim|wohnung|penthouse|traumhaus|tiny house", " dream home house "),
    (r"fernseher|tv-gerät|oled|smart-tv", " tv "), (r"kopfhörer|lautsprecher|soundbar|musikbox", " headphones speaker audio "), (r"handy|smartphone|iphone", " smartphone phone "),
    (r"laptop|notebook|tablet|ipad", " laptop tablet "), (r"spielkonsole|konsole|playstation|nintendo|xbox", " games console "), (r"kamera|drohne", " camera drone "),
    (r"saugroboter|staubsauger|waschmaschine|kühlschrank|geschirrspüler|haushaltsgerät\w*", " vacuum appliance "),
    (r"kaffeevollautomat|kaffeemaschine|küchenmaschine|heißluftfritteuse|airfryer|mixer|grill(?![a-z])", " kitchen appliance coffee machine "),
    (r"küche\w*|outdoor-küche", " kitchen "), (r"garten\w*|gartenhaus|rasenmäher|pflanzen", " garden "), (r"möbel\w*|sofa|matratze|bett(?![a-z])|sitzsack|einrichtung", " furniture "),
    (r"werkzeug\w*|akkuschrauber|bohrmaschine|baumarkt", " diy tools "),
    (r"konzertkarten|konzert\w*|festival\w*", " concert festival tickets "), (r"tickets?|eintrittskarten|karten(?![a-z])|freikarten", " tickets "),
    (r"musical|theater|show(?![a-z])", " theatre "), (r"kino\w*|film\w*|dvd|blu-ray", " film dvd "), (r"fußball|bundesliga|stadion", " football "),
    (r"buch(?![a-z])|bücher|hörbuch\w*|roman", " books "), (r"zeitschrift\w*|abo(?![a-z])|magazin", " magazine "),
    (r"schmuck|kette|armband|ohrringe|ring(?![a-z])", " jewellery "), (r"uhr(?:en)?(?![a-z])|armbanduhr|smartwatch", " watch "), (r"parfum|duft\w*", " perfume fragrance "),
    (r"kosmetik\w*|pflegeprodukte|hautpflege|beauty", " skincare beauty "), (r"kleidung|mode(?![a-z])|outfit|schuhe|sneaker|jacke", " clothing fashion shoes "), (r"tasche|handtasche|rucksack", " handbag "),
    (r"wein\w*|bier\w*|sekt|champagner|whisky|gin", " wine beer "), (r"genusspaket|präsentkorb|feinkost", " hamper "), (r"schokolade|süßigkeiten|snacks?|kaffee|eis(?![a-z])", " chocolate snacks coffee "),
    (r"essen|abendessen|restaurant\w*|dinner", " restaurant dinner "), (r"lebensmittel\w*|einkauf(?![a-z])|supermarkt|rewe|edeka|kaufland|aldi|lidl|penny|netto", " supermarket grocery "),
    (r"spielzeug\w*|lego|playmobil|brettspiel\w*|puzzle", " toys "), (r"baby\w*|kinderwagen", " baby "), (r"kinder(?![a-z]*schokolade)\w*|familie\w*", " kids family "),
    (r"hund\w*|katze\w*|haustier\w*|tierfutter", " dog cat pet "), (r"fitness\w*|sport(?![a-z]*wagen)\w*|laufschuhe|yoga", " fitness sport "), (r"camping|zelt|wandern|outdoor", " camping outdoor "),
    (r"sonnenbrille\w*", " sunglasses "), (r"rinderfilet|fleisch\w*|steak\w*|grillpaket|wurst\w*", " meat box food box "), (r"training\w*|hantel\w*|fitnessgerät\w*", " fitness "),
    (r"führung|besichtigung|ausflug|freizeitpark|zoo(?![a-z])|erlebnis\w*", " days out "), (r"nachtlicht|lampe\w*|leuchte\w*|deko\w*|wohnaccessoire\w*", " interiors furniture "),
    (r"meilen", " travel holiday flights "), (r"zuschuss|stromkosten|energiekosten|miete", " bills paid "), (r"street triple|triumph", " triumph street motorbike "),
    (r"paket(?![a-z]*dienst)", " bundle "), (r"set(?![a-z])", " gift set "),
    (r"adventskalender", " advent calendar "), (r"weihnacht\w*|ostern|halloween", " christmas "), (r"sofortgewinn\w*|rubbellos", " instant win "),
], compound=True)
DE_DOM = r"\b(deutschland|ostsee|nordsee|sylt|rügen|usedom|bayern|allgäu|schwarzwald|harz|eifel|berlin|hamburg|münchen|köln|dresden|bodensee|sauerland|mosel|rhein|europa-park|phantasialand|heide-park)\b"

FR = _c([
    (r"bons? d'achat|cartes? cadeaux?|e-cartes? cadeaux?|chèques? cadeaux?|bons? de réduction|bons?(?= de \d)|cartes? kadéos|code promo", " gift card voucher "),
    (r"séjours?|voyages?|vacances|week-ends?|escapades?|nuits? d'hôtel|nuitées?|hôtel|circuit", " holiday trip hotel stay "), (r"croisières?", " cruise "), (r"thalasso\w*|spa|bien-être", " spa wellness break "),
    (r"billets? d'avion|vols?", " flights "), (r"argent|espèces|cash|chèques?(?! cadeau)|virement", " cash "), (r"par mois|chaque mois|mensuel\w*", " a month "), (r"à vie", " for life "),
    (r"voiture électrique|véhicule électrique", " electric car "), (r"camping-cars?|fourgon aménagé|van aménagé", " motorhome "), (r"voitures?|véhicules?|automobile", " car "),
    (r"motos?", " motorbike "), (r"scooters?|trottinettes?", " scooter "), (r"vélos? électriques?|vae", " e-bike "), (r"vélos?", " bicycle "), (r"bateaux?|voilier", " boat "),
    (r"maison|appartement|villa|logement", " dream home house "), (r"téléviseur|télévision|tv|écran", " tv "), (r"casques?|écouteurs|enceintes?|barre de son", " headphones speaker audio "),
    (r"smartphones?|téléphones?|iphone", " smartphone phone "), (r"ordinateurs?|pc portable|tablettes?|ipad", " laptop tablet "), (r"consoles?|jeux? vidéo|playstation|nintendo switch|xbox", " games console "),
    (r"appareils? photo|caméras?|drones?|gopro", " camera drone "), (r"aspirateurs?|robot aspirateur|lave-linge|réfrigérateur|électroménager", " vacuum appliance "),
    (r"robots? culinaires?|machines? à café|cafetières?|friteuses?|airfryer|blender|barbecue|plancha|cuiseur", " kitchen appliance coffee machine "),
    (r"cuisine|ustensiles", " kitchen "), (r"jardin\w*|jardinage|tondeuse|plantes?", " garden "), (r"meubles?|mobilier|canapés?|matelas|literie|déco\w*|plaids?|coussins?", " furniture interiors "),
    (r"outils?|bricolage|perceuse", " diy tools "), (r"places? de concert|concerts?|festivals?", " concert festival tickets "), (r"places?|billets?|entrées?|invitations?|pass", " tickets "),
    (r"spectacles?|théâtre|comédie musicale|cirque|exposition|musée", " theatre "), (r"places? de cinéma|cinéma|films?|dvd|blu-?ray", " film dvd "), (r"football|match|stade|rugby|ligue 1", " football "),
    (r"livres?|romans?|bandes? dessinées?|bd|mangas?", " books "), (r"magazines?|abonnements?", " magazine "),
    (r"bijoux|colliers?|bracelets?|bagues?|boucles d'oreilles", " jewellery "), (r"montres?", " watch "), (r"parfums?|eaux? de toilette", " perfume fragrance "),
    (r"cosmétiques?|soins?|crèmes?|maquillage|beauté|coffrets? beauté", " skincare beauty "), (r"vêtements?|tenues?|mode|chaussures|baskets|sneakers|vestes?", " clothing fashion shoes "),
    (r"sacs?(?: à main)?|valises?", " handbag "), (r"vins?|bouteilles?|champagnes?|bières?|spiritueux|whisky|rhum", " wine beer "), (r"paniers? gourmands?|coffrets? gourmands?|colis", " hamper "),
    (r"chocolats?|bonbons|gâteaux|biscuits|café|thé", " chocolate snacks coffee "), (r"repas|dîners?|restaurants?|gastronomi\w*|chefs?", " restaurant dinner "),
    (r"courses|supermarché|carrefour|leclerc|auchan|intermarché|monoprix|super u|lidl|aldi", " supermarket grocery "),
    (r"jouets?|jeux? de société|lego|playmobil|peluches?|puzzles?", " toys "), (r"bébés?|poussettes?|puériculture", " baby "), (r"enfants?|famille\w*", " kids family "),
    (r"chiens?|chats?|animaux|croquettes", " dog cat pet "), (r"fitness|sport\w*|running|yoga", " fitness sport "), (r"camping|randonnée|tentes?", " camping outdoor "),
    (r"taxe foncière|factures?|loyer|électricité", " bills paid "), (r"lessives?|vaisselle|ménage|nettoyage", " household cleaning "), (r"maillots?|t-shirts?|pulls?", " shirt clothing "),
    (r"albums?|kididoc", " books "), (r"paniers?", " hamper "), (r"ateliers?|cours de|visite|stage", " days out experience "), (r"beurres?|cafés|fromages?|biscuits|épicerie|confitures?", " food snacks "),
    (r"glacière|batterie|lampe", " outdoor camping gear "), (r"routine|shampo+ing|baume|soins? capillaires?|lissage|sèche-cheveux", " haircare skincare "), (r"lots? de|coffrets?", " gift set bundle "),
    (r"calendriers? de l'avent", " advent calendar "), (r"noël|halloween|pâques", " christmas "), (r"instants? gagnants?|grattage", " instant win "),
])
FR_DOM = r"\b(france|paris|provence|bretagne|normandie|alsace|corse|côte d'azur|nice|lyon|marseille|bordeaux|alpes|pyrénées|auvergne|loire|dordogne|disneyland paris|parc astérix|futuroscope|puy du fou)\b"

NL = _c([
    (r"cadeaubonn?e?n?|cadeaukaarte?n?|tegoedbonn?e?n?|shoptegoed|winkeltegoed|vvv[- ]bonn?e?n?|bol\.com bon|waardebonn?e?n?|kortingsbonn?e?n?", " gift card voucher "),
    (r"vakanties?|reizen|reis|weekendje|weekend weg|stedentrip|overnachtingen?|hotelovernachting|hotel|vakantiehuis|vakantiepark|center parcs", " holiday trip hotel stay "), (r"cruise", " cruise "),
    (r"wellness\w*|sauna|spa", " spa wellness break "), (r"vliegtickets?", " flights "), (r"geld(?:prijs|prijzen)?|contant|cash", " cash "), (r"per maand|elke maand|maandelijks", " a month "), (r"levenslang", " for life "),
    (r"elektrische auto|e-auto", " electric car "), (r"camper\w*|caravan", " motorhome "), (r"auto'?s?|leaseauto|wagen", " car "), (r"motor(?!\w)", " motorbike "), (r"scooters?", " scooter "),
    (r"e-bikes?|elektrische fiets", " e-bike "), (r"fietsen|fiets", " bicycle "), (r"boot|sloep|zeilboot", " boat "), (r"huis|woning|appartement|droomhuis", " dream home house "),
    (r"televisie|tv|oled", " tv "), (r"koptelefoons?|oordopjes|speakers?|soundbar", " headphones speaker audio "), (r"telefoons?|smartphones?|iphone", " smartphone phone "),
    (r"laptops?|tablets?|ipad", " laptop tablet "), (r"spelcomputer|consoles?|playstation|nintendo|xbox", " games console "), (r"camera'?s?|drones?", " camera drone "),
    (r"stofzuigers?|robotstofzuiger|wasmachine|koelkast|vaatwasser|witgoed", " vacuum appliance "), (r"koffiemachines?|koffiezetapparaat|airfryer|keukenmachine|blender|barbecue|bbq", " kitchen appliance coffee machine "),
    (r"keukens?", " kitchen "), (r"tuin\w*|planten", " garden "), (r"meubels?|banken?|matras|bed|interieur|woonaccessoires", " furniture interiors "), (r"gereedschap|klussen|boormachine", " diy tools "),
    (r"concertkaarten|concerten?|festivals?", " concert festival tickets "), (r"kaartjes|kaarten|tickets?|vrijkaarten|entreekaarten|toegangskaarten", " tickets "),
    (r"musical|theater|voorstelling|show|museum|pretpark|dierentuin|efteling", " theatre days out "), (r"bioscoopkaartjes|bioscoop|films?|dvd", " film dvd "), (r"voetbal|stadion|eredivisie", " football "),
    (r"boeken|boek|luisterboeken?", " books "), (r"tijdschriften?|abonnement|magazine", " magazine "),
    (r"sieraden|ketting|armband|oorbellen|ring", " jewellery "), (r"horloges?|smartwatch", " watch "), (r"parfums?|geuren", " perfume fragrance "),
    (r"beautypakket\w*|verzorgingsproducten|huidverzorging|make-?up|cosmetica|goodiebags?|beauty", " skincare beauty "), (r"kleding|mode|schoenen|sneakers|jas", " clothing fashion shoes "),
    (r"tassen|tas", " handbag "), (r"wijn|bier|champagne|whisky|gin", " wine beer "), (r"pakket|kerstpakket|foodbox|maaltijdbox", " hamper "),
    (r"chocolade|snoep|koffie|thee|koekjes", " chocolate snacks coffee "), (r"diner|etentje|restaurant", " restaurant dinner "),
    (r"boodschappen|supermarkt|albert heijn|jumbo|lidl|aldi|plus|dirk|ah(?= )", " supermarket grocery "),
    (r"speelgoed|lego|bordspellen?|puzzels?", " toys "), (r"baby\w*|kinderwagen", " baby "), (r"kinderen|kinder\w*|gezin\w*|familie\w*", " kids family "),
    (r"honden?|katten?|huisdieren?|dierenvoer", " dog cat pet "), (r"fitness|sport\w*|hardloop\w*|yoga", " fitness sport "), (r"kamperen|tent|wandel\w*", " camping outdoor "),
    (r"glossy|glossies", " magazine "), (r"vuurkorf|vuurschaal|tuinset", " garden "), (r"reischeque|reisbon", " travel holiday voucher "), (r"alarm\w*|beveiliging\w*", " smart home "),
    (r"ansichtkaarten|kaarten set", " stationery "), (r"brandstof|tankpas", " fuel voucher "), (r"pakket", " bundle "),
    (r"adventskalender", " advent calendar "), (r"kerst\w*|sinterklaas|pasen|halloween", " christmas "), (r"loterij|staatslot|postcode loterij|gratis lot", " lottery draw "),
])
NL_DOM = r"\b(nederland|holland|amsterdam|rotterdam|utrecht|den haag|maastricht|texel|terschelling|ameland|vlieland|veluwe|zeeland|limburg|friesland|drenthe|wadden\w*|efteling|center parcs)\b"

IT = _c([
    (r"buoni? (?:spesa|acquisto|regalo|sconto)|gift ?card|carte? regalo|voucher|codici? sconto", " gift card voucher "),
    (r"viaggi?o?|vacanz[ae]|soggiorni?|weekend|notti? in hotel|pernottament\w+|hotel|crociera\w*", " holiday trip hotel stay "), (r"crocier[ae]", " cruise "), (r"terme|spa|benessere", " spa wellness break "),
    (r"voli", " flights "), (r"denaro|contanti|soldi|premi in denaro|bonifico|cash", " cash "), (r"al mese|ogni mese|mensil\w*", " a month "), (r"a vita|per sempre", " for life "),
    (r"auto elettrica|auto ibrida", " electric car "), (r"camper", " motorhome "), (r"auto(?:mobile)?|vettura", " car "), (r"moto(?:cicletta)?", " motorbike "), (r"scooter|monopattin\w+", " scooter "),
    (r"e-bike|bici elettrica", " e-bike "), (r"bici(?:clett\w)?", " bicycle "), (r"barca|gommone|yacht", " boat "), (r"casa|appartamento|villa", " dream home house "),
    (r"televisor\w*|smart tv|tv", " tv "), (r"cuffie|auricolari|altoparlant\w|cassa bluetooth|soundbar", " headphones speaker audio "), (r"smartphone|telefono|cellulare|iphone", " smartphone phone "),
    (r"computer|portatile|notebook|tablet|ipad", " laptop tablet "), (r"console|playstation|nintendo|xbox|videogioc\w+", " games console "), (r"fotocamer\w|videocamer\w|drone", " camera drone "),
    (r"aspirapolvere|robot aspirapolvere|lavatrice|frigorifero|lavastoviglie|elettrodomestic\w+", " vacuum appliance "), (r"macchin\w+ (?:da|del) caffè|friggitrice\w*|robot da cucina|bimby|frullatore|barbecue", " kitchen appliance coffee machine "),
    (r"cucina|pentol\w+|stoviglie", " kitchen "), (r"giardin\w+|piante", " garden "), (r"mobili|divano|materasso|arredament\w|cuscin\w", " furniture interiors "), (r"attrezzi|utensili|trapano", " diy tools "),
    (r"concert\w|festival", " concert festival tickets "), (r"biglietti|ingressi|tickets?|pass", " tickets "), (r"teatro|spettacol\w|musical|museo|mostra|parco divertimenti|gardaland", " theatre days out "),
    (r"cinema|film|dvd", " film dvd "), (r"calcio|stadio|serie a|partita", " football "), (r"libri|libro|romanzo|fumetti|manga", " books "), (r"rivist\w|abbonament\w", " magazine "),
    (r"gioielli|collana|bracciale|orecchini|anello", " jewellery "), (r"orologi?o?|smartwatch", " watch "), (r"profum\w+|fragranz\w", " perfume fragrance "),
    (r"cosmetic\w+|trucchi|make-?up|crema|skincare|bellezza", " skincare beauty "), (r"abbigliamento|vestiti|moda|scarpe|sneakers|giacca|felpa", " clothing fashion shoes "),
    (r"borse?|zaino|valigi\w", " handbag "), (r"vino|vini|birr\w|spumante|champagne|prosecco|whisky|gin", " wine beer "), (r"cesto|cesti|box gastronomic\w|forniture? di (?:prodotti|pasta|caffè)|fornitura", " hamper "),
    (r"cioccolat\w+|dolci|biscotti|caffè|tè|merendine|snack|gelat\w", " chocolate snacks coffee "), (r"cena|pranzo|ristorante", " restaurant dinner "),
    (r"spesa|supermercato|esselunga|conad|coop|carrefour|lidl|eurospin|pam|despar", " supermarket grocery "),
    (r"giocattol\w|lego|giochi da tavolo|peluche|puzzle", " toys "), (r"neonat\w|passeggino|bebè|bambino", " baby "), (r"bambini|famiglia|scuola", " kids family "),
    (r"cani?|gatti?|animali|crocchette|cibo per", " dog cat pet "), (r"fitness|sport\w*|palestra|yoga|corsa", " fitness sport "), (r"campeggio|tenda|trekking", " camping outdoor "),
    (r"notte|notti", " night stay hotel "), (r"forno|microonde", " kitchen appliance "), (r"kit di prodotti|kit|prodotti", " bundle "), (r"consulenza", " wellbeing "),
    (r"boombox", " speaker audio "), (r"live show|x factor|sanremo", " tickets show theatre "),
    (r"calendario dell'avvento", " advent calendar "), (r"natale|pasqua|halloween", " christmas "), (r"instant win|gratta e vinci", " instant win "),
])
IT_DOM = r"\b(italia|roma|milano|venezia|firenze|toscana|sicilia|sardegna|puglia|dolomiti|lago di garda|costiera amalfitana|napoli|torino|bologna|gardaland)\b"

EN_LOCAL = {   # English-speaking countries: local shops/places the UK rules don't know
    "ie": _c([(r"dunnes(?: stores)?|supervalu|centra|spar|tesco|lidl|aldi|eurospar|londis|mace|super ?valu", " supermarket "),
              (r"brown thomas|arnotts|penneys|one4all|one 4 all", " shopping voucher "), (r"eircode", " ")]),
    "au": _c([(r"woolworths|woolies|coles|iga|aldi|harris farm", " supermarket "), (r"jb hi-?fi|the good guys|harvey norman|bunnings|myer|david jones|kmart|big w|westfield|prezzee|ultimate gift card", " shopping voucher "),
              (r"ute|4wd|landcruiser|hilux|ranger", " 4x4 car "), (r"esky", " cooler bag "), (r"double pass(?:es)?|in-season pass(?:es)?|family pass(?:es)?", " tickets "),
              (r"breakfast|lunch|brunch", " restaurant meal "), (r"first aid kits?", " household "), (r"footy|afl|nrl|state of origin", " football "), (r"thongs", " sandals "), (r"barbie(?=\s|$)", " bbq ")]),
    "nz": _c([(r"countdown|woolworths|new world|pak'?n'?save|four square|fresh choice", " supermarket "), (r"the warehouse|noel leeming|harvey norman|farmers|briscoes|mitre 10|bunnings|prezzy card|prezzy", " shopping voucher "),
              (r"ute|4wd", " 4x4 car "), (r"double pass(?:es)?|family pass(?:es)?", " tickets "), (r"chilly bin", " cooler bag "), (r"rugby|all blacks|super rugby", " rugby sports "), (r"jandals", " sandals "), (r"bach", " holiday home stay ")]),
}
DOMESTIC = {
    "de": DE_DOM, "fr": FR_DOM, "nl": NL_DOM, "it": IT_DOM,
    "ie": r"\b(ireland|irish|dublin|cork|galway|kerry|killarney|kilkenny|limerick|sligo|donegal|wicklow|wexford|waterford|clare|mayo|connemara|wild atlantic way|belfast)\b",
    "au": r"\b(australia|aussie|sydney|melbourne|brisbane|perth|adelaide|hobart|tasmania|darwin|cairns|gold coast|sunshine coast|byron bay|whitsundays|great barrier reef|uluru|queensland|victoria|new south wales|nsw|qld|kangaroo island|margaret river|noosa|canberra)\b",
    "nz": r"\b(new zealand|aotearoa|auckland|wellington|christchurch|queenstown|rotorua|taupo|wanaka|nelson|dunedin|bay of islands|coromandel|hawke'?s bay|marlborough|fiordland|milford sound|tauranga|waiheke)\b",
}
GLOSS = {"de": DE, "fr": FR, "nl": NL, "it": IT}

def _money_to_gbp_form(t):
    """'500 €' / '€ 1.000' / '$2,500' -> '£500' so the (currency-agnostic in spirit) cash rules apply."""
    out = []; last = 0
    for m, v in util._money_iter(t):
        out.append(t[last:m.start()]); out.append(f"£{v:.0f}"); last = m.end()
    out.append(t[last:])
    return "".join(out)

def english(text, cc=None):
    """Classifier text for country cc: original + English keyword hints (+ normalised money)."""
    cc = cc or util.CUR["cc"]
    if not text or cc == "uk": return text or ""
    t = _money_to_gbp_form(text)
    if cc == "nl": t = re.sub(r"\bvan\b", "of", t, flags=re.I)      # Dutch 'van' (= of/from) is not a van
    if cc == "de": t = re.sub(r"\bvon\b", "from", t, flags=re.I)
    hints = []
    for rx, en in GLOSS.get(cc, []) + EN_LOCAL.get(cc, []):
        if rx.search(t): hints.append(en.strip())
    lead = ""
    if cc in GLOSS and re.search(r"\b(gewinne?n?|gagne[zr]?|remporte[zr]?|win(?:nen)?|vinci|vincere|maak kans)\b", t, re.I): lead = "win "
    return (lead + t + (" | " + " ".join(dict.fromkeys(hints)) if hints else "")).strip()

def domestic(text, cc=None):
    cc = cc or util.CUR["cc"]
    rx = DOMESTIC.get(cc)
    return bool(rx and re.search(rx, text or "", re.I))
