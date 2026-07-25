"""
DRISHTI — Karnataka Police Crime Intelligence Platform
Deterministic mock-data generator (stdlib only).

Drops and recreates all 8 tables in the FIR database with 24 months of
realistic Karnataka crime data: seasonal/growing volumes, geographic
hotspots, hour-of-day patterns, gang co-offending networks, repeat
offenders, and two deliberately injected crime spikes (Chain Snatching in
Bengaluru City and Narcotics in Mangaluru over the last 30 days) that the
analytics insight detector is expected to surface.

Run:  python scripts/generate_data.py   (from any CWD)
"""
import csv
import json
import math
import os
import random
import sqlite3
import sys
from datetime import date, datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings  # noqa: E402

rng = random.Random(42)

TODAY = date(2026, 7, 25)

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

DISTRICTS = {
    "Bengaluru City": (12.9716, 77.5946),
    "Mysuru": (12.2958, 76.6394),
    "Mangaluru": (12.9141, 74.8560),
    "Hubballi-Dharwad": (15.3647, 75.1240),
    "Belagavi": (15.8497, 74.4977),
    "Kalaburagi": (17.3297, 76.8343),
    "Ballari": (15.1394, 76.9214),
    "Shivamogga": (13.9299, 75.5681),
    "Tumakuru": (13.3392, 77.1140),
    "Davanagere": (14.4644, 75.9218),
    "Vijayapura": (16.8302, 75.7100),
    "Udupi": (13.3409, 74.7421),
    "Hassan": (13.0068, 76.0996),
    "Ramanagara": (12.7159, 77.2811),
}

DISTRICT_WEIGHTS = {
    "Bengaluru City": 33.0, "Mysuru": 8.0, "Mangaluru": 7.0,
    "Hubballi-Dharwad": 6.5, "Belagavi": 6.0, "Kalaburagi": 5.0,
    "Ballari": 4.5, "Shivamogga": 4.5, "Tumakuru": 4.5, "Davanagere": 4.0,
    "Vijayapura": 4.0, "Udupi": 3.5, "Hassan": 3.5, "Ramanagara": 3.0,
}

STATION_LOCALITIES = {
    "Bengaluru City": ["Cubbon Park", "Koramangala", "Whitefield",
                       "Yeshwanthpur", "Jayanagar", "Indiranagar"],
    "Mysuru": ["Devaraja", "Lashkar", "Kuvempunagar", "Saraswathipuram"],
    "Mangaluru": ["Barke", "Kadri", "Ullal", "Surathkal", "Panambur"],
    "Hubballi-Dharwad": ["Vidyanagar", "Old Hubballi", "Dharwad Town", "Gokul Road"],
    "Belagavi": ["Camp", "Tilakwadi", "Shahapur", "Khade Bazar"],
    "Kalaburagi": ["Station Bazar", "Brahmpur", "Chowk", "MSK Mill"],
    "Ballari": ["Cowl Bazar", "Bruce Pete", "Toranagallu", "Kampli Road"],
    "Shivamogga": ["Doddapete", "Vinoba Nagar", "Kote", "Tilak Nagar"],
    "Tumakuru": ["Tumakuru Town", "Kyathsandra", "Antharasanahalli", "Sira Gate"],
    "Davanagere": ["KTJ Nagar", "Azad Nagar", "Nittuvalli", "Bethur Road"],
    "Vijayapura": ["Gandhi Chowk", "Adarsh Nagar", "Jorapur Peth", "Station Road"],
    "Udupi": ["Malpe", "Manipal", "Kaup", "Udupi Town"],
    "Hassan": ["Hassan Town", "Pension Mohalla", "Salagame Road"],
    "Ramanagara": ["Ramanagara Town", "Channapatna", "Bidadi", "Kanakapura Road"],
}

MAJOR_HEADS = {
    "Property Crimes": 27.0,
    "Crimes Against Body": 18.0,
    "Cyber Crimes": 15.0,
    "Crimes Against Women": 12.0,
    "Narcotics": 8.0,
    "Economic Offences": 8.0,
    "Road Incidents": 7.0,
    "Public Order": 5.0,
}

MINOR_HEADS = {
    "Property Crimes": [("Chain Snatching", 28), ("House Burglary", 22),
                        ("Vehicle Theft", 22), ("Mobile Phone Theft", 18),
                        ("Robbery", 10)],
    "Crimes Against Body": [("Assault", 55), ("Attempt to Murder", 13),
                            ("Murder", 12), ("Kidnapping", 20)],
    "Cyber Crimes": [("OTP Fraud", 35), ("Investment Scam", 30),
                     ("Identity Theft", 15), ("Social Media Harassment", 20)],
    "Crimes Against Women": [("Domestic Cruelty", 45), ("Harassment", 33),
                             ("Stalking", 22)],
    "Narcotics": [("Ganja Possession", 60), ("Synthetic Drugs Peddling", 40)],
    "Economic Offences": [("Cheating", 50), ("Ponzi Scheme", 22), ("Bank Fraud", 28)],
    "Road Incidents": [("Hit and Run", 45), ("Rash Driving", 55)],
    "Public Order": [("Rioting", 55), ("Unlawful Assembly", 45)],
}

MINOR_TO_MAJOR = {m: maj for maj, lst in MINOR_HEADS.items() for m, _ in lst}

