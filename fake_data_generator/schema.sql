PRAGMA foreign_keys = ON;

CREATE TABLE FIRs (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    fir_number VARCHAR NOT NULL,
    brief_facts TEXT,
    crime_category VARCHAR,
    date_reported VARCHAR,
    district VARCHAR,
    police_station VARCHAR,
    status VARCHAR,
    latitude DECIMAL,
    longitude DECIMAL,
    gravity VARCHAR,
    crime_major_head VARCHAR,
    crime_minor_head VARCHAR,
    court_name VARCHAR,
    incident_from_date VARCHAR,
    incident_to_date VARCHAR,
    info_received_date VARCHAR
);

CREATE TABLE Accused (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR,
    age INTEGER,
    address TEXT,
    fir_rowid INTEGER,
    gender VARCHAR,
    person_id VARCHAR,
    arrest_date VARCHAR,
    arrest_state VARCHAR,
    arrest_district VARCHAR,
    arrest_station VARCHAR,
    arrest_officer_name VARCHAR,
    FOREIGN KEY(fir_rowid) REFERENCES FIRs(ROWID)
);

CREATE TABLE Victims (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR,
    age INTEGER,
    fir_rowid INTEGER,
    gender VARCHAR,
    is_police BOOLEAN,
    is_complainant BOOLEAN,
    occupation VARCHAR,
    religion VARCHAR,
    caste VARCHAR,
    FOREIGN KEY(fir_rowid) REFERENCES FIRs(ROWID)
);

CREATE TABLE IPCSections (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    section_number VARCHAR,
    description VARCHAR,
    act_name VARCHAR,
    act_short_name VARCHAR,
    is_active BOOLEAN
);

CREATE TABLE FIR_IPC_Map (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    fir_rowid INTEGER,
    ipc_rowid INTEGER,
    FOREIGN KEY(fir_rowid) REFERENCES FIRs(ROWID),
    FOREIGN KEY(ipc_rowid) REFERENCES IPCSections(ROWID)
);

CREATE TABLE PoliceStations (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    station_name VARCHAR,
    district VARCHAR,
    latitude DECIMAL,
    longitude DECIMAL,
    unit_type VARCHAR,
    state VARCHAR
);

CREATE TABLE Officers (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR,
    rank VARCHAR,
    station_rowid INTEGER,
    designation VARCHAR,
    kgid VARCHAR,
    dob VARCHAR,
    gender VARCHAR,
    blood_group VARCHAR,
    is_physically_challenged BOOLEAN,
    appointment_date VARCHAR,
    FOREIGN KEY(station_rowid) REFERENCES PoliceStations(ROWID)
);

CREATE TABLE Chargesheets (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    fir_rowid INTEGER,
    filing_date VARCHAR,
    status VARCHAR,
    charge_sheet_type VARCHAR,
    filing_officer_name VARCHAR,
    FOREIGN KEY(fir_rowid) REFERENCES FIRs(ROWID)
);
