"""Two-level prize taxonomy (category -> sub-category) by ordered keyword rules.

classify(title, desc, hint) -> (category, subcategory). The first matching rule wins, so order matters (specific before generic).
Rules are tried on the title, then on the description, then the 'fallback' rules (cash amounts, generic bundles, instant-win
style titles) on the title, then a weak hint from the source's own category label; anything left is ("Other", "Unclear").
"""
import re
from . import util as _util, gloss as _gloss

def _r(p): return re.compile(p, re.I)

TAXONOMY = {
    "Cars": ["Supercars/Performance", "Luxury", "Electric/Hybrid", "Family/SUV", "Classic/Retro", "Vans/Campers", "Everyday cars"],
    "Motorbikes": ["Motorbikes", "Scooters/Mopeds", "Bicycles/E-bikes"],
    "Boats": ["Yachts/Speedboats", "Jet skis", "Kayaks/Paddleboards", "Narrowboats"],
    "Holidays/Travel": ["UK breaks", "Europe", "Long-haul", "Cruises", "Theme parks/Disney", "Spa/Wellness breaks", "Hotels/Other travel"],
    "Money/Cash": ["Cash lump sum", "Monthly/weekly income", "Mortgage/Bills paid", "Wedding", "Instant wins/Prize pools"],
    "Tech/Gadgets": ["Phones/Wearables", "Laptops/Tablets", "Gaming consoles/PC", "TVs/Audio", "Smart home/Appliances", "Cameras/Drones", "Other tech"],
    "Home/Property": ["Win a house", "Garden/Outdoor", "Furniture/Interiors", "Kitchen", "DIY/Tools", "Cleaning/Household"],
    "Experiences/Events": ["Concert/festival tickets", "Sports tickets", "Theatre/Events", "Days out/Driving experiences", "Meet & greet/VIP"],
    "Gift cards/Vouchers": ["Supermarket", "Shopping", "Restaurants/Takeaway", "Entertainment/Streaming"],
    "Fashion/Beauty": ["Jewellery/Watches", "Handbags/Accessories", "Skincare/Makeup", "Fragrance", "Haircare", "Clothing/Footwear"],
    "Food/Drink": ["Hampers/Food boxes", "Wine/Spirits/Beer", "Restaurant meals", "Snacks/Coffee/Treats"],
    "Family/Kids": ["Toys/Games/Crafts", "Baby/Nursery", "Pets", "Kids/School"],
    "Golf": ["Golf trips/breaks", "Golf equipment", "Golf tickets/events", "Golf lessons/rounds"],
    "Sport/Fitness": ["Gym/Fitness", "Activewear", "Outdoor/Camping/Walking", "Wellbeing/Recovery", "Memorabilia"],
    "Books/Music/Film": ["Books/Audiobooks", "Stationery/Journals", "Music/Vinyl", "Films/TV/Blu-ray", "Magazines/Comics"],
    "Gifts/Bundles": ["Advent calendars", "Seasonal bundles", "Gift sets/Goody bags"],
    "Other": ["Unclear"],
}
CATEGORIES = list(TAXONOMY)
ASSET_CATS = {"Cars", "Motorbikes", "Boats", "Home/Property"}

TRAVEL = r"(holidays?|airways|airlines?|cruise|hotel|resort|flights?|travel|villa|getaway|caravan park|holiday park|break|stay|nights?|trip|safari|retreat)"
rules = []   # (group, category, sub, regex, negative regex|None)
_G = ["x"]
def G(name): _G[0] = name
def R(cat, sub, pat, neg=None):
    assert sub in TAXONOMY[cat], (cat, sub)
    rules.append((_G[0], cat, sub, _r(pat), _r(neg) if neg else None))

# ------------------------------------------------------------------ Money specials
G("money")
R("Money/Cash", "Cash lump sum", r"^\W*(?:win |free (?:entry )?)?(?:up to )?£\s?[\d,.]+\s?[km]?\s*(?:in )?(?:tax[- ]free )?cash\b|\bcash (?:thanks|with|from)\b|\bin cash\b", r"\b(or|\+|&)\s+(?:an?\s+)?(?:apple|iphone|ipad|rolex|car|bmw|audi)")
R("Money/Cash", "Mortgage/Bills paid", r"\b(mortgage|energy bills?|household bills?|bills? (?:paid|cleared|covered)|rent (?:paid|for a year)|pay off (?:your )?debt|clear your debt|council tax)\b", r"\b(mortgage[- ]free (?:house|home))\b")
R("Money/Cash", "Monthly/weekly income", r"£\s?[\d,.]+\s?[km]?\s*(?:a|per|every|each|/)\s*(?:month|week|day|year)\b|\b(?:monthly|weekly) (?:income|salary|pay)\b|\bfor life\b|\bsalary\b|\b(?:a|per) month for\b")
R("Money/Cash", "Wedding", r"\b(dream wedding|your wedding|wedding (?:day|fund|package|of your dreams)|win a wedding|wedding worth|towards (?:your|a) wedding)\b")
# ------------------------------------------------------------------ Vouchers (not travel vouchers: those are holidays)
G("voucher")
SUPER = r"(tesco|asda|lidl|aldi|sainsbury'?s?|morrisons|waitrose|co-?op|iceland|ocado|supermarket|grocer(?:y|ies)|food shop)"
R("Gift cards/Vouchers", "Supermarket", r"(£\s?[\d,]+[^a-z]{0,6}.{0,40}\b" + SUPER + r"\b|\b" + SUPER + r"\b.{0,40}£\s?[\d,]+)", TRAVEL + r"\b")
R("Gift cards/Vouchers", "Restaurants/Takeaway", r"\b(vouchers?|gift ?cards?|e-?gift|credit|to spend|spend at|tokens?)\b.{0,40}\b(restaurant|dining|takeaway|deliveroo|just eat|uber eats|nando'?s|wagamama|pizza express|prezzo|zizzi|meal)\b|\b(restaurant|dining|takeaway|deliveroo|just eat|uber eats|nando'?s|wagamama|prezzo|zizzi)\b.{0,30}\b(vouchers?|gift ?cards?|credit|to spend)\b|£\s?\d+\s+takeaway")
R("Gift cards/Vouchers", "Entertainment/Streaming", r"\b(netflix|spotify|disney\+|prime video|now tv|sky (?:tv|cinema)|streaming|xbox game pass|playstation plus|steam (?:gift|wallet)|itunes|google play)\b.{0,40}\b(gift ?cards?|subscription|vouchers?|credit|months?)\b|\b(gift ?cards?|subscription)\b.{0,30}\b(netflix|spotify|streaming)\b")
R("Gift cards/Vouchers", "Shopping", r"\b(vouchers?|gift ?cards?|e-?gift|gift ?certificates?|spending sprees?|shopping sprees?|\bspends?|site credit|store credit|to spend (?:at|with|on)|spend at|love2shop|buyagift|red letter days|book tokens?|tokens?|rewards? pass|prepaid card|money to spend|towards (?:your )?shopping)\b", TRAVEL + r"\b|\bvoucher code\b")
# ------------------------------------------------------------------ Property
G("property")
R("Home/Property", "Win a house", r"\b(house|home|townhouse|penthouse|cottages?|villa|bungalow|apartment|flat|mansion|farmhouse|barn conversion|new build|dream home|property|castle|lodge)\b.{0,40}\b(in|at|on|near)\b.{0,20}\b[A-Z]|\bwin (?:a|an|the|our|this)\s+(?:[\w£€.,'’-]+\s+){0,5}(house|home|townhouse|penthouse|cottages?|villa|bungalow|apartment|flat|mansion|farmhouse|dream home)\b|\bdream home\b|\b\d[- ]bed(?:room)?s?\b|\bpenthouse\b|\btownhouse\b|\b(?:coastal )?(?:lighthouse )?cottages\b|\b£\s?[\d.,]+\s?(?:m|million)\b.{0,15}\b(house|home)\b",
  r"\b(break|stay|night|nights|getaway|holiday|trip|weekend|retreat|escape|spa|hotel|afternoon tea|dinner|house of|household|housewarming|treehouse|playhouse|dollhouse|house ?plants?|home (?:comfort|prizes|makeover|cinema|gaming|security|delivery|gym|baking|spa)|homeware|work from home|at home|home (?:and|&) garden)\b")