# section_number, description, act_name, act_short_name
IPC_SECTIONS = [
    ("302", "Murder", "Indian Penal Code", "IPC"),
    ("307", "Attempt to murder", "Indian Penal Code", "IPC"),
    ("304B", "Dowry death", "Indian Penal Code", "IPC"),
    ("323", "Voluntarily causing hurt", "Indian Penal Code", "IPC"),
    ("324", "Voluntarily causing hurt by dangerous weapons", "Indian Penal Code", "IPC"),
    ("354", "Assault on woman with intent to outrage modesty", "Indian Penal Code", "IPC"),
    ("354D", "Stalking", "Indian Penal Code", "IPC"),
    ("363", "Kidnapping", "Indian Penal Code", "IPC"),
    ("376", "Rape", "Indian Penal Code", "IPC"),
    ("379", "Theft", "Indian Penal Code", "IPC"),
    ("380", "Theft in dwelling house", "Indian Penal Code", "IPC"),
    ("392", "Robbery", "Indian Penal Code", "IPC"),
    ("397", "Robbery with attempt to cause death or grievous hurt", "Indian Penal Code", "IPC"),
    ("406", "Criminal breach of trust", "Indian Penal Code", "IPC"),
    ("409", "Criminal breach of trust by public servant or banker", "Indian Penal Code", "IPC"),
    ("420", "Cheating and dishonestly inducing delivery of property", "Indian Penal Code", "IPC"),
    ("454", "Lurking house-trespass in order to commit offence", "Indian Penal Code", "IPC"),
    ("457", "Lurking house-trespass by night", "Indian Penal Code", "IPC"),
    ("498A", "Cruelty by husband or relatives of husband", "Indian Penal Code", "IPC"),
    ("504", "Intentional insult with intent to provoke breach of peace", "Indian Penal Code", "IPC"),
    ("506", "Criminal intimidation", "Indian Penal Code", "IPC"),
    ("143", "Unlawful assembly", "Indian Penal Code", "IPC"),
    ("147", "Rioting", "Indian Penal Code", "IPC"),
    ("279", "Rash driving on a public way", "Indian Penal Code", "IPC"),
    ("304A", "Causing death by negligence", "Indian Penal Code", "IPC"),
    ("66C", "Identity theft", "Information Technology Act", "IT Act"),
    ("66D", "Cheating by personation using computer resource", "Information Technology Act", "IT Act"),
    ("20", "Contravention in relation to cannabis", "Narcotic Drugs and Psychotropic Substances Act", "NDPS Act"),
    ("22", "Contravention in relation to psychotropic substances", "Narcotic Drugs and Psychotropic Substances Act", "NDPS Act"),
]

# minor head -> (always sections, optional sections)
IPC_MAP_RULES = {
    "Chain Snatching": (["379"], ["392", "506"]),
    "House Burglary": (["457", "380"], ["454"]),
    "Vehicle Theft": (["379"], []),
    "Mobile Phone Theft": (["379"], []),
    "Robbery": (["392"], ["397", "506"]),
    "Assault": (["323"], ["324", "504", "506"]),
    "Murder": (["302"], ["506"]),
    "Attempt to Murder": (["307"], ["324", "506"]),
    "Kidnapping": (["363"], ["506"]),
    "OTP Fraud": (["420", "66D"], ["66C"]),
    "Investment Scam": (["420"], ["406", "66D"]),
    "Identity Theft": (["66C"], ["420"]),
    "Social Media Harassment": (["66C"], ["504", "506"]),
    "Domestic Cruelty": (["498A"], ["504", "506"]),
    "Harassment": (["354"], ["504", "506"]),
    "Stalking": (["354D"], ["506"]),
    "Ganja Possession": (["20"], []),
    "Synthetic Drugs Peddling": (["22"], []),
    "Cheating": (["420"], ["406"]),
    "Ponzi Scheme": (["420", "406"], ["409"]),
    "Bank Fraud": (["420"], ["409", "66D"]),
    "Hit and Run": (["279"], ["304A"]),
    "Rash Driving": (["279"], []),
    "Rioting": (["147"], ["143", "323"]),
    "Unlawful Assembly": (["143"], ["506"]),
}

MALE_FIRST = [
    "Ramesh", "Suresh", "Mahesh", "Ganesh", "Prakash", "Santhosh", "Manjunath",
    "Nagaraj", "Shivakumar", "Ravi", "Kiran", "Harish", "Girish", "Lokesh",
    "Umesh", "Venkatesh", "Srinivas", "Raghavendra", "Anand", "Arun", "Vinod",
    "Sunil", "Anil", "Praveen", "Naveen", "Pavan", "Chetan", "Darshan",
    "Karthik", "Vijay", "Ajay", "Sanjay", "Mohan", "Krishna", "Gopal",
    "Basavaraj", "Siddaraju", "Hanumantha", "Chandru", "Puneeth", "Yash",
    "Abhishek", "Rakesh", "Dinesh", "Rajesh", "Satish", "Jagadish", "Shankar",
    "Murali", "Madhu", "Sudeep", "Vikram", "Bharath", "Nithin", "Rohan",
    "Imran", "Irfan", "Salman", "Abdul", "Syed", "Farhan", "Riyaz", "Mustafa",
    "Peter", "Joseph", "Thomas", "Wilson", "Charan", "Gagan", "Sagar",
]
FEMALE_FIRST = [
    "Lakshmi", "Saraswathi", "Parvathi", "Gowri", "Shobha", "Radha", "Geetha",
    "Seetha", "Savitha", "Kavitha", "Sunitha", "Anitha", "Vanitha", "Latha",
    "Hema", "Rekha", "Usha", "Asha", "Nisha", "Divya", "Priya", "Shruthi",
    "Swathi", "Deepa", "Pooja", "Ramya", "Soumya", "Navya", "Bhavya",
    "Chaitra", "Meghana", "Rashmi", "Shilpa", "Shwetha", "Pallavi", "Vidya",
    "Sandhya", "Suma", "Uma", "Manjula", "Sharada", "Yashoda", "Ambika",
    "Bhagya", "Nandini", "Spandana", "Ayesha", "Fathima", "Salma", "Mary",
]
LAST_NAMES = [
    "Gowda", "Reddy", "Rao", "Shetty", "Hegde", "Kulkarni", "Deshpande",
    "Joshi", "Kamath", "Pai", "Nayak", "Naik", "Bhat", "Acharya", "Murthy",
    "Sharma", "Patil", "Jadhav", "Chavan", "Pawar", "Shinde", "Kattimani",
    "Biradar", "Angadi", "Hiremath", "Kumar", "Swamy", "Poojary", "Suvarna",
    "Salian", "Kotian", "Ballal", "Alva", "Rai", "Adiga", "Udupa", "Karanth",
    "Kini", "Prabhu", "Bangera", "Amin", "Khan", "Sheikh", "Pasha", "Baig",
    "Sait", "DSouza", "Fernandes", "Pinto", "Lobo", "Sequeira", "Iyer",
    "Iyengar", "Achar", "Devadiga", "Moily", "Puthran", "Shanbhag", "Kamat",
    "Madiwal",
]
OCCUPATIONS = [
    "Software Engineer", "Teacher", "Shop Owner", "Auto Driver", "Farmer",
    "Homemaker", "Student", "Bank Employee", "Daily Wage Worker", "Nurse",
    "Businessman", "Tailor", "Security Guard", "Retired Govt Servant",
    "Hotel Worker",
]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
RANKS = ["PSI", "SI", "ASI", "Inspector", "DySP"]
RANK_WEIGHTS = [30, 25, 22, 15, 8]

BIKES = ["black Pulsar motorcycle", "red Splendor motorcycle",
         "blue Activa scooter", "grey KTM motorcycle", "black Apache motorcycle"]
VEHICLES = ["white van", "silver Swift car", "black Scorpio SUV",
            "grey Bolero pickup", "white Innova car"]
