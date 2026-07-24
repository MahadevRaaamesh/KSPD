import asyncio
import random
import sys
import os

# Add parent directory to path to import adapters and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.database import (
    init_db, execute_insert, execute_query,
    case_master, accused, victim, unit, district,
    act_section_association, act, section, crime_head, crime_sub_head, case_status_master
)

DISTRICTS = ["Bengaluru Urban", "Mysuru", "Hubballi-Dharwad", "Mangaluru", "Belagavi"]

POLICE_STATIONS = {
    "Bengaluru Urban": ["Indiranagar PS", "Koramangala PS", "Whitefield PS", "Jayanagar PS"],
    "Mysuru": ["Devaraja PS", "Lashkar PS", "Kuvempunagar PS"],
    "Hubballi-Dharwad": ["Suburban PS", "Vidyanagar PS"],
    "Mangaluru": ["Barke PS", "Kadri PS", "Pandeshwar PS"],
    "Belagavi": ["Market PS", "Camp PS"]
}

CRIME_HEADS = [
    (1, "Crimes Against Body"),
    (2, "Crimes Against Property"),
    (3, "Economic Offences"),
    (4, "Cyber Crimes")
]

CRIME_SUB_HEADS = [
    (1, 1, "Murder"),
    (2, 1, "Attempt to Murder"),
    (3, 2, "Robbery"),
    (4, 2, "Theft"),
    (5, 2, "Burglary"),
    (6, 3, "Cheating"),
    (7, 4, "Phishing")
]

STATUSES = [
    (1, "Under Investigation"),
    (2, "Charge Sheeted"),
    (3, "Closed"),
    (4, "Undetected")
]

ACTS = [
    ("IPC", "Indian Penal Code", "IPC"),
    ("NDPS", "Narcotic Drugs and Psychotropic Substances Act", "NDPS"),
    ("ITACT", "Information Technology Act", "IT Act")
]

SECTIONS = [
    ("IPC", "302", "Punishment for murder"),
    ("IPC", "307", "Attempt to murder"),
    ("IPC", "392", "Punishment for robbery"),
    ("IPC", "379", "Punishment for theft"),
    ("IPC", "420", "Cheating and dishonestly inducing delivery of property"),
    ("NDPS", "20", "Punishment for contravention in relation to cannabis plant and cannabis"),
    ("ITACT", "66D", "Punishment for cheating by personation by using computer resource")
]

BRIEF_FACTS_TEMPLATES = [
    "The complainant reported that unknown persons entered their house by breaking the back door and stole gold ornaments worth Rs. {amount}.",
    "A person was found dead under suspicious circumstances near {landmark}. Preliminary investigation suggests foul play.",
    "The victim was threatened at knifepoint near {landmark} and their mobile phone and wallet were snatched.",
    "A fraudulent transaction of Rs. {amount} was made from the complainant's bank account after they shared an OTP.",
    "During a routine patrol, police intercepted a vehicle and recovered illegal substances.",
    "Two groups clashed near {landmark} resulting in severe injuries to three individuals."
]

LANDMARKS = ["the central bus stand", "the main market", "the railway station", "a local park", "an ATM kiosk"]

NAMES = ["Ramesh", "Suresh", "Mahesh", "Kumar", "Rahul", "Rajesh", "Priya", "Kavya", "Sneha", "Anjali", "Manjula"]
LAST_NAMES = ["Gowda", "Patil", "Shetty", "Rao", "Nayak", "Kamat", "Hegde"]