# ------------------------------------------------------------------ Boats
G("boats")
R("Boats", "Jet skis", r"\bjet ?-?skis?\b")
R("Boats", "Narrowboats", r"\bnarrow ?boat")
R("Boats", "Kayaks/Paddleboards", r"\b(kayaks?|canoe|paddle ?-?boards?|sup board|inflatable boat)\b")
R("Boats", "Yachts/Speedboats", r"\b(yachts?(?!-?master)|speed ?boats?|boats?|sailing|\bRIB\b|catamaran|cabin cruiser|dinghy)\b", r"\b(boat (?:shoes|neck|trip|party|cruise)|goat|gravy|lifeboat|rolex|yacht-?master)\b|" + TRAVEL + r"\b.{0,20}\bboat|\bboat\b.{0,25}\b(holiday|stay|break)\b")
# ------------------------------------------------------------------ Bikes / scooters
G("bikes")
R("Motorbikes", "Scooters/Mopeds", r"\b(e-?scooters?|electric scooters?|scooters?|mopeds?|vespa|lambretta|honda c90|c90|super cub)\b", r"\b(kids?|children'?s?|micro|toddler)\s+scooter")
R("Motorbikes", "Motorbikes", r"\b(motorbikes?|motorcycles?|motor ?cycle|harley(?:-davidson)?|ducati|yamaha|kawasaki|ktm|triumph (?:bonneville|street|speed|tiger|rocket|thruxton|trident)|honda (?:cb|crf|cbr|africa|gold)|royal enfield|bmw (?:gs|r ?1|s ?1000)|suzuki (?:gsx|hayabusa)|quad bikes?|dirt bikes?|pit bikes?|trials? bikes?|super ?moto|\bCBR\b|\bgsx\b|\bcb ?\d{3}\b|\byz ?\d+|\bcrf\b)")
R("Motorbikes", "Bicycles/E-bikes", r"\b(bicycles?|e-?bikes?|electric bikes?|mountain bikes?|road bikes?|gravel bikes?|bmxs?|cycle|bikes?)\b", r"\b(exercise|spin|stationary|balance|motor ?bike|kids?)\s*bike|peloton|bike (?:lock|helmet|light|rack)|cycle (?:to|route)|cycleways?|recycl|\bbike\b.{0,20}\b(shop|voucher)")
# ------------------------------------------------------------------ Cars
CARNEG = r"\b(van cleef|van gogh|pokemon|pokémon|jet wash|diagnostic|putter|golf (?:for|club|day)|yacht-?master|toys?|lego|kids?|ride-?on|playset|scale model|model (?:car|kit|railway|train|aircraft|plane)|diecast|car (?:seat|wash|mat|detailing|care|insurance|park|boot)|sat ?nav|hot ?wheels|dash ?cam|race track set|carpet|carton|cardboard|card(?:s)?\b.{0,5}game|mini (?:fridge|oven|beauty|bar|cooper\s+(?:toy|lego)))\b|\btrain\b|lego"
ELEC = r"\b(tesla|model [3sxy]\b|electric (?:car|vehicle|suv|van)|\bev\b|id\.?[3-7]\b|ioniq|polestar|e-?tron|nissan leaf|\bleaf\b|hybrid|plug-?in|kia ev\d|mg ?4|mg ?zs ev|cupra born|bmw i[3-8x]|mini electric|fiat 500e|renault zoe|taycan|lucid|rivian|byd|zero emission|electric)\b"
VANS = r"\b(vans?|campervans?|camper|motorhomes?|motor ?home|caravans?|pick-?ups?|trucks?|transporters?|transit|ranger|hilux|l200|navara|amarok|sprinter|crafter|berlingo|vivaro|trailer|horsebox|tractor|t[4-6]\.?1?|california|ducato|boxer|relay|vauxhall movano|ford transit|vw crafter|day van|conversion|burstner|bürstner|bailey|elddis|auto-?trail|hymer|adria|swift (?:escape|sundance|bolero)|coachman|knaus|dethleffs|chausson|benimar|autosleeper|lunar|marquis)\b"
CLASSIC = r"\b(classic|retro|vintage|heritage|restomod|mk ?[1-4]\b|sierra|escort|capri|cortina|beetle|mini cooper (?:s )?(?:mk|classic)|e-?type|mgb|spitfire|morris|rover mini|(?<![£\d,.])(?:19[5-9]\d|200[0-5])(?![\d,])|cosworth|rs500|celica gt|supra mk|\bmk[12]\b|rx-?7|\bmr2\b)"
SUPERC = r"\b(ferrari|lamborghini|mclaren|porsche|\b911\b|gt3\s?rs?|gt2|gt-?r\b|nissan gt-?r|aston martin|bugatti|pagani|koenigsegg|audi r8|\br8\b|lotus|maserati|corvette|mustang|shelby|camaro|hellcat|viper|supra|\bm[2345] (?:competition|cs|csl|gts)?\b|\bm[2345]\b|\bm ?power\b|\bamg\b|\brs ?[3-7]\b|rs ?q8|\bs[3-8]\b.{0,10}\b(sport|v8|v10)|type[- ]?r|\bgti\b|golf r\b|focus (?:rs|st)\b|fiesta st|civic type|cupra r|megane rs|clio rs|impreza|wrx|\bsti\b|evo(?:lution)?\b|\bgtr\b|\bcosworth\b|v8|v10|v12|supercar|hypercar|track car|bmw m\d|\bgts\b|\bs5\b|\bs3\b|\bs4\b|\bs6\b|\bs7\b|\bs8\b|\bttrs\b|\brs\b|\bct5\b)\b"
LUXURY = r"\b(bentley|rolls-?royce|range rover|maybach|mercedes[- ]?(?:benz)?\s*(?:s[- ]?class|e[- ]?class|c[- ]?class|gle|gls|g[- ]?class|g63|g[- ]?wagon)|g[- ]?wagon|defender|lexus|jaguar|genesis|bmw (?:7|8|x[5-7]m?)|\bx[5-7]m\b|audi (?:a[6-8]|q[7-8])|porsche (?:cayenne|panamera|macan)|volvo xc90|land rover (?:discovery|defender)|discovery|velar|evoque|urban|vogue|autobiography|luxury)\b"
SUV = r"\b(suv|4x4|crossover|tiguan|touareg|t-?roc|q[2-8]\b|x[1-7]\b|qashqai|juke|kuga|puma|sportage|sorento|tucson|santa fe|cr-?v|rav4|outlander|captur|duster|3008|5008|2008|karoq|kodiaq|ateca|arona|tarraco|gle|glc|discovery sport|range rover sport|estate|touring|family car|people carrier|mpv|seven seater|7 seater|jimny|bronco|cayenne|macan)\b"
CARBRANDS = r"(\bcars?\b|\byaris\b|\bcorolla\b|honda civic|civic type|(?:vw|volkswagen) golf|golf (?:gti|r|tdi)\b|(?:vw|volkswagen) polo|polo gti|ford focus|ford fiesta|\bastra\b|\bcorsa\b|\bclio\b|\bmegane\b|\bmini countryman\b|\bjuke\b|\bqashqai\b|\baudi\b|\bbmw\b|\bmercedes|\bporsche\b|range rover|land rover|defender|\bford\b|mustang|volkswagen|\bvw\b|tesla|lamborghini|ferrari|mclaren|bentley|rolls-?royce|aston martin|jaguar|nissan|toyota|honda|skoda|cupra|volvo|lexus|\bkia\b|hyundai|vauxhall|peugeot|renault|citroen|mazda|subaru|lotus|maserati|alfa romeo|jeep|dodge|chevrolet|corvette|cosworth|amg|\brs[3-7]\b|rsq8|gt3|transporter|go-?kart|\bmini cooper\b|\bsubaru\b|\bfiat\b|\bsuzuki\b|\bdacia\b|\bbyd\b|\bpolestar\b|\bmitsubishi\b|\bsmart (?:car|fortwo)\b|\b\d{4} (?:audi|bmw|ford|vw|mercedes|porsche|nissan|toyota|honda|volvo|jaguar|land|range|tesla|mini|seat|skoda|kia|hyundai))\b"
def _car_sub(t):
    s = t
    if re.search(ELEC, s, re.I): return "Electric/Hybrid"
    if re.search(VANS, s, re.I) and not re.search(r"\b(vanilla|vanessa|advance|van gogh)\b", s, re.I): return "Vans/Campers"
    if re.search(CLASSIC, s, re.I)  or re.search(r"(?<![£\d,.])(?:19[5-9]\d|200[0-5])(?![\d,]).{0,30}" + CARBRANDS, s, re.I): return "Classic/Retro"
    if re.search(SUPERC, s, re.I): return "Supercars/Performance"
    if re.search(LUXURY, s, re.I): return "Luxury"
    if re.search(SUV, s, re.I): return "Family/SUV"
    return "Everyday cars"

