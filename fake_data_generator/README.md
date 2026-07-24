# Fake Data Generator for KSPD

This folder contains scripts to generate fake data that matches the schema described in the `Police_FIR_ER_Diagram.pdf`.

It uses the `Faker` library (with the Indian locale) to generate realistic names and information, and uses `pandas` along with `SQLAlchemy` to either dump the data into a target database or export it to CSVs.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

You can run the script directly. By default, it will create a small sample of data and load it into a local SQLite database named `mock_fir_data.db`.

```bash
python generate_full.py
```

### Options

You can pass arguments to control how much data is generated and where it is saved:

- `--cases`: Integer, number of FIR cases to generate. Defaults to 50.
- `--db`: Path to output the local SQLite database. Defaults to `mock_fir_data.db`.
- `--llm-url`: Point to your local llama.cpp endpoint. Defaults to `http://localhost:8080/v1`.
- `--export-csv`: Directory to export CSV files.

**How to guarantee CSV and Database data are related:**
Because relational integrity (foreign keys) is crucial, the script always builds the database first. If you want CSVs, the script will dump the exact, perfectly mapped tables from the generated SQLite database into the CSV folder. 

This means that if you load the CSVs into PostgreSQL (or Zoho Catalyst Data Store), the IDs will perfectly align!

**Example:**
Generate 100 cases using your local LLM, save to SQLite, and simultaneously dump matching CSV files to a folder:
```bash
python generate_full.py --cases 100 --llm-url "http://localhost:8080/v1" --export-csv ./kspd_csv_data
```