LANDMARKS = ["the bus stop", "the market road", "the park entrance",
             "the temple street", "the main road junction", "the metro station",
             "the vegetable market", "the college gate"]

# ---------------------------------------------------------------------------
# Brief-facts templates (feed the FAISS semantic-search demo)
# ---------------------------------------------------------------------------

def _amount(lo, hi):
    v = rng.randint(lo, hi)
    v = int(round(v, -3))
    s = f"{v:,}".replace(",", ",")
    return f"Rs. {s}"


def make_brief_facts(minor, loc, loc2, d, hour):
    ds = d.strftime("%d/%m/%Y")
    ampm = "AM" if hour < 12 else "PM"
    h12 = hour % 12 or 12
    t = f"around {h12}:{rng.choice(['00', '15', '30', '45'])} {ampm}"
    bike = rng.choice(BIKES)
    veh = rng.choice(VEHICLES)
    lm = rng.choice(LANDMARKS)
    grams = rng.randint(15, 60)

    T = {
        "Chain Snatching": [
            f"On {ds} {t}, the complainant was walking near {lm} in {loc} when two unidentified men on a {bike} approached from behind and snatched her gold chain of {grams} grams worth {_amount(40000, 260000)}. The riders sped away towards {loc2} before anyone could note the registration number.",
            f"The complainant, a resident of {loc}, reported that while returning from the market {t} on {ds}, the pillion rider of a {bike} without number plates snatched her mangalsutra valued at {_amount(50000, 200000)}. She sustained minor abrasions on the neck. CCTV footage of nearby shops is being collected.",
            f"On {ds} {t}, an elderly woman on her morning walk near {lm}, {loc} was targeted by a chain snatcher on a {bike} who fled towards the {loc2} ring road with her gold chain worth {_amount(35000, 150000)}. Two similar incidents were reported in the same beat during the fortnight.",
        ],
        "House Burglary": [
            f"On the night of {ds}, unknown persons broke the rear door lock of the complainant's residence in {loc} and committed theft of gold ornaments and cash totalling {_amount(150000, 900000)} while the family was away at their native place. Neighbours reported a {veh} parked near the gate {t}.",
            f"Between the night of {ds} and the following morning, burglars gained entry into a locked house at {loc} by cutting the window grill and decamped with valuables worth {_amount(100000, 600000)}. Fingerprints were lifted from the almirah and a dog squad was pressed into service.",
            f"The complainant reported that when the family returned to their house in {loc} on {ds}, the main door latch was found broken and gold jewellery, a laptop and cash amounting to {_amount(80000, 500000)} were missing. Entry appears to have been made {t} through the terrace door.",
        ],
        "Vehicle Theft": [
            f"The complainant parked his {bike} in front of his residence in {loc} on the night of {ds}. When he came out {t} the next morning the vehicle was missing along with its documents kept in the boot. The vehicle is valued at {_amount(45000, 120000)}.",
            f"On {ds}, a {veh} parked near {lm} in {loc} was stolen by unknown persons {t}. CCTV footage shows two men tampering with the door lock before driving away towards {loc2}. The vehicle bears a Karnataka registration.",
            f"The complainant reported theft of his {bike} from the paid parking lot near the {loc} railway station on {ds} {t}. The parking attendant noticed nothing unusual. The vehicle was purchased six months ago for {_amount(60000, 110000)}.",
        ],
        "Mobile Phone Theft": [
            f"On {ds} {t}, the complainant's mobile phone worth {_amount(15000, 90000)} was stolen from his pocket while boarding a crowded bus near {lm} in {loc}. The IMEI number has been noted for tracking.",
            f"The complainant reported that while shopping at the {loc} market on {ds} {t}, an unknown person snatched her mobile phone worth {_amount(12000, 70000)} and disappeared into the crowd towards {loc2}.",
        ],
        "Robbery": [
            f"On {ds} {t}, three unknown persons armed with knives waylaid the complainant near {lm} in {loc} and robbed him of cash {_amount(8000, 90000)}, a gold ring and his mobile phone. The accused threatened him with dire consequences before escaping on a {bike}.",
            f"The complainant, a petrol bunk employee at {loc}, reported that {t} on {ds} two masked men brandishing a machete robbed the day's collection of {_amount(30000, 150000)} and fled in a {veh} towards {loc2}. One of the accused appeared to know the cash-handover routine.",
        ],
        "Assault": [
            f"On {ds} {t}, following a dispute over parking near {lm} in {loc}, the accused abused the complainant in filthy language and assaulted him with fists and a wooden stick, causing injuries to his head and arm. The injured was shifted to the government hospital.",
            f"The complainant reported that on {ds} {t} his neighbour in {loc}, along with two associates, assaulted him over a long-standing civil dispute regarding a shared compound wall. He sustained a fracture to his left hand and has submitted a wound certificate.",
        ],
        "Murder": [
            f"On {ds}, the body of a male aged about {rng.randint(24, 55)} years was found near {lm} in {loc} with multiple stab injuries. Preliminary investigation suggests the deceased was done to death {t} the previous night over a financial dispute. The scene was secured and forensic teams collected evidence.",
            f"The complainant reported that his brother was fatally attacked with machetes by known assailants near {loc} {t} on {ds} following a previous enmity over a land dealing in {loc2}. He was declared dead at the district hospital. Special teams have been formed to trace the accused.",
        ],
        "Attempt to Murder": [
            f"On {ds} {t}, the accused, harbouring a grudge over an old rivalry, attacked the complainant with a machete near {lm} in {loc}, inflicting deep cut injuries on his shoulder and forearm. Passers-by rushed the injured to hospital where his condition is stated to be stable.",
            f"The complainant stated that on {ds} {t}, two persons on a {bike} intercepted him near {loc} and one of them stabbed him in the abdomen intending to kill him over a money-lending dispute. Doctors have opined the injury as grievous and life-threatening.",
        ],
        "Kidnapping": [
            f"The complainant reported that his {rng.randint(14, 17)}-year-old daughter left home in {loc} for tuition on {ds} {t} and did not return. Investigation revealed she was last seen near {lm} boarding a {veh}. A kidnapping case has been registered and special teams dispatched.",
            f"On {ds} {t}, the complainant's son was forcibly taken into a {veh} by three unknown persons near {loc}. A ransom call demanding {_amount(500000, 2000000)} was received the same evening from an unregistered number. Technical teams are tracing the call.",
        ],
        "OTP Fraud": [
            f"On {ds} {t}, the complainant, a resident of {loc}, received a call from a person posing as a bank officer who claimed his debit card would be blocked. On sharing the OTP, {_amount(25000, 400000)} was fraudulently debited from his savings account in three transactions. The cyber cell has written to the bank to freeze the beneficiary account.",
            f"The complainant reported that on {ds} she received an SMS about a pending electricity bill with a link. After entering card details and the OTP on the fake page, {_amount(15000, 250000)} was siphoned from her account. The money trail leads to a wallet registered in another state.",
        ],
        "Investment Scam": [
            f"The complainant of {loc} was added to a trading group on a messaging app in which fraudsters promised {rng.randint(20, 45)}% monthly returns on stock investments. Between {ds} and the following weeks he transferred {_amount(200000, 2500000)} to various UPI IDs. When he attempted to withdraw, the app was disabled and the group deleted.",
            f"On {ds}, the complainant reported that an online acquaintance induced her to invest in a fake cryptocurrency platform showing fabricated profits. She invested {_amount(150000, 1200000)} in tranches from her account in {loc}. The platform domain was registered abroad and has since gone offline.",
        ],
        "Identity Theft": [
            f"The complainant of {loc} reported on {ds} that an unknown person obtained a duplicate SIM of his mobile number and operated his bank and UPI accounts, transferring {_amount(40000, 300000)}. His identity documents appear to have been misused for the SIM swap.",
            f"On {ds}, the complainant found that a loan of {_amount(100000, 500000)} had been availed in his name using forged Aadhaar and PAN details. He resides in {loc} and has never applied for the said loan. The NBFC records show an unknown address in {loc2}.",
        ],
        "Social Media Harassment": [
            f"The complainant, a college student from {loc}, reported on {ds} that an unknown person created a fake profile in her name using her photographs and sent obscene messages to her contacts. The profile was created {t} and continues to be active despite reporting.",
            f"On {ds}, the complainant reported that morphed photographs of her were being circulated on social media by an account demanding money to take them down. She resides in {loc} and suspects a former colleague. Preservation requests have been sent to the platform.",
        ],
        "Domestic Cruelty": [
            f"The complainant, married for {rng.randint(2, 12)} years and residing at {loc}, reported that her husband and in-laws subjected her to physical and mental cruelty demanding additional dowry of {_amount(200000, 1000000)}. On {ds} {t} she was assaulted and driven out of the matrimonial home.",
            f"On {ds}, the complainant of {loc} stated that her husband, addicted to alcohol, has been beating her frequently and taunting her over dowry. The previous night {t} he assaulted her with a belt in front of the children. Medical examination was conducted at the district hospital.",
        ],
        "Harassment": [
            f"The complainant reported that on {ds} {t}, while waiting near {lm} in {loc}, the accused passed lewd remarks and attempted to grab her hand despite her protests. Onlookers intervened and the accused fled towards {loc2}.",
            f"On {ds}, the complainant, employed at a private firm in {loc}, reported persistent harassment by a co-worker who follows her {t} and makes unwelcome advances despite repeated warnings from the management.",
        ],
        "Stalking": [
            f"The complainant of {loc} reported that the accused has been following her daily from her office to her residence since the past month, waiting near {lm} {t} and repeatedly calling from different numbers. On {ds} he threatened her when she confronted him.",
            f"On {ds}, the complainant, a student of {loc} college, reported that the accused loiters near her house {t}, monitors her movements and has sent over {rng.randint(40, 300)} messages from multiple accounts despite being blocked.",
        ],
        "Ganja Possession": [
            f"On {ds} {t}, on credible information, the police intercepted a person near {lm} in {loc} and on search found {rng.randint(2, 18)} kg of ganja concealed in a gunny bag intended for sale to local youth. The contraband was seized under a mahazar and the accused was arrested on the spot.",
            f"Acting on a tip-off, a raid was conducted on {ds} {t} at a rented room in {loc} where {rng.randint(1, 8)} kg of ganja packed in small pouches was recovered along with cash of {_amount(15000, 90000)}. The accused was peddling near the {loc2} college campus.",
        ],
        "Synthetic Drugs Peddling": [
            f"On {ds} {t}, a special team laid a trap near {lm} in {loc} and apprehended a peddler with {rng.randint(20, 120)} MDMA pills and {rng.randint(10, 60)} grams of hydro ganja meant for circulation at parties. Mobile phones recovered indicate contacts with an inter-state supplier.",
            f"On credible information, police intercepted a {bike} near {loc} on {ds} {t} and seized LSD strips and MDMA crystals worth {_amount(150000, 900000)} from the rider. The accused was supplying synthetic drugs to students around {loc2}. Forward and backward linkages are being investigated.",
        ],
        "Cheating": [
            f"The complainant of {loc} reported that the accused took an advance of {_amount(100000, 900000)} on {ds} promising to supply construction material, but neither supplied the goods nor returned the amount and is now evading calls. The accused issued a cheque which was dishonoured.",
            f"On {ds}, the complainant stated that the accused induced him to pay {_amount(200000, 1500000)} towards booking a site at {loc2}, showing forged layout approval documents. On verification with the authority the layout was found to be unapproved. The accused's office in {loc} is closed.",
        ],
        "Ponzi Scheme": [
            f"Several depositors of {loc} reported that a chit-fund company collected deposits promising {rng.randint(14, 30)}% annual interest and doubled-money schemes. On {ds} the office was found locked and the promoters absconding with public deposits estimated at {_amount(5000000, 40000000)}.",
            f"The complainant reported on {ds} that he and {rng.randint(8, 60)} others of {loc} invested in a multi-level marketing scheme which promised commissions for enrolling members. The scheme collapsed and the promoter stopped payments, cheating investors of about {_amount(2000000, 15000000)}.",
        ],
        "Bank Fraud": [
            f"The branch manager of a nationalised bank at {loc} reported on {ds} that an account holder, in collusion with an insider, discounted forged cheques and siphoned {_amount(500000, 8000000)} across multiple transactions {t}. Internal audit flagged the irregularity.",
            f"On {ds}, the complainant bank at {loc} reported that a borrower availed a gold loan of {_amount(300000, 2000000)} by pledging spurious gold ornaments. The fraud came to light during the annual verification of pledged articles.",
        ],
        "Hit and Run": [
            f"On {ds} {t}, an unknown {veh} moving at high speed knocked down a pedestrian crossing the road near {lm} in {loc} and sped away without stopping. The injured was shifted to hospital by passers-by and is critical. CCTV cameras along the stretch are being examined.",
            f"The complainant reported that on {ds} {t} his father, a morning walker, was hit by an unidentified {bike} near {loc} which fled the scene. He succumbed to head injuries at the hospital. Vehicle fragments found at the spot have been sent for examination.",
        ],
        "Rash Driving": [
            f"On {ds} {t}, the accused drove a {veh} in a rash and negligent manner near {lm} in {loc}, endangering pedestrians and colliding with a parked {bike}. The vehicle was seized and the driver subjected to a medical test.",
            f"Patrol staff noticed a {bike} being ridden {t} on {ds} in a zig-zag manner at high speed near {loc}, performing wheelies amid traffic. The rider, without a valid licence, was intercepted after a short chase near {loc2}.",
        ],
        "Rioting": [
            f"On {ds} {t}, two groups clashed near {lm} in {loc} over an old rivalry, pelting stones and damaging {rng.randint(2, 8)} vehicles and shop fronts. Police resorted to mild force to disperse the mob and additional forces were deployed in the area.",
            f"Following a dispute during a local procession on {ds} {t}, members of two communities gathered at {loc} armed with sticks and stones and indulged in rioting, injuring {rng.randint(2, 9)} persons including a police constable. Prohibitory orders were promulgated.",
        ],
        "Unlawful Assembly": [
            f"On {ds} {t}, about {rng.randint(30, 200)} persons assembled unlawfully near {lm} in {loc} in violation of prohibitory orders, blocking the highway and raising slogans over a civic issue. The assembly was dispersed and ringleaders were identified from video footage.",
            f"Despite prohibitory orders in force, a mob gathered {t} on {ds} in front of the {loc} government office demanding action on a local dispute, obstructing public servants from discharging duty. The crowd dispersed after police intervention.",
        ],
    }
    return rng.choice(T[minor])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def db_path_from_settings():
    url = settings.DATABASE_URL
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if url.startswith(prefix):
            p = url[len(prefix):]
            if not os.path.isabs(p):
                backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                p = os.path.join(backend_dir, p)
            return os.path.abspath(p)
    raise ValueError(f"Unsupported DATABASE_URL: {url}")