# ------------------------------------------------------------------ Holidays
G("holspecial")
R("Holidays/Travel", "Theme parks/Disney", r"\b(disney(?:land)?(?: paris| world)?|walt disney|legoland|alton towers|thorpe park|chessington|universal studios|theme parks?|paultons|peppa pig world|warner bros\.? studio|drayton manor|flamingo land|blackpool pleasure)\b.{0,40}\b(holiday|trip|resort|world|land|park|parks|cruise|break|tickets?|stay|visit|day|entry)\b|\b(holiday|trip|tickets?|break)\b.{0,30}\bdisney", r"\b(on blu-?ray|on ice|4k|dvd|plus|\+|toy|plush|lego set|book|film|musical)\b")
R("Holidays/Travel", "Cruises", r"\b(cruises?|cruising|msc|p&o|norwegian|royal caribbean|azamara|celebrity cruises|princess|fred\. olsen|ambassador|river cruise)\b", r"\bprincess (?:diana|leia|bride)|norwegian wood")
R("Holidays/Travel", "Spa/Wellness breaks", r"\b(spa (?:break|stay|weekend|retreat|escape|getaway|hotel|resort)|wellness (?:retreat|break|weekend|stay)|yoga retreat|health retreat|detox retreat|retreat)\b|\b(?:night|nights?)\b.{0,40}\bspa\b|\bspa\b.{0,40}\b(?:night|nights|stay|break)\b")
LONGH = r"\b(dubai|abu dhabi|maldives|caribbean|barbados|jamaica|antigua|st lucia|bahamas|cuba|dominican|mexico|cancun|bali|thailand|phuket|vietnam|japan|tokyo|kyoto|singapore|hong kong|china|india|goa|sri lanka|mauritius|seychelles|zanzibar|kenya|tanzania|south africa|cape town|safari|egypt|morocco|marrakech|australia|sydney|new zealand|fiji|hawaii|las vegas|new york|nyc|los angeles|california|florida|orlando|miami|usa|america|canada|toronto|vancouver|banff|brazil|peru|costa rica|bora bora|tahiti|long[- ]haul|st\.? barts|oman|qatar|jordan|petra|bangkok|jordan)\b"
EURO = r"\b(spain|spanish|majorca|mallorca|menorca|ibiza|tenerife|canary|canaries|lanzarote|fuerteventura|gran canaria|costa del sol|costa brava|portugal|algarve|lisbon|madeira|azores|italy|italian|rome|venice|florence|milan|tuscany|amalfi|sicily|sardinia|lake garda|greece|greek|crete|corfu|santorini|rhodes|kos|zante|mykonos|athens|paris|france|french|riviera|provence|nice|amsterdam|netherlands|belgium|brussels|bruges|barcelona|madrid|seville|prague|budapest|vienna|berlin|germany|munich|croatia|dubrovnik|split|montenegro|turkey|bodrum|cyprus|malta|bulgaria|iceland|norway|sweden|stockholm|denmark|copenhagen|finland|lapland|swiss|switzerland|austria|alps|ski(?:ing)?|europe(?:an)?|city break|poland|krakow|estonia|tallinn|riga|dolomites|courchevel|val d'?isere|verbier)\b"
UKH = r"\b(uk|britain|british|england|english|scotland|scottish|wales|welsh|northern ireland|cotswolds?|cornwall|devon|dorset|somerset|norfolk|suffolk|kent|sussex|brighton|hampshire|surrey|yorkshire|york|lake district|lakes|peak district|snowdonia|brecon|pembrokeshire|northumberland|durham|highlands|edinburgh|glasgow|london|manchester|birmingham|liverpool|leeds|chester|bath|cambridge|oxford|stratford|isle of (?:wight|skye|man|arran)|scilly|jersey|guernsey|new forest|center parcs|centre parcs|butlins|haven|bluestone|hoburne|parkdean|premier inn|travelodge|national trust|english heritage|staycation|cottage|lodge|castle|country (?:house|hotel)|inn|glamping|lowry|the pig|cheltenham|tenby|whitby|lyme regis|st ives|newquay|padstow|southwold|aldeburgh|windermere|keswick|bakewell|harrogate|llandudno|blackpool|torquay|cardiff|swansea|belfast|newcastle|sheffield|nottingham|leicester|bristol|exeter|plymouth|falmouth|whitstable|margate|broadstairs|hertfordshire|essex|chichester|bournemouth|poole|weymouth|ladram bay|coastline|seaside|coastal)\b"
HOLW = r"\b(holidays?|breaks?|getaways?|stays?|hotels?|resorts?|flights?|trips?|travel|villas?|safari|escape|staycation|weekend away|all[- ]inclusive|glamping|retreat|adventure holiday|honeymoon|bed (?:&|and) breakfast|b&b|city break|ski|(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fourteen)[- ]?nights?|weeks?\s+(?:in|at|away|on)|overnight|nights? (?:stay|in|at|away))\b"
HOLNEG = r"\b(hotel chocolat|escape room|great snake escape|travel (?:set|bag|pillow|accessories)|family ticket|take a break|gift set|(?<!and )(?<!& )break ?fast|tea break|late night|movie night|night in|coffee break|lunch break|stay (?:warm|cool|safe|hydrated|healthy|connected|in touch)|break ?through|break ?dance|jailbreak|outbreak|prison break|trip ?wire|stay ?at ?home|stays? tuned)\b|\bwin (?:a )?(?:copy|book)|\b(book|novel|dvd|blu-?ray|album|voucher code|instant wins?)\b"
def _hol_sub(t):
    if _util.CUR["cc"] != "uk" and _gloss.domestic(t): return "UK breaks"    # = 'domestic'; relabelled per country in the site JSON
    if re.search(LONGH, t, re.I) and not re.search(r"\b(new york (?:times|yankees)|florida water|california roll)\b", t, re.I): return "Long-haul"
    if re.search(EURO, t, re.I): return "Europe"
    if re.search(UKH, t, re.I): return "UK breaks"
    return "Hotels/Other travel"

