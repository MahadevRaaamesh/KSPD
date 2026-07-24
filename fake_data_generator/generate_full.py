import sqlite3
import pandas as pd
from faker import Faker
import random
import string
import requests
import json
import argparse
import os
import time

fake = Faker('en_IN')

# Setup Database
def setup_database(db_path, schema_path):
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    conn.executescript(schema_sql)
    return conn

def generate_static_data(conn):
    print("Generating Static Lookups...")
    
    # IPCSections
    sections = [
        (1, '302', 'Punishment for murder', 'Indian Penal Code', 'IPC', True),
        (2, '379', 'Punishment for theft', 'Indian Penal Code', 'IPC', True),
        (3, '420', 'Cheating and dishonestly inducing delivery of property', 'Indian Penal Code', 'IPC', True),
        (4, '392', 'Punishment for robbery', 'Indian Penal Code', 'IPC', True),
        (5, '20', 'Punishment for contravention in relation to cannabis plant and cannabis', 'Narcotic Drugs and Psychotropic Substances Act', 'NDPS', True)
    ]
    conn.executemany("INSERT INTO IPCSections VALUES (?,?,?,?,?,?)", sections)
    
    # PoliceStations
    districts = [fake.city() for _ in range(5)]
    stations = []
    station_id = 1
    for dist in districts:
        for _ in range(3): # 3 stations per district
            stations.append((
                station_id, f"{fake.city()} PS", dist, 
                float(fake.latitude()), float(fake.longitude()), 
                'Police Station', 'Karnataka'
            ))
            station_id += 1
            
    conn.executemany("INSERT INTO PoliceStations VALUES (?,?,?,?,?,?,?)", stations)
    
    # Officers
    officers = []
    officer_id = 1
    ranks = ['Constable', 'Head Constable', 'Sub-Inspector', 'Inspector']
    designations = ['Beat Officer', 'Investigating Officer (IO)', 'Station House Officer (SHO)']
    
    for st in stations:
        for _ in range(5): # 5 officers per station
            officers.append((
                officer_id, fake.name(), random.choice(ranks), st[0],
                random.choice(designations), ''.join(random.choices(string.digits, k=10)),
                fake.date_of_birth(minimum_age=25, maximum_age=58).isoformat(),
                random.choice(['Male', 'Female']),
                random.choice(['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']),
                random.choice([True, False, False, False]), # 25% chance physically challenged
                fake.date_between(start_date='-15y', end_date='-1y').isoformat()
            ))
            officer_id += 1
            
    conn.executemany("INSERT INTO Officers VALUES (?,?,?,?,?,?,?,?,?,?,?)", officers)
    conn.commit()
    
    return stations, officers, sections