def station_code(name, used):
    base = name.replace(" PS", "").upper()
    letters = [c for c in base if c.isalpha()]
    cons = [letters[0]] + [c for c in letters[1:] if c not in "AEIOU"]
    code = "".join(cons)[:4]
    if len(code) < 4:
        code = (code + "".join(letters))[:4]
    code = code.ljust(4, "X")
    i = 2
    while code in used:
        code = code[:3] + str(i)
        i += 1
    used.add(code)
    return code


def month_back(anchor, k):
    """(year, month) k months before anchor's month."""
    y = anchor.year + (anchor.month - 1 - k) // 12
    m = (anchor.month - 1 - k) % 12 + 1
    return y, m


def days_in_month(y, m):
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return (nxt - timedelta(days=1)).day


def pick_hour(minor, major):
    if minor in ("House Burglary", "Vehicle Theft"):
        pool = [(h, 6.0) for h in (23, 0, 1, 2, 3, 4)] + \
               [(h, 0.5) for h in range(24) if h not in (23, 0, 1, 2, 3, 4)]
    elif minor == "Chain Snatching":
        pool = [(h, 5.0) for h in (6, 7, 8, 9, 10, 18, 19, 20, 21)] + \
               [(h, 0.5) for h in range(24) if h not in (6, 7, 8, 9, 10, 18, 19, 20, 21)]
    elif major == "Cyber Crimes":
        pool = [(h, 4.0) for h in range(10, 23)] + \
               [(h, 0.5) for h in range(24) if not 10 <= h <= 22]
    elif major == "Road Incidents":
        pool = [(h, 5.0) for h in (18, 19, 20, 21, 22, 23)] + \
               [(h, 2.0) for h in (7, 8, 9, 10)] + \
               [(h, 0.7) for h in range(24) if h not in (18, 19, 20, 21, 22, 23, 7, 8, 9, 10)]
    else:
        pool = [(h, 4.0) for h in range(8, 20)] + \
               [(h, 0.8) for h in range(24) if not 8 <= h <= 19]
    hours, weights = zip(*pool)
    return rng.choices(hours, weights=weights)[0]