# ------------------------------------------------------------------ Experiences
SPORTS = r"\b(football|soccer|premier league|champions league|arsenal|chelsea|tottenham|spurs|liverpool|man(?:chester)? (?:united|city)|everton|west ham|newcastle|aston villa|celtic|rangers|fc\b|lille|losc|rugby|six nations|nations championship|lions tour|cricket|the hundred|ashes|tennis|wimbledon|queen'?s club|laver cup|atp|wta|golf|ryder cup|the open|boxing|ufc|wwe|darts|snooker|f1|formula (?:1|one|e)|grand prix|silverstone|motogp|nascar|racing|races?|race meeting|horse racing|ascot|cheltenham festival|aintree|grand national|derby day|goodwood|marathon|olympics|athletics|diamond league|basketball|nba|nfl|ice hockey|hockey|netball|stadium|match(?:day)? (?:tickets?|hospitality)|hospitality)\b"
TICKETISH = r"\b(tickets?|seats?|hospitality|box|passes|pass|place at|places at|admission|entry to|vip|to see|to watch|to attend|to experience|to the)\b"
G("tickets")
R("Experiences/Events", "Meet & greet/VIP", r"\b(meet (?:&|and) greets?|meet the|backstage|album playback|listening (?:party|session)|exclusive (?:event|access|screening|preview|playback)|fan experience|vip (?:experience|package|tickets?|access|fan)|vip\b)\b")
R("Experiences/Events", "Days out/Driving experiences", r"\bfamily (?:ticket|pass|day)s?\b|\b(zoo|zoological|aquarium|safari park|wildlife park|farm park|adventure park|water park|attractions?|castle|cathedral|gardens?|abbey|palace|light (?:trail|experience)|illuminat\w+|family (?:day|ticket|pass)|day out|racecourse|heritage|railway|steam train|planetarium|sanctuary|museum)\b.{0,50}\b(tickets?|passes|pass|entry|admission|day|visit)\b|\b(tickets?|passes|pass|entry|admission|visit)\b.{0,50}\b(zoo|zoological|aquarium|safari park|wildlife park|farm park|adventure park|water park|attractions?|castle|cathedral|gardens?|abbey|palace|light (?:trail|experience)|racecourse|railway|steam train|planetarium|sanctuary)\b")
R("Experiences/Events", "Sports tickets", r"(" + TICKETISH + r".{0,80}" + SPORTS + r"|" + SPORTS + r".{0,60}" + TICKETISH + r"|\b\w+ (?:v|vs\.?) \w+\b.{0,30}(?:tickets?|seats?)|(?:tickets?|seats?).{0,40}\b\w+ (?:v|vs\.?) \w+\b)", r"\b(shirt|kit|boots|signed|memorabilia|voucher|tour|concert|gig|oasis|live in)\b")
R("Experiences/Events", "Theatre/Events", r"\b(theatre|theater|musical|west end|opera|ballet|comedy|comedian|stand-?up|panto|pantomime|circus|cabaret|cirque|playhouse|mean girls|live experience|traitors|on ice|magic show|illusion|wicked|mamma mia|lion king|hamilton|matilda|les mis|phantom|six the musical|cinema|film (?:premiere|screening)|premiere|screening|exhibition|museum|gallery|comic[- ]?con|convention|expo|show\b|the play\b|play at|brit awards|awards|quartet|live (?:show|event|recording)|lowry|palladium|old vic|national theatre|royal albert hall|ice show|ice skating|christmas market|fair\b)\b.{0,60}\b(tickets?|seats?|to see|entry|admission|passes?|places?|night|experience)\b|\b(tickets?|seats?|to see|passes?)\b.{0,60}\b(theatre|theater|musical|west end|opera|ballet|comedy|comedian|panto|pantomime|circus|cabaret|cinema|premiere|screening|exhibition|museum|comic[- ]?con|convention|expo|brit awards|awards|quartet|show)\b")
R("Experiences/Events", "Concert/festival tickets", r"(\b(concert|festival|gig|gigs|live in|live at|live\b|tour|arena|o2|wembley|hyde park|bestival|glastonbury|reading|download|latitude|wireless|capital'?s? (?:summertime|jingle)|jingle bell|summertime ball|bbc proms|proms|radio \d|band|singer|dj|rave|club night|orchestra|symphony|choir)\b.{0,60}" + TICKETISH + r"|" + TICKETISH + r".{0,60}\b(concert|festival|gig|live|tour|arena|o2|wembley|bestival|proms|band|singer|dj|orchestra)\b|\btickets? (?:to|for) see\b|\btickets? to \w+)")
R("Experiences/Events", "Concert/festival tickets", r"\btickets?\b", r"\b\d[\d,]*\s+(?:house\s+)?tickets|tickets? (?:for|worth|\d|5p|£)|a ticket|per ticket|instant win|raffle|house tickets|\bcomp\b|entries|every ticket|ticket tout|rolex|limited tickets|ticket(?:s)? (?:left|sold)")
G("restaurant")
R("Food/Drink", "Restaurant meals", r"\b(restaurants?|dinner (?:for|at)|lunch (?:for|at)|brunch|dining|afternoon tea|tasting menu|meal (?:for|at|out)|supper|michelin|fine dining|steakhouse|burgers?|pizza (?:for|night)|sunday roast|fish (?:&|and) chips|fish and chip|curry night|a night out|date night|nandos|wagamama|gaucho|hawksmoor|pizza express|honest burgers|five guys|chef'?s table)\b", r"\b(cookbook|book|vouchers?|gift ?cards?|credit|hamper|kit|box|break|stay|night stay|nights? at|overnight|hotel)\b")
G("daysout")
R("Experiences/Events", "Days out/Driving experiences", r"\b(day out|days out|family (?:day|ticket|pass)|driving experience|supercar (?:experience|driving)|track day|zoo|aquarium|safari park|theme park|attractions?|spa days?|spa experience|massage experience|skydiv\w*|sky ?dive|bungee|zip ?wire|go[- ]?kart(?:ing)?|escape room|bowling|laser (?:tag|quest)|trampoline park|adventure park|balloon (?:flight|ride)|helicopter|boat trip|river trip|walking tour|brewery tour|distillery tour|vineyard|cookery (?:class|course|school)|cooking (?:class|lesson)|masterclass|workshop|lessons?|experience (?:day|for)|an? experience|gift experience|annual pass|membership|national trust|english heritage|entry for|golf day|spa days?|science (?:centre|center|museum)|passports?|ladies day|race ?day|racecourse|polo|fishing day|falconry|archery|paintball|axe throwing|wine tasting|gin tasting|spa pass|day pass)\b", r"\bgym\b|\b(mattress|insurance|netflix|spotify)\s+membership|\b(12|one)[- ]?(?:months?|year)s?\b.{0,20}gym|lessons? (?:learned|plan)")

# ------------------------------------------------------------------ Holiday rule (needs custom sub) -- inserted via function below
# ------------------------------------------------------------------ Books / music / film
G("media")
R("Books/Music/Film", "Films/TV/Blu-ray", r"\b(blu-?ray|dvd|4k ultra hd|4k uhd|box ?set|on 4k|film|movie|the complete series|digital download|steelbook)\b", r"\b(tickets?|premiere|screening|cinema|tv|inch|smart)\b")
R("Books/Music/Film", "Music/Vinyl", r"\b(vinyl|records?|lps?|cds?|album|signed guitar|ukulele|music (?:box|lesson)|merch(?:andise)?)\b", r"\b(record player|turntable|tickets?|playback|gaming|hot|world records?|resolutions?|medical records?|brewery|beers?|experience)\b|\bkeyboard\b")
R("Books/Music/Film", "Magazines/Comics", r"\b(magazines?|comics?|comic books?|graphic novels?|manga)\b", r"\b(netflix|spotify|disney|streaming|gym)\b")
R("Books/Music/Film", "Books/Audiobooks", r"\b(books?|novels?|cookbooks?|cook books?|recipe books?|paperbacks?|hardbacks?|hardcovers?|copy of|copies of|signed copy|bestsellers?|author|audiobooks?|audio dramas?|audio books?|trilogy|book bundle|children'?s books?|picture books?|book set|prize shortlist|booker|reading|kindle (?:books?|unlimited))\b", r"\b(book (?:a|your|now|tickets?|online)|booking|bookmaker|bookcase|bookshelf|bookshelves|shelving|book nook kit|notebook)\b")
R("Books/Music/Film", "Stationery/Journals", r"\b(journals?|notebooks?|pencils?|art prints?|posters?|diary|diaries|planner|stationery|pens?|fountain pen|calendars?|stickers?|bookmark|book nook|bookclub|book club)\b", r"\b(smart|skylight|digital|advent|ticket)\b|\bpen\b.{0,5}\b(sion|alty)\b")