def call_llm_batch(api_url, crime_types, count=5):
    crime_list_str = ", ".join(crime_types)
    prompt = f"Generate a JSON array containing exactly {count} distinct police FIR brief facts (narrative summaries). "
    prompt += f"Make them realistic and relevant to these crime types: {crime_list_str}. "
    prompt += "Each summary should be 2-3 sentences. Output ONLY a valid JSON array of strings, nothing else."

    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that strictly outputs valid JSON arrays of strings."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 800
    }

    try:
        response = requests.post(f"{api_url}/chat/completions", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        content = data['choices'][0]['message']['content']
        content = content.replace("```json", "").replace("```", "").strip()
        facts = json.loads(content)
        if isinstance(facts, list) and len(facts) >= count:
            return facts[:count]
    except Exception as e:
        print(f"LLM call failed or returned invalid format: {e}. Falling back to Faker.")
    
    return [fake.text(max_nb_chars=300) for _ in range(count)]

def generate_cases_and_events(conn, num_cases, stations, officers, ipc_sections, api_url):
    print(f"Generating {num_cases} Cases...")
    firs = []
    accused_list = []
    victims = []
    fir_ipc_maps = []
    chargesheets = []
    
    crime_categories = ['FIR', 'UDR', 'Zero FIR']
    gravity_options = ['Heinous', 'Non-Heinous']
    major_heads = ['Crimes Against Body', 'Property Crimes', 'Cyber Crimes', 'Narcotics']
    status_options = ['Under Investigation', 'Charge Sheeted', 'Closed']
    
    batch_size = 5
    fir_id = 1
    accused_id = 1
    victim_id = 1
    map_id = 1
    cs_id = 1

    for batch_start in range(0, num_cases, batch_size):
        current_batch_size = min(batch_size, num_cases - batch_start)
        batch_crime_types = [random.choice(major_heads) for _ in range(current_batch_size)]
        
        print(f"Calling LLM for batch {batch_start//batch_size + 1} ({current_batch_size} facts)...")
        brief_facts = call_llm_batch(api_url, batch_crime_types, current_batch_size)
        
        while len(brief_facts) < current_batch_size:
            brief_facts.append(fake.text(max_nb_chars=300))

        for i in range(current_batch_size):
            st = random.choice(stations)
            crime_reg_date = fake.date_time_this_year()
            c_status = random.choice(status_options)
            
            firs.append((
                fir_id,
                f"{random.randint(1,9)}{st[0]:04d}{crime_reg_date.year}{fir_id:05d}",
                brief_facts[i][:1500],
                random.choice(crime_categories),
                crime_reg_date.date().isoformat(),
                st[2], # district
                st[1], # station_name
                c_status,
                float(fake.latitude()), float(fake.longitude()),
                random.choice(gravity_options),
                batch_crime_types[i],
                fake.word().capitalize(), # minor head
                f"{st[2]} District Court", # court name
                (crime_reg_date - pd.Timedelta(days=random.randint(1, 10))).isoformat(),
                crime_reg_date.isoformat(),
                crime_reg_date.isoformat()
            ))

            # 1-3 IPC Sections mapped
            num_sections = random.randint(1, 3)
            selected_sections = random.sample(ipc_sections, num_sections)
            for sec in selected_sections:
                fir_ipc_maps.append((map_id, fir_id, sec[0]))
                map_id += 1

            # 1-3 Accused
            for j in range(random.randint(1, 3)):
                is_arrested = random.choice([True, False])
                arr_date = (crime_reg_date + pd.Timedelta(days=random.randint(1, 30))).isoformat() if is_arrested else None
                arr_state = 'Karnataka' if is_arrested else None
                arr_dist = st[2] if is_arrested else None
                arr_st = st[1] if is_arrested else None
                arr_off = random.choice(officers)[1] if is_arrested else None

                accused_list.append((
                    accused_id, fake.name(), random.randint(18, 65), fake.address(), fir_id,
                    random.choice(['Male', 'Female']), f"A{j+1}",
                    arr_date, arr_state, arr_dist, arr_st, arr_off
                ))
                accused_id += 1
                
            # 1-2 Victims
            for _ in range(random.randint(1, 2)):
                victims.append((
                    victim_id, fake.name(), random.randint(10, 80), fir_id,
                    random.choice(['Male', 'Female']),
                    random.choice([True, False]), # is_police
                    random.choice([True, False]), # is_complainant
                    random.choice(['Student', 'Private Sector', 'Govt Employee', 'Business']),
                    random.choice(['Hindu', 'Muslim', 'Christian', 'Other']),
                    random.choice(['General', 'OBC', 'SC', 'ST'])
                ))
                victim_id += 1

            # Chargesheet (if status is Charge Sheeted or Closed)
            if c_status in ['Charge Sheeted', 'Closed']:
                chargesheets.append((
                    cs_id, fir_id,
                    (crime_reg_date + pd.Timedelta(days=random.randint(30, 90))).isoformat(),
                    'Submitted',
                    random.choice(['Chargesheet', 'False Case', 'Undetected']),
                    random.choice(officers)[1]
                ))
                cs_id += 1

            fir_id += 1

        time.sleep(0.5)
        
    conn.executemany("INSERT INTO FIRs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", firs)
    conn.executemany("INSERT INTO FIR_IPC_Map VALUES (?,?,?)", fir_ipc_maps)
    conn.executemany("INSERT INTO Accused VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", accused_list)
    conn.executemany("INSERT INTO Victims VALUES (?,?,?,?,?,?,?,?,?,?)", victims)
    conn.executemany("INSERT INTO Chargesheets VALUES (?,?,?,?,?,?)", chargesheets)
    conn.commit()

def export_db_to_csv(conn, output_dir):
    print(f"Exporting SQLite database to CSVs in '{output_dir}'...")
    os.makedirs(output_dir, exist_ok=True)
    
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table_name in tables:
        table = table_name[0]
        # Ignore system tables
        if table == "sqlite_sequence":
            continue
            
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        df.to_csv(os.path.join(output_dir, f"{table}.csv"), index=False)
        print(f"  -> Exported {table}.csv")

def main():
    parser = argparse.ArgumentParser()
    # Updated defaults for data sharing
    parser.add_argument("--db", default="../backend/data/mock_data/mock_fir_data.db", help="Path to output sqlite DB")
    parser.add_argument("--cases", type=int, default=50, help="Number of cases to generate")
    parser.add_argument("--llm-url", default="http://localhost:8080/v1", help="URL for the llama.cpp compatible endpoint")
    parser.add_argument("--export-csv", default="../backend/data/mock_data/", help="Directory to export CSV files")
    args = parser.parse_args()

    # Ensure paths are relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.normpath(os.path.join(script_dir, args.db))
    csv_dir = os.path.normpath(os.path.join(script_dir, args.export_csv))

    if os.path.exists(db_path):
        os.remove(db_path)

    print("Setting up schema...")
    schema_path = os.path.join(script_dir, 'schema.sql')
    conn = setup_database(db_path, schema_path)

    stations, officers, ipc_sections = generate_static_data(conn)
    generate_cases_and_events(conn, args.cases, stations, officers, ipc_sections, args.llm_url)

    print(f"Data generation complete! Saved to {db_path}")
    
    if args.export_csv:
        export_db_to_csv(conn, csv_dir)
        
    conn.close()

if __name__ == "__main__":
    main()
