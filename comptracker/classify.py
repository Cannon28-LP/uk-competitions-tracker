import re

def _r(words):
    return re.compile(r"\b(?:" + "|".join(words) + r")\b", re.I)

CARS = _r(["cars?", "van", "campervan", "camper", "motorhome", "caravan", "suv", "saloon", "estate", "hatchback", "coupe", "convertible", "pick-?up", "truck",
           "audi", "bmw", "mercedes(?:-benz)?", "mercedes", "porsche", "range rover", "land rover", "defender", "ford", "mustang", "fiesta", "focus", "ranger", "transit",
           "volkswagen", "vw", "golf", "tiguan", "transporter", "t6\\.?1", "tesla", "mini cooper", "mini", "lamborghini", "ferrari", "mclaren", "bentley", "rolls-?royce",
           "aston martin", "jaguar", "nissan", "gt-?r", "toyota", "supra", "honda civic", "civic", "skoda", "octavia", "seat", "cupra", "volvo", "lexus", "kia", "hyundai",
           "vauxhall", "corsa", "peugeot", "renault", "citroen", "mazda", "mx-?5", "subaru", "impreza", "evo", "lotus", "alpine", "maserati", "alfa romeo", "jeep", "dodge",
           "chevrolet", "corvette", "cosworth", "escort", "sierra", "m3", "m4", "m5", "rs3", "rs4", "rs5", "rs6", "rsq8", "gt3rs", "a3", "a6", "x3", "x5", "c63", "g63", "amg",
           "kart", "go-?kart", "classic car", "motor ?home", "trailer", "tractor"])
BIKES = _r(["motorbikes?", "motorcycles?", "bikes?", "harley(?:-davidson)?", "ducati", "yamaha", "kawasaki", "ktm", "triumph", "vespa", "scooter", "lambretta", "quad", "mx", "r1", "ninja zx", "cb\\d+", "trials", "dirt bike", "pit bike"])
NOT_MOTO = re.compile(r"\b(bicycles?|e-?bikes?|mountain bike|road bike|cycle|peloton|exercise bike|balance bike|kids? bike)\b", re.I)
BOATS = _r(["boats?", "yacht", "sailing", "kayak", "canoe", "paddle ?board", "jet ?ski", "speedboat", "narrowboat", "rib"])
PROP = _r(["house", "home worth", "cottage", "villa", "apartment", "flat", "bungalow", "property", "barn conversion", "mansion", "bedroom", "bed", "mortgage", "land",
           "sofa", "mattress", "furniture", "garden", "bbq", "hot tub", "patio", "kitchen", "cookware", "hexclad", "dyson", "vacuum", "air fryer", "coffee machine",
           "barista", "sage", "tools?", "milwaukee", "makita", "bosch", "drill", "detailing", "pressure washer", "lawn ?mower", "decorating", "wallpaper", "curtain", "rug",
           "bedding", "duvet", "lighting", "lamp", "home security", "storage", "shed", "greenhouse", "fire ?pit", "appliances?"])
HOLIDAY = _r(["holidays?", "cruise", "break", "getaway", "stay", "hotel", "resort", "villa break", "flights?", "trip", "travel", "weekend away", "spa break", "safari",
              "city break", "ski", "all-inclusive", "all inclusive", "caribbean", "maldives", "dubai", "disney(?:land)?", "center ?parcs", "haven", "butlins", "adventure",
              "tour", "lodge", "glamping", "retreat", "adriatic", "marella", "tui", "jet2", "lisbon", "paris", "new york", "bali", "thailand", "tenerife", "orlando", "florida"])
TECH = _r(["iphone", "ipad", "macbook", "mac mini", "imac", "apple watch", "airpods", "apple", "laptop", "notebook", "tablet", "tv", "oled", "qled", "4k", "smart tv", "monitor",
           "playstation", "ps[345]", "ps5 pro", "xbox", "nintendo", "switch", "steam deck", "steam machine", "console", "gaming", "pc", "gpu", "rtx", "samsung", "galaxy", "pixel",
           "headphones?", "earbuds", "speaker", "soundbar", "sound bar", "jbl", "bose", "sonos", "echo", "alexa", "kindle", "drone", "dji", "gopro", "camera", "canon", "nikon",
           "smart ?watch", "garmin", "fitbit", "oculus", "meta quest", "vr", "robot vacuum", "roomba", "projector", "router", "orbi", "netgear", "electronics?", "gadgets?",
           "tech", "ps5", "controller", "keyboard", "mouse", "hp omen", "msi", "asus", "lenovo", "dell", "e-?reader", "e-?scooter", "e-?bike"])