# ------------------------------------------------------------------ Tech
G("tech")
R("Tech/Gadgets", "Cameras/Drones", r"\b(cameras?|gopro|drones?|dji|canon|nikon|sony alpha|fujifilm|instax|polaroid|lens|camcorder|binoculars?|telescope|insta360|webcam|dash ?cam)\b", r"\b(camera ?man|cameraman|camera crew|camera ready)\b")
R("Tech/Gadgets", "Gaming consoles/PC", r"\b(playstation|ps ?[2345]\b|ps5 pro|xbox|nintendo|switch(?: 2| oled| lite)?\b|steam (?:deck|machine)|gaming|gamer|(?<!\d)(?<!\d )pc\b|gpu|rtx|graphics card|console|controller|razer|logitech|corsair|steelseries|keyboard|mouse|headset|monitor|grand theft auto|gta ?(?:v|vi|6|5)?\b|call of duty|fifa|ea sports|fc ?2\d|video games?|game pass|pre-?order|cherry|xtrfy|pc build|rog\b|alienware|msi|asus|omen|hp omen|meta quest|oculus|vr headset|retro (?:console|gaming)|arcade machine)\b", r"\b(board game|card game|games? night|game (?:of thrones)|pokemon cards?|trading cards?)\b")
R("Tech/Gadgets", "Phones/Wearables", r"\b(iphone|i phone|samsung galaxy|galaxy s\d+|galaxy z|pixel \d|google pixel|smartphones?|mobile phones?|phones?|oneplus|xiaomi|huawei|oppo|nothing phone|apple watch|smart ?watch|fitbit|garmin|whoop|oura|galaxy watch|wearables?|fitness tracker|airpods)\b", r"\b(phone (?:box|case|call|in)|on-?air|phone-?in|online, phone|phone, text|postal)\b|\bcall\b|\bwatch(?:es)?\b.{0,5}\b(rolex|omega)\b")
R("Tech/Gadgets", "Laptops/Tablets", r"\b(macbook|mac mini|imac|laptops?|ipad|tablets?|notebook computer|chromebook|surface (?:pro|laptop|go)|kindle|e-?readers?|kobo|galaxy tab|computer|computers)\b", r"\b(tablet(?:s)?\b.{0,10}\b(vitamin|supplement)|ipad (?:case|cover))\b")
R("Tech/Gadgets", "TVs/Audio", r"\b(tvs?|televisions?|oled|qled|smart tv|4k tv|\d{2}\"? ?(?:inch )?tv|soundbars?|sound ?bars?|speakers?|headphones?|earbuds?|earphones?|jbl|bose|sonos|sony wh|beats|marshall|bang (?:&|and) olufsen|hi-?fi|turntable|record player|projector (?!&)|home cinema|bluetooth|dab radio|radio set|karaoke|noise[- ]cancelling|wireless (?:speaker|earbuds|headphones)|amp\b)\b", r"\b(tv (?:show|series|star|presenter|quiz|licen[cs]e)|on tv|bbc|itv|channel \d|tv chef|tv ?times)\b")
R("Tech/Gadgets", "Other tech", r"\b(3d printers?|printers?|scanners?|netgear|routers?|hotspot|wi-?fi|mesh|modem|smart glasses|ai (?:glasses|gadget|device|pin)|alcosense|breathalys\w+|usb|hard drive|ssd|memory card|e-?ink|sat ?nav|power ?bank|charger|solar (?:panel|charger|power)|walkie|translator|ring light|tripod|gimbal)\b", r"\b(lego|toy)\b")
R("Tech/Gadgets", "Smart home/Appliances", r"\b(robot vacuums?|robotic vacuum|vacuum|hoover|dyson|shark (?:vacuum|steam|stratos|flexstyle)|roomba|smart (?:home|speaker|display|plug|bulb|lock|thermostat|heating|calendar|mirror|doorbell|light)|alexa|echo (?:dot|show|pop|hub|spot)|google nest|nest (?:hub|thermostat|cam)|ring (?:doorbell|camera|alarm|video)|hive|philips hue|\bhue\b|wiser|heating kit|thermostat|video doorbell|cctv|security camera|air purifier|humidifier|dehumidifier|water (?:dispenser|filter|purifier|softener)|waterdrop|ro system|steam mop|steam cleaner|washing machine|tumble dryer|garment steamer|skylight|smart (?:home|speaker|display|plug|bulb|lock|thermostat|heating|calendar|mirror|doorbell|light|scale|bin)|airtag|power ?bank|gadgets?|tech bundle|electronics?|e-?cig)\b", r"\b(smart (?:price|choice|meter reading|games?)|iron ?man|ironing board|vacuum[- ]sealed|solar system|orbiting|airwrap|supersonic|toothbrush|lego|puzzle|board game)\b")

# ------------------------------------------------------------------ Home
G("home")
R("Home/Property", "Kitchen", r"\b(fridge|freezer|fridge freezer|dishwasher|ovens?|hobs?|cookers?|range cooker|microwave|air ?fryers?|coffee (?:machines?|makers?)|espresso|nespresso|tassimo|dolce gusto|kettles?|toasters?|blenders?|nutribullet|kitchen ?aid|stand mixer|food processor|ninja (?:foodi|creami|blender|air|slow)|le creuset|staub|tefal|sage (?:barista|bambino)|slow cooker|pressure cooker|instant pot|saucepans?|frying pans?|cookware|pans?|knife (?:set|block)|knives|cutlery|crockery|dinnerware|dinner set|tableware|glassware|sodastream|water tap|boiling water tap|hot water tap|hot tap|tap\b|waffle|pizza oven|ooni|juicer|breadmaker|bread maker|kitchen|appliances?|smeg|casserole|procook|roasting tin|utensils|bakeware|baking (?:tin|set|kit)|lunch ?box|flask|hydro ?flask|stanley cup|tupperware)\b", r"\b(cookbooks?|cook books?|recipe books?|cooking (?:class|lesson|course)|kitchen (?:tour|party)|panty|pans out)\b")
R("Home/Property", "Cleaning/Household", r"\b(clean(?:er|ers|ing)|detergent|laundry|washing (?:powder|liquid|up)|fabric (?:softener|conditioner)|bleach|disinfectant|mop|dishwasher tablets|bin bags|household (?:bundle|essentials)|toilet roll|kitchen roll|sponges?|stain remover)\b", r"\b(skin|face|facial|teeth|hair|make-?up)\b")
R("Home/Property", "Garden/Outdoor", r"\b(gardens?|gardening|patio|bbqs?|barbecues?|hot tubs?|fire ?pits?|sheds?|greenhouses?|lawn ?mowers?|mowers?|strimmer|plants?|bulbs?|seeds?|outdoor (?:furniture|living|kitchen|cooking|heater|lighting)|garden (?:furniture|set|room|office|tools?)|gazebo|parasol|summer ?house|pergola|decking|water butt|bird ?(?:feeder|table|box|bath)|hanging basket|compost|raised bed|pond|swing set|trampoline|wildlife|weber|traeger|ninja woodfire|solo stove|chiminea|sun ?lounger|hammock|trees?|terrarium|aerator|scarifier|pool (?:skimmer|cover|pump)|moss|planters?|jacuzzi|swim ?spa|paddling pool|pizza oven|ooni)\b", r"\b(plant-?based|plants? vs|power plant|seed (?:funding|round)|seeded)\b")
G("diy")
R("Home/Property", "DIY/Tools", r"\b(tools?|tool ?kit|toolkit|tool ?box|cordless|drills?|milwaukee|makita|bosch|dewalt|stanley|ryobi|karcher|kärcher|pressure washers?|decorating|paint(?:ing)?|dulux|farrow|wickes|b&q|screwfix|diy|workbench|power tools?|ladder|spirit level|workwear|flooring|tiles?|radiator|boiler|home improvement|renovation)\b", r"\b(paint(?:ing)? by numbers|face paint|nail|painting kit|art|beauty|tools? for|tool kit for kids|tool bag)\b")
G("home")
R("Home/Property", "Furniture/Interiors", r"\b(sofas?|couch|armchair|bed ?(?:frame|set)?|beds\b|mattress(?:es)?|pillows?|duvet|bedding|bed linen|sheets|furniture|wardrobe|desk|bookcase|bookshelf|shelving|shelves|cabinet|sideboard|dining (?:table|set)|coffee table|rug|rugs|curtains?|blinds|wallpaper|lighting|lamps?|chandelier|candles?|cushions?|throws?|blankets?|vases?|mirrors?|clocks?|interiors?|decor|homeware|home (?:comfort|prizes|makeover|bundle|accessories|essentials)|makeover|room makeover|bathroom|shower|wet room|towels?|storage|ottoman|doormats?|bunk|armoire|headboard|nightstand|chair|chairs|stool|table)\b", r"\b(chair(?:man|person)|table (?:tennis|football)|tables? at|sleep(?:ing)? bag|candle ?(?:light dinner))\b|\b(mattress|sleep) (?:expert)\b")