async def generate_data():
    print("Initializing Database...")
    await init_db()
    
    print("Populating lookup tables...")
    # Districts
    district_map = {}
    for i, d_name in enumerate(DISTRICTS, 1):
        d_id = await execute_insert("District", {"DistrictName": d_name})
        district_map[d_name] = d_id
        
    # Police Stations
    station_map = {}
    for d_name, stations in POLICE_STATIONS.items():
        for s_name in stations:
            s_id = await execute_insert("Unit", {
                "UnitName": s_name, 
                "DistrictID": district_map[d_name],
                "StateID": 1
            })
            station_map[s_name] = s_id
            
    # Crime Heads
    for ch_id, ch_name in CRIME_HEADS:
        await execute_insert("CrimeHead", {"CrimeGroupName": ch_name})
        
    # Crime Sub Heads
    for csh_id, ch_id, csh_name in CRIME_SUB_HEADS:
        await execute_insert("CrimeSubHead", {"CrimeHeadID": ch_id, "CrimeHeadName": csh_name})
        
    # Statuses
    for st_id, st_name in STATUSES:
        await execute_insert("CaseStatusMaster", {"CaseStatusID": st_id, "CaseStatusName": st_name})
        
    # Acts & Sections
    for act_code, desc, short in ACTS:
        await execute_insert("Act", {"ActCode": act_code, "ActDescription": desc, "ShortName": short})
        
    for act_code, sec_code, desc in SECTIONS:
        await execute_insert("Section", {"ActCode": act_code, "SectionCode": sec_code, "SectionDescription": desc})

    print("Generating FIRs, Accused, and Victims...")
    
    # Generate 500 FIRs
    for i in range(1, 501):
        district_name = random.choice(DISTRICTS)
        station_name = random.choice(POLICE_STATIONS[district_name])
        
        csh_id, ch_id, csh_name = random.choice(CRIME_SUB_HEADS)
        status = random.choice(STATUSES)
        
        # Determine Act/Section based on subhead
        if csh_name == "Murder":
            act_sec = ("IPC", "302")
        elif csh_name == "Attempt to Murder":
            act_sec = ("IPC", "307")
        elif csh_name == "Robbery":
            act_sec = ("IPC", "392")
        elif csh_name == "Theft" or csh_name == "Burglary":
            act_sec = ("IPC", "379")
        elif csh_name == "Cheating":
            act_sec = ("IPC", "420")
        elif csh_name == "Phishing":
            act_sec = ("ITACT", "66D")
        else:
            act_sec = ("IPC", "392")
            
        facts = random.choice(BRIEF_FACTS_TEMPLATES).format(
            amount=random.randint(5, 500) * 1000,
            landmark=random.choice(LANDMARKS)
        )
        
        # Base Lat/Lng roughly around Karnataka
        lat = 12.0 + random.random() * 6.0
        lng = 74.0 + random.random() * 4.0
        
        fir_data = {
            "CrimeNo": f"{random.randint(1,9)}044300062024{i:05d}",
            "CaseNo": f"2024{i:05d}",
            "CrimeRegisteredDate": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "PoliceStationID": station_map[station_name],
            "CrimeMajorHeadID": ch_id,
            "CrimeMinorHeadID": csh_id,
            "CaseStatusID": status[0],
            "BriefFacts": facts,
            "latitude": round(lat, 6),
            "longitude": round(lng, 6)
        }
        
        fir_id = await execute_insert("CaseMaster", fir_data)
        
        # Accused
        num_accused = random.randint(1, 4) if status[0] in [1, 2] else 0
        for a in range(num_accused):
            name = f"{random.choice(NAMES)} {random.choice(LAST_NAMES)}"
            await execute_insert("Accused", {
                "CaseMasterID": fir_id,
                "AccusedName": name,
                "AgeYear": random.randint(18, 60),
                "GenderID": random.choice([1, 2])
            })
            
        # Victims
        num_victims = random.randint(1, 2)
        for v in range(num_victims):
            name = f"{random.choice(NAMES)} {random.choice(LAST_NAMES)}"
            await execute_insert("Victim", {
                "CaseMasterID": fir_id,
                "VictimName": name,
                "AgeYear": random.randint(20, 70),
                "GenderID": random.choice([1, 2])
            })
            
    print("Mock data generation complete!")

if __name__ == "__main__":
    asyncio.run(generate_data())