VOUCHER = _r(["vouchers?", "gift cards?", "gift ?card", "e-?gift", "spending spree", "shopping spree", "to spend", "spend at", "love2shop", "amazon", "tesco", "asda", "sainsbury'?s",
              "waitrose", "morrisons", "aldi", "lidl", "john lewis", "m&s", "marks (?:&|and) spencer", "argos", "currys", "ikea", "next", "boots", "just eat", "deliveroo",
              "uber eats", "netflix", "spotify", "buyagift", "red letter days", "site credit", "credit", "store credit", "dfs"])
EXPERIENCE = _r(["tickets?", "experience", "concert", "festival", "theatre", "theater", "musical", "show", "gig", "vip", "meet (?:&|and) greet", "day out", "afternoon tea",
                 "dining", "dinner for", "restaurant", "premiere", "screening", "cinema", "match tickets", "football", "premier league", "f1", "grand prix", "wicked",
                 "spa day", "spa", "lesson", "course", "class", "driving experience", "track day", "zoo", "theme park", "attraction", "entry to", "membership", "pass", "tour"])
KIDS = _r(["kids?", "child(?:ren)?", "baby", "babies", "toddler", "toys?", "lego", "pushchair", "stroller", "pram", "car seat", "nappies", "nappy", "playhouse", "trampoline", "doll",
           "barbie", "paw patrol", "peppa", "bluey", "pokemon", "pokémon", "disney", "family", "nursery", "school", "mumsnet", "mum", "maternity", "ride-?on", "bike for kids", "playset", "teddy", "plush", "board game", "puzzle", "game bundle"])
FASHION = _r(["fashion", "clothing", "clothes", "outfit", "dress", "shoes?", "trainers?", "boots", "footwear", "sneakers?", "handbag", "bag", "purse", "wallet", "jewel(?:lery|ry)",
              "necklace", "bracelet", "pendant", "ring", "earrings?", "watch", "watches", "rolex", "omega", "moonswatch", "swatch", "tissot", "tag heuer", "seiko", "casio", "chanel",
              "gucci", "louis vuitton", "prada", "dior", "hermes", "diamond", "gold", "silver", "perfume", "fragrance", "skincare", "makeup", "make-?up", "beauty", "cosmetics", "haircare",
              "hair dryer", "ghd", "dyson airwrap", "airwrap", "sunglasses", "ray-?ban", "coat", "jacket", "hoodie", "shirt", "jumper", "cashmere", "lingerie", "swimwear", "nails", "salon"])
FOOD = _r(["food", "drink", "hampers?", "wine", "gin", "whisky", "whiskey", "vodka", "rum", "champagne", "prosecco", "beer", "ale", "cocktails?", "chocolates?", "sweets", "biscuits",
           "cheese", "meat", "meat box", "steak", "bbq box", "butcher", "grocer(?:y|ies)", "supermarket shop", "shopping", "meal", "meals", "pizza", "burgers?", "coffee", "tea",
           "snacks?", "cake", "baking", "treats?", "pet food", "dog food", "graze", "box", "crisps", "pasta", "olive oil", "gourmet", "recipe", "dining", "honest burgers", "heinz"])
CASH = re.compile(r"(\bcash\b|\btax[- ]free\b|£\s?[\d,]+(?:k|m)?\s*(?:\(|$|\)|-|–|/|x\b|\bprize\b|\bto be won\b)|^\W*(?:win\s+)?(?:up to\s+)?£\s?[\d,.]+(?:k|m)?\W*$|\bmillion\b|\binstant wins?\b|\bpremium bonds\b|\bprize money\b|\bjackpot\b)", re.I)

ASSET_CATS = {"Cars", "Motorbikes", "Boats", "Home/Property"}

CATEGORIES = ["Cars", "Motorbikes", "Boats", "Holidays/Travel", "Money/Cash", "Tech/Gadgets", "Home/Property",
              "Experiences/Events", "Gift cards/Vouchers", "Fashion/Beauty", "Food/Drink", "Family/Kids", "Other"]