# ------------------------------------------------------------------ Sport / fitness (before fashion)
G("sport")
R("Sport/Fitness", "Memorabilia", r"\b(memorabilia|signed\b.{0,40}\b(?:shirt|ball|boots|glove|bat|helmet|jersey)|replica\b.{0,40}\bhelmet|helmets?|match[- ]worn|autographed?)\b")
# (golf has its own top-level category: see _golf() below)
R("Sport/Fitness", "Gym/Fitness", r"\b(gym|fitness|workout|work-?out|yoga|pilates|peloton|treadmill|rowing machine|exercise bike|spin bike|dumb-?bells?|kettle-?bells?|weights?|resistance bands?|home gym|crossfit|boxing (?:gloves|bag|kit)|punch ?bag|personal train(?:er|ing)|online coaching|coaching|training plan|supplements?|protein|whey|creatine|smoothie maker|running machine|cross trainer|stepper|hoola|skipping|membership)\b", r"\b(fitbit|garmin|apple watch|tickets?)\b")
R("Sport/Fitness", "Activewear", r"\b(activewear|sportswear|gymwear|leggings|sports bra|running (?:shoes|trainers|kit|gear)|football (?:kit|shirt|boots)|(?:rugby|cricket|tennis) (?:kit|racket|bat|shirt)|trainers|nike|adidas|puma|new balance|asics|under armour|lululemon|gymshark|sweaty betty|on running|hoka|brooks|skechers|reebok|fila|umbro|kit bundle)\b")
R("Sport/Fitness", "Outdoor/Camping/Walking", r"\b(camping|tents?|sleeping bags?|rucksacks?|backpacks?|hiking|walking (?:boots|shoes|poles|gear|jacket)|walking|climbing|outdoor (?:gear|clothing|kit|jacket)|waterproof|gore-?tex|le chameau|barbour|hunter (?:boots|wellies)|wellies|wellington|fishing|angling|reel|daiwa|tackle|carp rod|fishing rod|surf(?:board|ing)?|wetsuit|paddle|ski (?:kit|jacket|gear)|snowboard|meindl|sprayway|berghaus|north face|patagonia|rab\b|craghoppers|regatta|trespass|lifeventure|trekking|compass|binoculars)\b", r"\b(tickets?|break|holiday|stay|hotel|cottage)\b")
R("Sport/Fitness", "Wellbeing/Recovery", r"\b(massage guns?|massagers?|massage chair|foam roller|recovery|sleep (?:aid|kit|mask|tracker|pod)|meditation|mindfulness|wellbeing|well-?being|wellness|self[- ]care|vitamins?|health (?:consultation|check|bundle|box)|nutritionist|detox|weight loss|therapy|acupuncture|aromatherapy|essential oils?|diffuser|sauna|cold plunge|ice bath|hydration|breathwork)\b", r"\b(retreat|break|holiday|stay|hotel|weekend)\b")

# ------------------------------------------------------------------ Fashion / beauty
G("family")
R("Family/Kids", "Pets", r"\b(dogs?|puppy|puppies|cats?|(?<!candy )kittens?|pets?|pet (?:food|bed|insurance|supplies)|dog (?:food|bed|treats|toys?|lead)|cat (?:food|tree|treats)|horses?|rabbits? (?:food|hutch)|hamster|aquarium|fish tank|bird (?:food|cage)|pooch|canine|feline|lily'?s kitchen|pedigree|whiskas|tails\.?com|burns pet|purina|royal canin|barking|feliway|animal)\b", r"\b(hot dogs?|dog days|cat ?walk|catwalk|cat(?:alogue|ch|ering)|peter rabbit|top dog|copycat|pet (?:shop boys)|petal|fish (?:&|and) chips|fish and chip|learning|dogs? (?:trust))\b")
R("Family/Kids", "Baby/Nursery", r"\b(baby|babies|newborn|toddler|infant|wet wipes|wipes|pushchairs?|prams?|strollers?|buggy|car seats?|nappies|nappy|nursery|cots?|crib|moses basket|maternity|mum-?to-?be|pregnan\w+|breast ?pump|baby (?:monitor|bundle|box|clothes|shower)|mamas? (?:&|and) papas?|silver cross|bugaboo|cybex|joie|maxi-?cosi|made ?for ?mums)\b")
R("Family/Kids", "Toys/Games/Crafts", r"\b(toys?|lego|duplo|playmobil|dolls?|barbie|playsets?|plush|soft toys?|jellycat|teddy(?: bear)?|teddies|squishmallows?|board games?|card games?|games? (?:bundle|night|set)|puzzles?|jigsaws?|pokemon|pokémon|yu-?gi-?oh|trading cards?|funko|collectables?|collectibles?|clickeez|figures?|figurines?|action figures?|warhammer|nerf|hot ?wheels|play-?doh|crafts?|craft (?:kit|set|box)|art (?:set|kit|supplies)|colouring|sewing|knitting|crochet|model (?:kit|railway|trains?|car|aircraft)|scalextric|train set|ride-?on|scooter|trampoline|playhouse|play kitchen|slime|fidget|bubble pops?|racing line games|snap|uno|monopoly|top trumps|sylvanian|peppa|vtech|leapfrog|fisher-?price|little tikes|hasbro|mattel|hornby|rc car|remote control|arrma|paw patrol|bluey|spider-?man|marvel|avengers|star wars|harry potter|disney (?:princess|toys)|frozen|encanto|moana|minecraft|roblox|fortnite|bundle of .{0,20}goodies|peter rabbit|book nook (?:kit)|diy kit|dollhouse|dobble|ride-?ons?|upc\b|etb\b|booster (?:packs?|boxes?)|tcg|kids? (?:bundle|gift)|children'?s (?:gift|toy)|goodies)\b", r"\b(tickets?|film|dvd|blu-?ray|disney (?:holiday|world|land|trip)|video games?|xbox|playstation)\b")
R("Family/Kids", "Kids/School", r"\b(kids?|child(?:ren)?'?s?|school|back to school|lunch ?boxes?|pencil case|school bag|uniform|teenager|teens?|family (?:bundle|prize|pack|fun|hamper)|schoolwear|nursery|parents?|mums?|dads?|mumsnet|grandparents?)\b")
# ------------------------------------------------------------------ Gifts / bundles
G("fashion")
R("Fashion/Beauty", "Fragrance", r"\b(perfumes?|fragrances?|eau de (?:parfum|toilette)|cologne|aftershave|parfum|creed|jo malone|scent(?:s)? (?:set|bundle|collection)|chanel (?:no|n°)|armani (?:code|si)|ysl|paco rabanne|hugo boss|dior sauvage|bottle of (?:creed|chanel|dior))\b", r"\b(scent-?free|scented candles?|candle)\b")
R("Fashion/Beauty", "Haircare", r"\b(hair(?: ?care|dryers?| dryer| straighteners?| ?tools?| ?products?| ?styler| ?brush| ?mask|oil|spray|wax)?|ghd|airwrap|supersonic|straighteners?|curling (?:tongs|wand|iron)|shampoo|conditioner|cloud nine|babyliss|salon|barber|haircut|hair ?extensions?|wigs?)\b", r"\b(hair (?:of the dog)|chair)\b")
R("Fashion/Beauty", "Jewellery/Watches", r"\b(rolex|omega|tag heuer|tissot|seiko|breitling|cartier|patek|audemars|hublot|casio|g-?shock|citizen|rado|longines|tudor|swatch|moonswatch|watch(?:es)?|jewel(?:l)?ery|necklaces?|bracelets?|bangles?|pendants?|earrings?|charms?|pandora|swarovski|tiffany|silver (?:proof )?coins?|gold coins?|proof coins?|\d+\s?oz|bullion|diamonds?|moissanite|gold|silver|gemstones?|pearls?|engagement rings?|wedding rings?|signet rings?|eternity rings?|rings? (?:from|by|set)|\bring\b.{0,15}\b(gold|silver|diamond)|cufflinks|birthstone|brooch|tiara)\b", r"\b(smart ?watch|apple watch|fitbit|garmin|watch (?:tv|the|out|party|later|free|live|this)|gold(?:en)? (?:ticket|rush|standard|bar of soap)|silver (?:screen|lining)|golden|goldfish|gold coast|bracelet.{0,5}\b(sensor)|diamond (?:geezer|jubilee)|sunday|kingsman)\b")
R("Fashion/Beauty", "Handbags/Accessories", r"\b(handbags?|hand bags?|purses?|wallets?|tote(?:s| bag)?|clutch|satchel|shoulder bag|crossbody|backpack|duffle|duffel|holdall|weekender|luggage|suitcases?|cabin bag|louis vuitton|chanel (?:bag|classic|flap)|gucci|prada|dior|hermes|hermès|coach|michael kors|kate spade|mulberry|radley|longchamp|ray-?bans?|sunglasses|scarf|scarves|umbrella|bags?)\b", r"\b(goody|gift|party|tea|bean|sleeping|sandwich|lunch|beauty|carrier|plastic|paper|crisp|bag of|bags of|bag for life|bagels?|bag-?pipes?|bagpipes|sandbag|baggage|air ?fryer|vacuum|coffee)|(goody|gift|bean|sleeping|beauty|lunch|tea|party|kit) bags?\b|bag clips?|heat resistant bag")
R("Fashion/Beauty", "Skincare/Makeup", r"\b(skin ?care|skin|serums?|moisturi[sz]ers?|cleansers?|toners?|face (?:masks?|creams?|oil|wash|palette)|eye (?:cream|shadow|liner)|make-?up|lipsticks?|lip (?:gloss|balm|kit)|mascara|foundation|concealer|blush|bronzer|palette|cosmetics?|beauty|facials?|body (?:lotion|butter|scrub|essence|oil|wash|care)|bath (?:bomb|bombs|set|products?|salts)|bubble bath|shower gels?|soaps?|nails?|manicure|gel polish|nail polish|lashes?|brow|oral care|toothpaste|toothbrush|whitening|teeth|razors?|shaving|beard|grooming|deodorant|spf|sun ?cream|sunscreen|lotion|ceramide|retinol|collagen|murad|spa (?:products|gift|set|hamper)|pamper(?:ing)?|self-?care|essence|illiyoon|k-?beauty|elemis|clinique|estee lauder|charlotte tilbury|lookfantastic|cult beauty|boots no7|the ordinary|olay|nivea|dove|simple|garnier|loreal|l'oreal|maybelline|mac cosmetics|rimmel|nyx|revolution|glossier|rituals|body shop|lush|molton brown|green people|handmade soap)\b", r"\b(skin (?:in the game|tight)|the simple life|simple (?:pleasures|as))\b")
R("Fashion/Beauty", "Clothing/Footwear", r"\b(fashion|clothing|clothes|outfits?|wardrobe (?:refresh|update|makeover)|dress(?:es)?|coats?|jackets?|jumpers?|cardi(?:gans?)?|hoodies?|sweatshirts?|t-?shirts?|shirts?|jeans|trousers|skirts?|knitwear|cashmere|boots|shoes|footwear|sandals|slippers|loafers|sneakers|pyjamas|pjs|loungewear|lingerie|underwear|bras?|socks|swimwear|bikinis?|swimsuits?|partywear|workwear|uniform|polo|gilets?|parka|trench|blazers?|suits?|menswear|womenswear|kidswear|slipper|ugg|dr\.? martens|converse|vans (?:shoes|trainers)|clarks|vionic|birkenstock|crocs|skechers|hotter|cosyfeet|insoles?|pairs? of (?:shoes|socks|boots|slippers)|freemans|next (?:voucher)?|christmas (?:jumper|cardi))\b", r"\b(suit(?:able| yourself)|shirt(?:less)?|coat of arms|jacket potato|boots (?:chemist)|the boots|dress (?:code|rehearsal))\b")

