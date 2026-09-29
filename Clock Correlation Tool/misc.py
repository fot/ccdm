import json
import re
from pathlib import Path
from datetime import datetime


def get_constants():
    """Loads constants"""
    file_path= Path(__file__).parent.resolve() / "constants.json"
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("[WARNING] constants.json not found. Using empty database.")
        return {}


def log_callback(msg):
    print(f"[LOG] {msg}")


def error_callback(msg):
    print(f"[ERROR] {msg}")


def load_dsn_database(json_path):
    """Loads the DSN station calibration database."""
    try:
        with open(json_path, 'r') as f:
            print(f"[LOG] Successfully loaded dsn_data.json.")
            return json.load(f)
    except FileNotFoundError:
        print("[WARNING] dsn_data.json not found. Using empty database.")
        return {}


def load_calib_database(json_path):
    """Loads the spacecraft hardware calibration delay database."""
    try:
        with open(json_path, 'r') as f:
            print(f"[LOG] Successfully loaded calib_data.json.")
            return json.load(f)
    except FileNotFoundError:
        print("[WARNING] calib_data.json not found. Using empty database.")
        return {}


def get_cumulative_leap_seconds(dt):
    if dt >= datetime(2017, 1, 1): return 37.0
    if dt >= datetime(2015, 7, 1): return 36.0
    if dt >= datetime(2012, 7, 1): return 35.0
    if dt >= datetime(2009, 1, 1): return 34.0
    if dt >= datetime(2006, 1, 1): return 33.0
    if dt >= datetime(1999, 1, 1): return 32.0 
    return 0.0


def is_consecutive_check(df):
    "check if corrected_vcdu values are consecutive"
    diffs = df.groupby('pass_id')['corrected_vcdu'].diff()
    failed_rows = df[(diffs != 1) & diffs.notna()]

    if failed_rows.empty:
        log_callback("corrected_vcdu consecutive check: PASS")
    else:
        log_callback("corrected_vcdu consecutive check: FAIL")

        # Log the specific failing indices and their values for debugging
        error_details = failed_rows[['pass_id', 'corrected_vcdu']].to_string()
        log_callback(f"Sequence broken at these rows:\n{error_details}")

def get_incremented_clkhst_name(filepath):
                    p = Path(filepath)
                    match = re.match(r"(CLKHST_)(\d+)", p.stem, re.IGNORECASE)
                    if match:
                        prefix = match.group(1).upper()
                        num = int(match.group(2))
                        return f"{prefix}{num + 1}{p.suffix.upper()}"
                    return f"NEW_{p.name}"