def classify(title, desc=""):
    t = f"{title or ''} {desc or ''}".strip()
    tl = t.lower()
    # headline prize wins priority: look at title first, then description
    def has(rx, s=t): return bool(rx.search(s))
    ti = title or ""
    # explicit house/property first (houses are assets, also contain "bed"/"home")
    if re.search(r"\b(house|cottage|villa|bungalow|barn conversion|mansion|apartment|flat|bedroom|property)\b", ti, re.I) and not re.search(r"\b(house of|housewarming|white house|treehouse|playhouse|dollhouse)\b", ti, re.I):
        return "Home/Property"
    if has(BOATS, ti): return "Boats"
    # watches/jewellery before cars? only when no car words
    STRONG_CAR = re.compile(r"\b(cars?|van|campervan|camper|motorhome|caravan|suv|saloon|audi|bmw|mercedes|porsche|range rover|land rover|defender|ford|mustang|volkswagen|vw|tiguan|tesla|lamborghini|ferrari|mclaren|bentley|rolls-?royce|aston martin|jaguar|nissan|toyota|honda|skoda|cupra|volvo|lexus|kia|hyundai|vauxhall|peugeot|renault|citroen|mazda|subaru|lotus|maserati|alfa romeo|jeep|dodge|chevrolet|corvette|cosworth|rs[3-6]|rsq8|gt3rs|amg|m[345] (?:competition|touring)|transporter|tractor|trailer|go-?kart)\b", re.I)
    if STRONG_CAR.search(ti) and not re.search(r"\b(toys?|lego|kids?|ride-?on|playset|model|scale|car (?:seat|wash|mat|detailing)|sat ?nav|hot ?wheels)\b", ti, re.I):
        return "Cars"
    if has(BIKES, ti) and not NOT_MOTO.search(ti):
        if not re.search(r"\b(exercise|balance|kids?)\b", ti, re.I):
            return "Motorbikes"
    if re.search(r"\b(cash|£\s?[\d,]+\s*(?:k)?\s*(?:tax[- ]free)?)\b", ti, re.I) and re.search(r"\btax[- ]free cash\b|\bcash prize\b|\bwin £\s?[\d,]+\s*(?:k)?\s*(?:cash|tax free)?\s*$", ti, re.I):
        return "Money/Cash"
    if has(HOLIDAY, ti) and not re.search(r"\b(break ?fast|tea break|stay (?:warm|cool)|fire)\b", ti, re.I) and not re.search(r"\b(boots?)\b", ti, re.I):
        # 'adventure','tour' weak -> only if travel-ish present
        if re.search(r"\b(holidays?|cruise|breaks?|getaway|hotel|resort|flights?|trip|travel|stay|safari|ski|all[- ]inclusive|villa|caribbean|maldives|dubai|center ?parcs|butlins|haven|glamping|retreat|lodge|weekend away|city break|spa break|adriatic|marella|tui|jet2|orlando|florida|bali|thailand|tenerife|lisbon|paris|new york|disney)\b", ti, re.I):
            return "Holidays/Travel"
    if has(VOUCHER, ti) and re.search(r"\b(vouchers?|gift ?cards?|e-?gift|to spend|spend at|spending spree|shopping spree|site credit|credit|buyagift|red letter days|love2shop)\b", ti, re.I):
        return "Gift cards/Vouchers"
    if has(TECH, ti): return "Tech/Gadgets"
    if has(EXPERIENCE, ti) and re.search(r"\b(tickets?|experience|concert|festival|theatre|musical|gig|vip|meet (?:&|and) greet|day out|afternoon tea|dinner for|premiere|screening|spa day|track day|theme park|attraction|membership|premier league|grand prix|f1|wicked|lesson|course)\b", ti, re.I):
        return "Experiences/Events"
    if re.search(r"\b(rolex|omega|watch|watches|tag heuer|tissot|swatch|moonswatch|seiko|cartier|breitling|jewel(?:lery|ry)|necklace|bracelet|pendant|handbag|chanel)\b", ti, re.I):
        return "Fashion/Beauty"
    if CASH.search(ti): return "Money/Cash"
    if has(KIDS, ti): return "Family/Kids"
    if has(FASHION, ti): return "Fashion/Beauty"
    if has(PROP, ti): return "Home/Property"
    if has(FOOD, ti): return "Food/Drink"
    # fall back to description (weaker)
    d = desc or ""
    if d:
        if has(CARS, d) and re.search(r"\b(car|audi|bmw|mercedes|porsche|van)\b", d, re.I): return "Cars"
        if re.search(r"\bcash\b", d, re.I): return "Money/Cash"
        if has(HOLIDAY, d): return "Holidays/Travel"
        if has(TECH, d): return "Tech/Gadgets"
        if has(VOUCHER, d): return "Gift cards/Vouchers"
        if has(FOOD, d): return "Food/Drink"
    return "Other"

def prize_type(category):
    return {"Money/Cash": "cash", "Cars": "asset", "Motorbikes": "asset", "Boats": "asset", "Home/Property": "asset",
            "Holidays/Travel": "holiday", "Tech/Gadgets": "tech"}.get(category, "other")