# ------------------------------------------------------------------ Food / drink
G("food")
R("Food/Drink", "Wine/Spirits/Beer", r"\b(wines?|gin|whisk(?:e)?y|whiskies|vodka|rum|champagne|prosecco|cava|beers?|ales?|lager|cider|cocktails?|spirits?|brandy|cognac|tequila|mezcal|liqueurs?|macallan|glenfiddich|bottles? of (?:wine|gin|whisk(?:e)?y|vodka|rum|champagne|prosecco|beer|cider|spirits?|fizz)|aperitifs?|aperol|non-?alcoholic|sherry|port\b|bourbon|craft beer|brew(?:ery|ing)|sipsmith|hendrick|tanqueray|jack daniel|baileys|pimm|negroni|spritz|wine (?:club|subscription|case|tasting)|case of wine|sake|mead|distill|orchards?|cases? of|drinks (?:cabinet|hamper|bundle|box))\b", r"\b(whisk (?:the|up)|spirit(?:s)? (?:of|world)|spirit of christmas|rum raisin|cider vinegar|alcosense|breathalys|ginger|gingerbread|ginny|drinks trolley|port(?:al|ugal|er|ion))\b")
R("Food/Drink", "Hampers/Food boxes", r"\b(hampers?|food (?:box|boxes|hamper|bundle|parcel|gift)|recipe (?:box|kit)|meal (?:kit|box|plan|delivery|subscription)|gousto|hello ?fresh|mmonths? of (?:meals|food)|graze|veg ?(?:box|etables)|fruit (?:box|basket)|meat (?:box|pack|hamper)|bbq (?:box|pack)|cheese (?:box|hamper|board|selection)|feast|foodie|gourmet|tasting box|treat box|picnic|food (?:and|&) drink|ready meals?|curry (?:kit|box)|indian feast|food shop|grocer(?:y|ies)|pantry|larder|olive oil|honey|spices?|sauces?|pizzas?|pies|pasta|rice|noodles|ketchup|jam|preserves|marmite|heinz|just bee|dairy|butter|cheese|meat|steak|sausages?|bacon|fish|seafood|lobster|vegan (?:box|food)|plant-?based (?:box|food)|bundle of (?:food|snacks)|subscription box)\b", r"\b(cookbooks?|cook books?|recipe books?|diary|dairy diary|books?|vouchers?)\b")
R("Food/Drink", "Snacks/Coffee/Treats", r"\b(chocolates?|choc\b|sweets?|candy|biscuits?|cookies?|oreo|crisps|snacks?|cakes?|bento|cupcakes?|brownies?|doughnuts?|donuts?|ice cream|gelato|popcorn|confectionery|truffles|fudge|toffee|marshmallows?|coffee|tea\b|teas\b|tea (?:bags|box|selection|bundle|subscription)|matcha|hot chocolate|energy drinks?|soft drinks?|smoothies?|fizz|kombucha|protein bars?|cereal|porridge|granola|nuts|treats?|tasty|delicious|bakery|baking|baked|bread|pastry|patisserie|bubble tea|sour sweets?|haribo|cadbury|lindt|hotel chocolat|thorntons|ferrero|nutella|pringles|walkers|doritos|pepsi|coca-?cola|irn-?bru|red bull|prime hydration|oatly|innocent)\b", r"\b(tea (?:break|room|time with)|water (?:filter|dispenser|bottle|park|tap|butt)|water(?:drop|proof|colour)|coffee (?:machine|maker|table|shop voucher)|cake (?:tin)|baking (?:tin))\b")

# ------------------------------------------------------------------ Family / kids
G("instant")
R("Money/Cash", "Instant wins/Prize pools", r"\b(instant ?(?:wins?|prizes?)|guaranteed prizes|prize every time|every time|#\s?\d{1,4}\b|instant wonder|wonder wheel|win(?:ner)? wheel|jammy|penny power|prize pool|make me a winner|lucky dip|mystery (?:box|prize)|auto ?-?win|daily (?:cash )?draw)\b|\bclaw\b.{0,12}\bvolume\b|\b\d{2}\s?/\s?\d{2}\s+split|\bderby\b")
G("cashword")
R("Money/Cash", "Cash lump sum", r"\b(cash|tax[- ]free|prize money|premium bonds?|jackpot)\b", r"\b(cash (?:back|machine|register|and carry)|voucher|tokens?|gift ?cards?|cashmere|cashew|cash-?free)\b")
G("seasonal")
G("advent")
R("Gifts/Bundles", "Advent calendars", r"\badvent\b")
G("seasonal")
R("Gifts/Bundles", "Seasonal bundles", r"\b(halloween|boo ?baskets?|boo box|spook\w*|pumpkin|autumn|winter (?:warm|warmth|wonder|bundle|gift|pamper)|christmas (?:bundle|box|hamper|gift|eve box|goodies|prizes|cheer|giveaway)|xmas|santa|festive|stocking (?:filler|fillers)|easter (?:egg|hamper|bundle|basket)|valentine'?s?|mother'?s day|father'?s day|bonfire|diwali|cosy (?:halloween|autumn|winter)|seasonal)\b")

