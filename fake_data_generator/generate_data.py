import pandas as pd
from faker import Faker
import random
import string
from sqlalchemy import create_engine
import os
import argparse

fake = Faker('en_IN') # Use Indian locale for realistic names

def generate_states(n=1):
    return [{"StateID": i, "StateName": fake.state(), "NationalityID": 1, "Active": 1} for i in range(1, n + 1)]

def generate_districts(n=10, states=None):
    return [{"DistrictID": i, "DistrictName": fake.city(), "StateID": random.choice(states)["StateID"] if states else 1, "Active": 1} for i in range(1, n + 1)]

def generate_units(n=30, districts=None):
    units = []
    for i in range(1, n + 1):
        district = random.choice(districts) if districts else {"DistrictID": 1, "StateID": 1}
        units.append({
            "UnitID": i,
            "UnitName": f"{fake.city()} Police Station",
            "TypeID": random.randint(1, 3),
            "ParentUnit": None,
            "NationalityID": 1,
            "StateID": district["StateID"],
            "DistrictID": district["DistrictID"],
            "Active": 1
        })
    return units

def generate_employees(n=100, units=None, districts=None):
    employees = []
    for i in range(1, n + 1):
        unit = random.choice(units) if units else {"UnitID": 1, "DistrictID": 1}
        employees.append({
            "EmployeeID": i,
            "DistrictID": unit["DistrictID"],
            "UnitID": unit["UnitID"],
            "RankID": random.randint(1, 5),
            "DesignationID": random.randint(1, 5),
            "KGID": ''.join(random.choices(string.digits, k=10)),
            "FirstName": fake.name(),
            "EmployeeDOB": fake.date_of_birth(minimum_age=22, maximum_age=60),
            "GenderID": random.choice([1, 2]),
            "BloodGroupID": random.randint(1, 8),
            "PhysicallyChallenged": 0,
            "AppointmentDate": fake.date_between(start_date='-20y', end_date='-1y')
        })
    return employees

def generate_cases(n=500, units=None, employees=None):
    cases = []
    for i in range(1, n + 1):
        unit = random.choice(units) if units else {"UnitID": 1}
        emp = random.choice(employees) if employees else {"EmployeeID": 1}
        
        crime_reg_date = fake.date_time_this_year()
        incident_from = crime_reg_date - pd.Timedelta(days=random.randint(1, 30))
        
        cases.append({
            "CaseMasterID": i,
            "CrimeNo": f"{random.randint(1,9)}{unit['UnitID']:04d}{crime_reg_date.year}{i:05d}",
            "CaseNo": f"{crime_reg_date.year}{i:05d}",
            "CrimeRegisteredDate": crime_reg_date.date(),
            "PolicePersonID": emp["EmployeeID"],
            "PoliceStationID": unit["UnitID"],
            "CaseCategoryID": random.randint(1, 5),
            "GravityOffenceID": random.randint(1, 3),
            "CrimeMajorHeadID": random.randint(1, 10),
            "CrimeMinorHeadID": random.randint(1, 20),
            "CaseStatusID": random.randint(1, 4),
            "CourtID": random.randint(1, 5),
            "IncidentFromDate": incident_from,
            "IncidentToDate": incident_from + pd.Timedelta(hours=random.randint(1, 48)),
            "InfoReceivedPSDate": crime_reg_date,
            "latitude": float(fake.latitude()),
            "longitude": float(fake.longitude()),
            "BriefFacts": fake.text(max_nb_chars=500)
        })
    return cases

def generate_victims(n=600, cases=None):
    victims = []
    for i in range(1, n + 1):
        case = random.choice(cases) if cases else {"CaseMasterID": 1}
        victims.append({
            "VictimMasterID": i,
            "CaseMasterID": case["CaseMasterID"],
            "VictimName": fake.name(),
            "AgeYear": random.randint(5, 80),
            "GenderID": random.choice([1, 2]),
            "VictimPolice": random.choice(['0', '1'])
        })
    return victims

def generate_accused(n=700, cases=None):
    accused = []
    for i in range(1, n + 1):
        case = random.choice(cases) if cases else {"CaseMasterID": 1}
        accused.append({
            "AccusedMasterID": i,
            "CaseMasterID": case["CaseMasterID"],
            "AccusedName": fake.name(),
            "AgeYear": random.randint(18, 70),
            "GenderID": random.choice([1, 2]),
            "PersonID": f"A{random.randint(1,5)}"
        })
    return accused

def generate_all_data(scale=1.0):
    print(f"Generating data with scale {scale}...")
    states = generate_states(n=1)
    districts = generate_districts(n=int(30 * scale) or 1, states=states)
    units = generate_units(n=int(100 * scale) or 1, districts=districts)
    employees = generate_employees(n=int(500 * scale) or 1, units=units)
    cases = generate_cases(n=int(2000 * scale) or 1, units=units, employees=employees)
    victims = generate_victims(n=int(2500 * scale) or 1, cases=cases)
    accused = generate_accused(n=int(3000 * scale) or 1, cases=cases)
    
    return {
        "State": pd.DataFrame(states),
        "District": pd.DataFrame(districts),
        "Unit": pd.DataFrame(units),
        "Employee": pd.DataFrame(employees),
        "CaseMaster": pd.DataFrame(cases),
        "Victim": pd.DataFrame(victims),
        "Accused": pd.DataFrame(accused)
    }

def load_to_db(data_dict, db_uri):
    """
    Loads data into any database supported by SQLAlchemy.
    db_uri examples: 
        sqlite:///mock_fir_data.db
        postgresql://user:password@localhost/dbname
        mysql+pymysql://user:password@localhost/dbname
    """
    print(f"Loading data into {db_uri}...")
    engine = create_engine(db_uri)
    for table_name, df in data_dict.items():
        print(f"Loading table {table_name} ({len(df)} rows)...")
        df.to_sql(table_name, con=engine, if_exists='replace', index=False)
    print("Done!")

def export_to_csv(data_dict, output_dir):
    print(f"Exporting data to CSV in {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    for table_name, df in data_dict.items():
        path = os.path.join(output_dir, f"{table_name}.csv")
        df.to_csv(path, index=False)
        print(f"Exported {table_name} to {path}")
    print("Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate fake police FIR data based on the ER Diagram")
    parser.add_argument("--scale", type=float, default=0.1, help="Scale factor for data volume (default: 0.1)")
    parser.add_argument("--db-uri", type=str, help="Database URI to load data into (e.g., sqlite:///police_data.db)")
    parser.add_argument("--csv-dir", type=str, help="Directory to export CSV files")
    
    args = parser.parse_args()
    
    data = generate_all_data(scale=args.scale)
    
    if args.db_uri:
        load_to_db(data, args.db_uri)
    elif args.csv_dir:
        export_to_csv(data, args.csv_dir)
    else:
        # Default behavior: generate sqlite db in current folder
        default_db = "sqlite:///mock_fir_data.db"
        print(f"No output method specified. Defaulting to SQLite database at {default_db}")
        load_to_db(data, default_db)