def person_name(gender):
    first = rng.choice(MALE_FIRST if gender == "Male" else FEMALE_FIRST)
    return f"{first} {rng.choice(LAST_NAMES)}"


# ---------------------------------------------------------------------------
# Build stations & officers
# ---------------------------------------------------------------------------

stations = []          # dicts; rowid = index+1
district_stations = {}  # district -> [station index]
used_codes = set()
for dist, (dlat, dlon) in DISTRICTS.items():
    idxs = []
    for loc in STATION_LOCALITIES[dist]:
        name = f"{loc} PS"
        st = {
            "station_name": name,
            "district": dist,
            "latitude": round(dlat + rng.uniform(-0.06, 0.06), 6),
            "longitude": round(dlon + rng.uniform(-0.06, 0.06), 6),
            "unit_type": "Law & Order",
            "state": "Karnataka",
            "code": station_code(name, used_codes),
            "locality": loc,
        }
        idxs.append(len(stations))
        stations.append(st)
    district_stations[dist] = idxs

officers = []           # dicts; station_rowid = station index+1
station_officers = {}   # station index -> [officer names]
for si, st in enumerate(stations):
    n_off = rng.randint(4, 8)
    names = []
    for _ in range(n_off):
        g = "Female" if rng.random() < 0.22 else "Male"
        nm = person_name(g)
        rank = rng.choices(RANKS, weights=RANK_WEIGHTS)[0]
        dob_year = rng.randint(1972, 1998)
        dob = date(dob_year, rng.randint(1, 12), rng.randint(1, 28))
        appt = dob + timedelta(days=365 * rng.randint(22, 30) + rng.randint(0, 300))
        designation = "Station House Officer" if rank == "Inspector" else (
            "Sub-Division Officer" if rank == "DySP" else "Investigating Officer")
        officers.append({
            "name": f"{rank} {nm}",
            "rank": rank,
            "station_rowid": si + 1,
            "designation": designation,
            "kgid": str(rng.randint(1000000, 2999999)),
            "dob": dob.isoformat(),
            "gender": g,
            "blood_group": rng.choice(BLOOD_GROUPS),
            "is_physically_challenged": 1 if rng.random() < 0.03 else 0,
            "appointment_date": appt.isoformat(),
        })
        names.append(f"{rank} {nm}")
    station_officers[si] = names

# Hotspot sub-centers per district (2-3, Bengaluru gets 3)
hotspots = {}
for dist, (dlat, dlon) in DISTRICTS.items():
    n = 3 if dist == "Bengaluru City" else rng.randint(2, 3)
    hotspots[dist] = [(dlat + rng.uniform(-0.05, 0.05), dlon + rng.uniform(-0.05, 0.05))
                      for _ in range(n)]