# ------------------------------------------------------------------ Golf (own category; car models / mini golf excluded)
GOLF_NOT = r"\b(?:vw|volkswagen|new|used|my|the)\s+golf\b(?!\s+(?:break|club|course|day|lesson|round|bag|balls?|resort|holiday|trip))|\bgolf\s+(?:gti|gtd|gte|tdi|tsi|r\b|r-line|estate|mk ?\d|[5-8]\b|alltrack|cabriolet|plus|sv|hatch(?:back)?|match|eHybrid)|\b(?:mini|crazy|adventure|pirate|indoor mini|putt ?putt|swingers)[- ]golf\b|\bgolf (?:car(?:t)? (?:toy|lego))"
GOLF_SIG = r"\bgolf(?:ing|ers?)?\b|\bryder cup\b|\bopen championship\b|\bthe open\b.{0,40}\b(?:royal|st andrews|troon|portrush|birkdale|hoylake|carnoustie|muirfield|lytham|sandwich|golf|championship)\b|\b(?:royal|st andrews|troon|portrush|birkdale|hoylake|carnoustie|muirfield|lytham)\b.{0,30}\bthe open\b|\bpga\b|\bdp world tour\b|\blpga\b|\bsolheim cup\b|\btitleist\b|\bcallaway\b|\btaylor ?made\b|\bsrixon\b|\bwilson staff\b|\bpro ?v1x?\b|\bgreen fees?\b|\btee times?\b|\b(?:ping|cobra|mizuno)\b.{0,25}\b(?:driver|putter|irons?|wedges?|woods?|hybrids?|clubs?)\b|\bfour-?balls?\b"
def _golf(t):
    tt = re.sub(GOLF_NOT, " ", t, flags=re.I)
    if not re.search(GOLF_SIG, tt, re.I): return None
    if re.search(r"\b(tickets?|hospitality|ryder cup|solheim cup|open championship|the open|pga|lpga|dp world tour|pro-?am|masters|championship|spectat\w+|grandstand|tournament)\b", tt, re.I) and not re.search(r"\b(?:pga (?:pro|professional)|lessons?)\b", tt, re.I): return "Golf tickets/events"
    if re.search(r"\b(breaks?|stays?|resorts?|nights?|holidays?|trips?|getaways?|hotels?|lodge|escape|tour (?:to|of)|weekend)\b", tt, re.I): return "Golf trips/breaks"
    if re.search(r"\b(lessons?|coaching|rounds?|green fees?|tee times?|four-?balls?|membership|golf days?|simulator|course|links|tuition|academy|driving range|pga (?:pro|professional)|fitting|experience|golf club\b(?!s)|golf for (?:two|three|four|\d))\b", tt, re.I): return "Golf lessons/rounds"
    return "Golf equipment"

# ------------------------------------------------------------------ rules that need computed sub-categories
VANWORDS = r"\b(campervans?|motorhomes?|caravans?|pick-?ups?|transit|crafter|transporter|vans?|hilux|ranger|navara|l200|amarok|burstner|bürstner|bailey|elddis|auto-?trail|hymer|adria|coachman|knaus|dethleffs|chausson|benimar|autosleeper|horsebox)\b"
def _vehicle(t):
    """Cars / vans: returns sub or None."""
    if re.search(CARNEG, t, re.I): return None
    if re.search(r"\b(stays?|hotel|resort|road trip|loan|hire|rental|nights?)\b", t, re.I) and not re.search(r"\b(or|\+|plus)\s*£|£\s?[\d,]+\s*(?:cash|or)\b|cash alternative", t, re.I): return None
    if re.search(r"\b(holiday park|caravan (?:park|holiday|break|stay)|campervan (?:hire|holiday|trip)|motorhome (?:hire|holiday)|haven|parkdean|butlins)\b", t, re.I): return None
    if re.search(CARBRANDS, t, re.I) or re.search(VANWORDS, t, re.I): return _car_sub(t)
    return None

def _holiday(t):
    if re.search(HOLNEG, t, re.I): return None
    if re.search(HOLW, t, re.I) or re.search(r"\b(break|tour)\b.{0,30}\b(for two|for 2)\b", t, re.I):
        # location-only 'break' words must be a real stay/travel prize
        return _hol_sub(t)
    if re.search(r"\b(" + LONGH[3:-3] + r")\b", t, re.I) and re.search(r"\bwin\b", t, re.I): return "Long-haul"
    return None

def _grp(t, name):
    for g, cat, sub, rx, neg in rules:
        if g == name and rx.search(t) and not (neg and neg.search(t)): return cat, sub
    return None

# evaluation order (specific before generic); ("fn", f) entries compute their own sub-category
ORDER = ["money", ("fn", "golf"), "voucher", "property", "boats", "bikes", ("fn", "vehicle"), "holspecial", ("fn", "holiday"), "tickets", "media",
         "restaurant", "daysout", "advent", "diy", "tech", "home", "sport", "family", "fashion", "food", "instant", "cashword", "seasonal"]

def _match(t):
    if not t: return None
    for g in ORDER:
        if isinstance(g, tuple):
            if g[1] == "golf":
                v = _golf(t)
                if v: return "Golf", v
            elif g[1] == "vehicle":
                v = _vehicle(t)
                if v: return "Cars", v
            else:
                h = _holiday(t)
                if h: return "Holidays/Travel", h
        else:
            r = _grp(t, g)
            if r: return r
    return None

FALLBACK_CASH = _r(r"^\W*(?:free (?:entry|giveaway)\W+)?(?:win\s+)?(?:up to\s+)?£\s?[\d,.]+\s?(?:k|m|million|thousand)?(?:\+|'?s)?(?:\s+(?:cash|tax[- ]free|prize|in prizes|to be won|each|for|on|with|thanks to|from|at|every|a|daily|weekly)\b|[\s]*[(!.\-–:,]|\s*$)|\bcash\b|\btax[- ]free\b|\bmillion\b|\bprize money\b|\bjackpot\b|\bpremium bonds?\b|£\s?[\d,.]+\s?(?:k|m)?\b(?:\s+in\s+prizes|\s+prize)|\bwin (?:up to |over )?£|^\W*\d+k\b")
FALLBACK_INSTANT = _r(r"(instant ?wins?|#\s?\d{1,4}\b|\bwheel\b|jammy|\bclaw\b|derby|\bsplit\b|scratch|lucky dip|mystery (?:box|prize)|golden|penny power|prize pool|prize every time|every time|make me a winner|\bspin\b|\bdraw\b|volume \d+|power ?ball|\bloot\b|\bhaul\b|goals?\b)")
FALLBACK_BUNDLE = _r(r"\b(bundles?|gift ?sets?|gift ?boxes?|gift ?baskets?|baskets?|goody ?bags?|goodies|prize ?packs?|prize ?bundles?|surprise|mystery|packs?|collections?|sets?|packages?|treats|prizes|bag of|box)\b")
HINTS = {"Vehicles": ("Cars", "Everyday cars"), "Bikes": ("Motorbikes", "Motorbikes"), "Watches": ("Fashion/Beauty", "Jewellery/Watches"),
         "Tech": ("Tech/Gadgets", "Other tech"), "Toys": ("Family/Kids", "Toys/Games/Crafts"), "Garden & Outdoors": ("Home/Property", "Garden/Outdoor"),
         "Trade Equipment": ("Home/Property", "DIY/Tools"), "Instant Wins": ("Money/Cash", "Instant wins/Prize pools"), "Cash": ("Money/Cash", "Cash lump sum")}

def classify(title, desc="", hint=""):
    """-> (category, subcategory). Non-UK listings are first glossed into English keywords (gloss.py)."""
    if _util.CUR["cc"] != "uk":
        title, desc = _gloss.english(title), _gloss.english(desc)
    title = (title or "").replace("’", "'").replace("‑", "-")
    r = _match(title)
    if r: return r
    d = (desc or "").replace("’", "'")
    if d and d != title:
        r = _match(d[:300])
        if r: return r
    # source's own category label (e.g. Competition Showroom 'Showroom category: Watches')
    m = re.search(r"Showroom category: ([^.]+)\.", hint or "")
    hv = HINTS.get(m.group(1)) if m else None
    if FALLBACK_INSTANT.search(title) and not re.search(r"\b(win (?:a|an|the|1|one)\s+\w+ ?\w*(draw))\b", title, re.I) and re.search(r"(instant|#\s?\d|wheel|jammy|claw|derby|split|scratch|lucky dip|mystery|golden|penny power|prize pool|every time|make me a winner|volume \d|loot|haul|goals)", title, re.I):
        return "Money/Cash", "Instant wins/Prize pools"
    if hv: return hv
    if FALLBACK_CASH.search(title): return "Money/Cash", "Cash lump sum"
    if FALLBACK_BUNDLE.search(title): return "Gifts/Bundles", "Gift sets/Goody bags"
    return "Other", "Unclear"

def prize_type(category):
    return {"Money/Cash": "cash", "Cars": "asset", "Motorbikes": "asset", "Boats": "asset", "Home/Property": "asset",
            "Holidays/Travel": "holiday", "Tech/Gadgets": "tech"}.get(category, "other")
