"""Run: python -m tests.test_classify   (or pytest)"""
from comptracker.classify import classify, TAXONOMY

CASES = [
 ("Win a Ferrari 488", "Cars", "Supercars/Performance"), ("Win a Bentley Continental GT", "Cars", "Luxury"),
 ("Win a Tesla Model 3", "Cars", "Electric/Hybrid"), ("Win a Nissan Qashqai", "Cars", "Family/SUV"),
 ("Win a 1967 Ford Mustang classic", "Cars", "Classic/Retro"), ("Win a VW California campervan", "Cars", "Vans/Campers"),
 ("Win a Honda CBR600 motorbike", "Motorbikes", "Motorbikes"), ("Win a Vespa scooter", "Motorbikes", "Scooters/Mopeds"),
 ("Win a Trek e-bike", "Motorbikes", "Bicycles/E-bikes"), ("Win a luxury yacht", "Boats", "Yachts/Speedboats"), ("Win a Sea-Doo jet ski", "Boats", "Jet skis"),
 ("Win a trip to Cornwall for two", "Holidays/Travel", "UK breaks"), ("Win a week in Majorca", "Holidays/Travel", "Europe"),
 ("Win a luxury holiday to Dubai", "Holidays/Travel", "Long-haul"), ("Win a Caribbean cruise", "Holidays/Travel", "Cruises"),
 ("Win a Disneyland Paris holiday", "Holidays/Travel", "Theme parks/Disney"), ("Win a spa break for two", "Holidays/Travel", "Spa/Wellness breaks"),
 ("Win £50,000 cash", "Money/Cash", "Cash lump sum"), ("Win £1,000 a month for a year", "Money/Cash", "Monthly/weekly income"),
 ("Win your mortgage paid", "Money/Cash", "Mortgage/Bills paid"), ("Win your dream wedding", "Money/Cash", "Wedding"),
 ("Win an iPhone 17", "Tech/Gadgets", "Phones/Wearables"), ("Win a MacBook Air", "Tech/Gadgets", "Laptops/Tablets"),
 ("Win a PS5", "Tech/Gadgets", "Gaming consoles/PC"), ("Win a Samsung 65 inch TV", "Tech/Gadgets", "TVs/Audio"),
 ("Win a Dyson V15 vacuum", "Tech/Gadgets", "Smart home/Appliances"), ("Win a GoPro", "Tech/Gadgets", "Cameras/Drones"),
 ("Win a £500,000 house in Kent", "Home/Property", "Win a house"), ("Win a garden furniture set", "Home/Property", "Garden/Outdoor"),
 ("Win a Sofa", "Home/Property", "Furniture/Interiors"), ("Win a Smeg kitchen appliance bundle", "Home/Property", "Kitchen"),
 ("Win Taylor Swift concert tickets", "Experiences/Events", "Concert/festival tickets"), ("Win Arsenal v Chelsea tickets", "Experiences/Events", "Sports tickets"),
 ("Win West End theatre tickets", "Experiences/Events", "Theatre/Events"), ("Win a supercar driving experience", "Experiences/Events", "Days out/Driving experiences"),
 ("Win a meet and greet with Ed Sheeran", "Experiences/Events", "Meet & greet/VIP"),
 ("Win a £100 Tesco voucher", "Gift cards/Vouchers", "Supermarket"), ("Win a £100 Amazon gift card", "Gift cards/Vouchers", "Shopping"),
 ("Win a £50 Nando's voucher", "Gift cards/Vouchers", "Restaurants/Takeaway"),
 ("Win a Rolex Submariner", "Fashion/Beauty", "Jewellery/Watches"), ("Win a Louis Vuitton handbag", "Fashion/Beauty", "Handbags/Accessories"),
 ("Win a skincare bundle", "Fashion/Beauty", "Skincare/Makeup"),
 ("Win a luxury food hamper", "Food/Drink", "Hampers/Food boxes"), ("Win a case of champagne", "Food/Drink", "Wine/Spirits/Beer"),
 ("Win dinner for two at The Ivy", "Food/Drink", "Restaurant meals"),
 ("Win a LEGO set", "Family/Kids", "Toys/Games/Crafts"), ("Win a Silver Cross pram", "Family/Kids", "Baby/Nursery"), ("Win a year of dog food", "Family/Kids", "Pets"),
 ("Win a Peloton bike", "Sport/Fitness", "Gym/Fitness"), ("Win a set of golf clubs", "Golf", "Golf equipment"),
 ("Win a golf break for four at Celtic Manor", "Golf", "Golf trips/breaks"), ("Win Ryder Cup tickets", "Golf", "Golf tickets/events"),
 ("Win a fourball at Wentworth", "Golf", "Golf lessons/rounds"), ("Win a TaylorMade Qi35 driver", "Golf", "Golf equipment"),
 ("Win a dozen Titleist Pro V1 balls", "Golf", "Golf equipment"), ("Win a series of golf lessons with a PGA pro", "Golf", "Golf lessons/rounds"),
 ("Win a VW Golf GTI", "Cars", "Supercars/Performance"), ("Win a Volkswagen Golf R", "Cars", "Supercars/Performance"),
 ("Win a 2024 VW Golf Estate", "Cars", None), ("Win a Golf GTI Clubsport + £1,000", "Cars", None),
 ("Win a copy of the new novel", "Books/Music/Film", "Books/Audiobooks"), ("Win a signed vinyl", "Books/Music/Film", "Music/Vinyl"),
 ("Win Toy Story 5 on Blu-ray", "Books/Music/Film", "Films/TV/Blu-ray"),
 ("Win a Christmas advent calendar", "Gifts/Bundles", "Advent calendars"), ("free giveaway", "Other", "Unclear"),
 # regressions: look-alikes that must NOT be misfiled
 ("Win £500 Spend On Oskia Skincare", "Gift cards/Vouchers", "Shopping"), ("Win a Van Cleef & Arpels necklace", "Fashion/Beauty", "Jewellery/Watches"),
 ("Win golf for four at Wynyard Golf Club", "Golf", "Golf lessons/rounds"), ("Win a family crazy golf day out", "NOTGOLF", None), ("Win mini golf tickets for four", "NOTGOLF", None), ("Win a Rolex Yacht-Master", "Fashion/Beauty", "Jewellery/Watches"),
]

def test_taxonomy_is_consistent():
    for cat, subs in TAXONOMY.items():
        assert subs and len(set(subs)) == len(subs), cat

def test_cases():
    def ok(r, c, s):
        if c == "NOTGOLF": return r[0] != "Golf"
        return r[0] == c and (s is None or r[1] == s)
    bad = [(t, classify(t), (c, s)) for t, c, s in CASES if not ok(classify(t), c, s)]
    assert not bad, bad

if __name__ == "__main__":
    test_taxonomy_is_consistent(); test_cases(); print(f"ok: {len(CASES)} cases")