# ---------------------------------------------------------------------------
# Phase A: FIR skeletons (district, major, minor, incident date)
# ---------------------------------------------------------------------------

dist_names = list(DISTRICT_WEIGHTS)
dist_w = list(DISTRICT_WEIGHTS.values())

skeletons = []
for m_idx in range(24):
    y, mo = month_back(TODAY, 23 - m_idx)
    dim = days_in_month(y, mo)
    last_day = TODAY.day if (y, mo) == (TODAY.year, TODAY.month) else dim
    growth = 1.0 + 0.28 * (m_idx / 23.0)
    season = 1.0 + 0.10 * math.sin(2 * math.pi * (mo - 4) / 12.0)
    monthly_total = int(round(88 * growth * season * (last_day / dim)))

    # Cyber share grows over the 24 months (~8% -> ~22%)
    cyber_scale = 0.55 + 0.90 * (m_idx / 23.0)
    for _ in range(monthly_total):
        dist = rng.choices(dist_names, weights=dist_w)[0]
        majors, weights = [], []
        for maj, w in MAJOR_HEADS.items():
            if maj == "Cyber Crimes":
                w = w * cyber_scale
            if maj == "Narcotics" and dist == "Mangaluru":
                w = w * 2.5   # coastal drug-route baseline
            majors.append(maj)
            weights.append(w)
        major = rng.choices(majors, weights=weights)[0]
        minors, mw = zip(*MINOR_HEADS[major])
        minor = rng.choices(minors, weights=mw)[0]
        day = rng.randint(1, last_day)
        skeletons.append({"district": dist, "major": major, "minor": minor,
                          "date": date(y, mo, day)})

# ---------------------------------------------------------------------------
# Phase A2: inject demo spikes in the last 30 days
# ---------------------------------------------------------------------------

def _count(dist, minor, d_from, d_to):
    return sum(1 for s in skeletons
               if s["district"] == dist and s["minor"] == minor
               and d_from <= s["date"] <= d_to)


last30_from = TODAY - timedelta(days=29)
prior_from, prior_to = TODAY - timedelta(days=119), TODAY - timedelta(days=30)


def inject_spike(dist, minor, mult, floor):
    existing = _count(dist, minor, last30_from, TODAY)
    baseline = _count(dist, minor, prior_from, prior_to) / 3.0
    target = max(int(round(mult * baseline)), floor)
    for _ in range(max(0, target - existing)):
        d = TODAY - timedelta(days=rng.randint(2, 27))
        skeletons.append({"district": dist, "minor": minor,
                          "major": MINOR_TO_MAJOR[minor], "date": d})
    return existing, baseline, target


sp1 = inject_spike("Bengaluru City", "Chain Snatching", 3.0, 14)
sp2 = inject_spike("Mangaluru", "Synthetic Drugs Peddling", 2.5, 8)
sp3 = inject_spike("Mangaluru", "Ganja Possession", 2.5, 7)

skeletons.sort(key=lambda s: s["date"])

# ---------------------------------------------------------------------------
# Phase B: gangs (co-offending networks)
# ---------------------------------------------------------------------------

person_seq = [0]


def new_person(gender=None, age_lo=19, age_hi=48):
    person_seq[0] += 1
    g = gender or ("Female" if rng.random() < 0.12 else "Male")
    return {
        "person_id": f"P-{person_seq[0]:04d}",
        "name": person_name(g),
        "gender": g,
        "base_age": rng.randint(age_lo, age_hi),
        "base_year": TODAY.year - 2,
    }


GANG_SPECS = [
    ("Chain Snatching", ["Bengaluru City", "Ramanagara"]),
    ("Vehicle Theft", ["Bengaluru City", "Tumakuru"]),
    ("House Burglary", ["Mysuru", "Hassan"]),
    ("Synthetic Drugs Peddling", ["Mangaluru", "Udupi"]),
    ("OTP Fraud", ["Bengaluru City"]),
    ("Robbery", ["Kalaburagi", "Vijayapura"]),
    ("Cheating", ["Hubballi-Dharwad", "Belagavi"]),
    ("Ganja Possession", ["Shivamogga", "Davanagere"]),
]

fir_accused = {}   # skeleton index -> list of (person, kind)
gangs = []
for minor, g_dists in GANG_SPECS:
    members = [new_person(age_lo=20, age_hi=38) for _ in range(rng.randint(3, 6))]
    n_firs = rng.randint(5, 10)
    pool = [i for i, s in enumerate(skeletons)
            if s["district"] in g_dists and s["minor"] == minor and i not in fir_accused]
    if len(pool) < n_firs:
        # mutate other FIRs in the gang's districts into the signature category
        candidates = [i for i, s in enumerate(skeletons)
                      if s["district"] in g_dists and i not in fir_accused
                      and s["minor"] != minor
                      and s["major"] not in ("Crimes Against Women",)]
        rng.shuffle(candidates)
        for i in candidates[: n_firs - len(pool)]:
            skeletons[i]["minor"] = minor
            skeletons[i]["major"] = MINOR_TO_MAJOR[minor]
            pool.append(i)
    chosen = rng.sample(pool, min(n_firs, len(pool)))
    for i in chosen:
        subset = rng.sample(members, rng.randint(2, min(4, len(members))))
        fir_accused[i] = [(p, "gang") for p in subset]
    gangs.append({"minor": minor, "districts": g_dists, "members": members,
                  "firs": chosen})

# ---------------------------------------------------------------------------
# Phase C: solo repeat offenders
# ---------------------------------------------------------------------------

SOLO_MINORS = ["Chain Snatching", "Vehicle Theft", "House Burglary",
               "Mobile Phone Theft", "OTP Fraud", "Assault", "Cheating",
               "Ganja Possession", "Stalking", "Robbery"]
solo_offenders = []
for _ in range(35):
    minor = rng.choice(SOLO_MINORS)
    p = new_person(gender="Male" if minor != "OTP Fraud" else None)
    pool = [i for i, s in enumerate(skeletons)
            if s["minor"] == minor and i not in fir_accused]
    # prefer a single district for a consistent beat
    dists = sorted({skeletons[i]["district"] for i in pool})
    if dists:
        home = rng.choice(dists)
        home_pool = [i for i in pool if skeletons[i]["district"] == home]
        if len(home_pool) >= 2:
            pool = home_pool
    n = min(rng.randint(2, 5), len(pool))
    for i in rng.sample(pool, n):
        fir_accused[i] = [(p, "solo")]
    solo_offenders.append(p)

# ---------------------------------------------------------------------------
# Phase D: materialize FIR rows
# ---------------------------------------------------------------------------

ONE_OFF_PROB = {
    "Property Crimes": 0.72, "Crimes Against Body": 0.85,
    "Cyber Crimes": 0.35, "Crimes Against Women": 0.80, "Narcotics": 0.95,
    "Economic Offences": 0.55, "Road Incidents": 0.55, "Public Order": 0.90,
}

fir_rows, accused_rows, victim_rows, chargesheet_rows, ipc_map_rows = [], [], [], [], []
seq_counters = {}
section_rowid = {(s[0], s[3]): i + 1 for i, s in enumerate(IPC_SECTIONS)}

for idx, sk in enumerate(skeletons):
    dist, major, minor, d = sk["district"], sk["major"], sk["minor"], sk["date"]
    si = rng.choice(district_stations[dist])
    st = stations[si]

    # coordinates: ~60% clustered into district hotspots
    if rng.random() < 0.60:
        hy, hx = rng.choice(hotspots[dist])
        lat = hy + rng.uniform(-0.01, 0.01)
        lon = hx + rng.uniform(-0.01, 0.01)
    else:
        lat = st["latitude"] + rng.uniform(-0.02, 0.02)
        lon = st["longitude"] + rng.uniform(-0.02, 0.02)

    hour = pick_hour(minor, major)
    incident_from = datetime(d.year, d.month, d.day, hour, rng.randint(0, 59))
    incident_to = incident_from + timedelta(minutes=rng.randint(0, 240))
    info_received = incident_from + timedelta(hours=rng.uniform(1, 48))
    now_cap = datetime(TODAY.year, TODAY.month, TODAY.day, 23, 59)
    info_received = min(info_received, now_cap)
    reported = info_received.date() + timedelta(days=rng.choices([0, 1, 2], weights=[70, 20, 10])[0])
    reported = min(reported, TODAY)

    key = (st["code"], reported.year)
    seq_counters[key] = seq_counters.get(key, 0) + 1
    fir_number = f"{st['code']}-{seq_counters[key]:04d}/{reported.year}"

    crime_category = rng.choices(["FIR", "Zero FIR", "UDR"], weights=[88, 8, 4])[0]
    gravity = "Heinous" if (minor in ("Murder", "Attempt to Murder", "Kidnapping")
                            or (minor == "Robbery" and rng.random() < 0.30)) else "Non-Heinous"

    age_days = (TODAY - reported).days
    if age_days > 365:
        status = rng.choices(["Charge Sheeted", "Closed", "Under Investigation"],
                             weights=[45, 30, 25])[0]
    else:
        resolved_p = 0.20 + 0.50 * (age_days / 365.0)
        if rng.random() < resolved_p:
            status = "Charge Sheeted" if rng.random() < 0.55 else "Closed"
        else:
            status = "Under Investigation"

    loc = st["locality"]
    other = [stations[j]["locality"] for j in district_stations[dist] if j != si]
    loc2 = rng.choice(other) if other else loc
    facts = make_brief_facts(minor, loc, loc2, incident_from.date(), hour)

    fir_rows.append((
        fir_number, facts, crime_category, reported.isoformat(), dist,
        st["station_name"], status, round(lat, 6), round(lon, 6), gravity,
        major, minor, f"{dist} District Court",
        incident_from.isoformat(sep=" "), incident_to.isoformat(sep=" "),
        info_received.replace(microsecond=0).isoformat(sep=" "),
    ))
    fir_rowid = len(fir_rows)

    # Chargesheet
    if status == "Charge Sheeted":
        filing = reported + timedelta(days=rng.randint(30, 180))
        if filing > TODAY:
            filing = reported + timedelta(days=max(7, min(180, age_days)))
            filing = min(filing, TODAY)
        chargesheet_rows.append((fir_rowid, filing.isoformat(), "Filed",
                                 "Final Report", rng.choice(station_officers[si])))

    # IPC sections (1-3, consistent with minor head)
    always, optional = IPC_MAP_RULES[minor]
    secs = list(always)
    for s in optional:
        if len(secs) >= 3:
            break
        if rng.random() < 0.40:
            secs.append(s)
    for s in secs[:3]:
        act_short = "IT Act" if s in ("66C", "66D") else ("NDPS Act" if s in ("20", "22") else "IPC")
        ipc_map_rows.append((fir_rowid, section_rowid[(s, act_short)]))

    # Accused
    people = list(fir_accused.get(idx, []))
    if not people and rng.random() < ONE_OFF_PROB[major]:
        n = rng.choices([1, 2, 3], weights=[70, 22, 8])[0]
        if minor in ("Rioting", "Unlawful Assembly"):
            n = rng.randint(2, 4)
        people = [(new_person(), "oneoff") for _ in range(n)]
    elif people and rng.random() < 0.15:
        people.append((new_person(), "oneoff"))

    for p, _kind in people:
        age = p["base_age"] + max(0, reported.year - p["base_year"])
        arrested = rng.random() < 0.55
        arrest_date = None
        if arrested:
            arrest_date = min(reported + timedelta(days=rng.randint(0, 60)), TODAY).isoformat()
        accused_rows.append((
            p["name"], age, f"{loc2}, {dist}", fir_rowid, p["gender"],
            p["person_id"],
            arrest_date,
            "Karnataka" if arrested else None,
            dist if arrested else None,
            st["station_name"] if arrested else None,
            rng.choice(station_officers[si]) if arrested else None,
        ))

    # Victims
    if major == "Crimes Against Women":
        n_vic = rng.choices([1, 2], weights=[85, 15])[0]
    elif minor == "Murder":
        n_vic = 1
    elif major == "Cyber Crimes":
        n_vic = 1
    else:
        n_vic = rng.choices([0, 1, 2, 3], weights=[20, 55, 18, 7])[0]
    for v_i in range(n_vic):
        if major == "Crimes Against Women" and v_i == 0:
            vg = "Female"
        else:
            vg = "Female" if rng.random() < 0.4 else "Male"
        is_police = 1 if (major == "Public Order" and rng.random() < 0.15) else 0
        victim_rows.append((
            person_name(vg), rng.randint(16, 72), fir_rowid, vg, is_police,
            1 if v_i == 0 else 0, rng.choice(OCCUPATIONS), "-", "-",
        ))

# ---------------------------------------------------------------------------
# Write to SQLite
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE FIRs (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    fir_number VARCHAR NOT NULL, brief_facts TEXT, crime_category VARCHAR,
    date_reported VARCHAR, district VARCHAR, police_station VARCHAR,
    status VARCHAR, latitude DECIMAL, longitude DECIMAL, gravity VARCHAR,
    crime_major_head VARCHAR, crime_minor_head VARCHAR, court_name VARCHAR,
    incident_from_date VARCHAR, incident_to_date VARCHAR, info_received_date VARCHAR
);
CREATE TABLE Accused (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR, age INTEGER, address TEXT, fir_rowid INTEGER, gender VARCHAR,
    person_id VARCHAR, arrest_date VARCHAR, arrest_state VARCHAR,
    arrest_district VARCHAR, arrest_station VARCHAR, arrest_officer_name VARCHAR,
    FOREIGN KEY(fir_rowid) REFERENCES FIRs(ROWID)
);
CREATE TABLE Victims (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR, age INTEGER, fir_rowid INTEGER, gender VARCHAR,
    is_police BOOLEAN, is_complainant BOOLEAN, occupation VARCHAR,
    religion VARCHAR, caste VARCHAR,
    FOREIGN KEY(fir_rowid) REFERENCES FIRs(ROWID)
);
CREATE TABLE IPCSections (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    section_number VARCHAR, description VARCHAR, act_name VARCHAR,
    act_short_name VARCHAR, is_active BOOLEAN
);
CREATE TABLE FIR_IPC_Map (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    fir_rowid INTEGER, ipc_rowid INTEGER,
    FOREIGN KEY(fir_rowid) REFERENCES FIRs(ROWID),
    FOREIGN KEY(ipc_rowid) REFERENCES IPCSections(ROWID)
);
CREATE TABLE PoliceStations (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    station_name VARCHAR, district VARCHAR, latitude DECIMAL, longitude DECIMAL,
    unit_type VARCHAR, state VARCHAR
);
CREATE TABLE Officers (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR, rank VARCHAR, station_rowid INTEGER, designation VARCHAR,
    kgid VARCHAR, dob VARCHAR, gender VARCHAR, blood_group VARCHAR,
    is_physically_challenged BOOLEAN, appointment_date VARCHAR,
    FOREIGN KEY(station_rowid) REFERENCES PoliceStations(ROWID)
);
CREATE TABLE Chargesheets (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    fir_rowid INTEGER, filing_date VARCHAR, status VARCHAR,
    charge_sheet_type VARCHAR, filing_officer_name VARCHAR,
    FOREIGN KEY(fir_rowid) REFERENCES FIRs(ROWID)
);
"""


def main():
    path = db_path_from_settings()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    for tbl in ("FIR_IPC_Map", "Chargesheets", "Accused", "Victims", "Officers",
                "FIRs", "IPCSections", "PoliceStations"):
        cur.execute(f"DROP TABLE IF EXISTS {tbl}")
    cur.executescript(DDL)

    cur.executemany(
        "INSERT INTO PoliceStations (station_name, district, latitude, longitude, unit_type, state) "
        "VALUES (?,?,?,?,?,?)",
        [(s["station_name"], s["district"], s["latitude"], s["longitude"],
          s["unit_type"], s["state"]) for s in stations])
    cur.executemany(
        "INSERT INTO Officers (name, rank, station_rowid, designation, kgid, dob, gender, "
        "blood_group, is_physically_challenged, appointment_date) VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(o["name"], o["rank"], o["station_rowid"], o["designation"], o["kgid"],
          o["dob"], o["gender"], o["blood_group"], o["is_physically_challenged"],
          o["appointment_date"]) for o in officers])
    cur.executemany(
        "INSERT INTO IPCSections (section_number, description, act_name, act_short_name, is_active) "
        "VALUES (?,?,?,?,1)", IPC_SECTIONS)
    cur.executemany(
        "INSERT INTO FIRs (fir_number, brief_facts, crime_category, date_reported, district, "
        "police_station, status, latitude, longitude, gravity, crime_major_head, crime_minor_head, "
        "court_name, incident_from_date, incident_to_date, info_received_date) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", fir_rows)
    cur.executemany(
        "INSERT INTO Accused (name, age, address, fir_rowid, gender, person_id, arrest_date, "
        "arrest_state, arrest_district, arrest_station, arrest_officer_name) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)", accused_rows)
    cur.executemany(
        "INSERT INTO Victims (name, age, fir_rowid, gender, is_police, is_complainant, "
        "occupation, religion, caste) VALUES (?,?,?,?,?,?,?,?,?)", victim_rows)
    cur.executemany(
        "INSERT INTO Chargesheets (fir_rowid, filing_date, status, charge_sheet_type, "
        "filing_officer_name) VALUES (?,?,?,?,?)", chargesheet_rows)
    cur.executemany(
        "INSERT INTO FIR_IPC_Map (fir_rowid, ipc_rowid) VALUES (?,?)", ipc_map_rows)
    conn.commit()

    print(f"Database regenerated at {path}\n")
    print(f"{'Table':<16}{'Rows':>8}")
    print("-" * 24)
    for tbl in ("FIRs", "Accused", "Victims", "IPCSections", "FIR_IPC_Map",
                "PoliceStations", "Officers", "Chargesheets"):
        n = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"{tbl:<16}{n:>8}")

    repeat = cur.execute(
        "SELECT COUNT(*) FROM (SELECT person_id FROM Accused GROUP BY person_id "
        "HAVING COUNT(DISTINCT fir_rowid) >= 2)").fetchone()[0]
    # Mirror every table to CSV beside the DB. These are committed (see
    # .gitignore) so teammates can pull the same corpus without re-running
    # the generator — they must never drift from the database.
    csv_dir = os.path.dirname(path)
    for tbl in ("FIRs", "Accused", "Victims", "IPCSections", "FIR_IPC_Map",
                "PoliceStations", "Officers", "Chargesheets"):
        cur.execute(f"SELECT * FROM {tbl}")
        cols = [d[0] for d in cur.description]
        with open(os.path.join(csv_dir, f"{tbl}.csv"), "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(cols)
            writer.writerows(cur.fetchall())
    print(f"\nExported 8 CSV mirrors to {csv_dir}")

    print(f"\nRepeat offenders (person_id with >=2 FIRs): {repeat}")
    print(f"Gangs: {len(gangs)} | gang FIRs: {sum(len(g['firs']) for g in gangs)}")
    for label, (existing, baseline, target) in (
            ("Bengaluru City / Chain Snatching", sp1),
            ("Mangaluru / Synthetic Drugs Peddling", sp2),
            ("Mangaluru / Ganja Possession", sp3)):
        print(f"Spike {label}: baseline {baseline:.1f}/mo -> last-30d target {target}")
    conn.close()


if __name__ == "__main__":
    main()
