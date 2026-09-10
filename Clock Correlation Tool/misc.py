from pathlib import Path
import json
from datetime import datetime
from astropy.time import Time
import pandas as pd
import numpy as np


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


def nrt_keep_data(item):
    if ':' in item:
        return True
    try:
        np.float32(item)
        return True
    except ValueError:
        return False


def parse_erp_file(filepath):
    data = []
    epoch_1958_tai = Time("1985-01-01 00:00:00", scale="tai")

    with open(filepath, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) == 7 and ':' in parts[0] and parts[0][:4].isdigit():
                # Parse the standard UTC datetime string from the file
                dt = datetime.strptime(parts[0], "%Y:%j:%H:%M:%S.%f")

                # 2. Convert standard datetime to an Astropy UTC object
                t_utc = Time(dt, scale="utc")

                # 3. Calculate true elapsed seconds since 1958 in TAI
                # This automatically applies all historical leap seconds.
                abs_time = (t_utc.tai - epoch_1958_tai).sec

                data.append({
                    'datetime': dt,
                    'abs_time': abs_time,  # Unified Physics Epoch (leap-second corrected)
                    'pos-x': np.float64(parts[1]),
                    'pos-y': np.float64(parts[2]),
                    'pos-z': np.float64(parts[3]),
                    'vel-x': np.float64(parts[4]),
                    'vel-y': np.float64(parts[5]),
                    'vel-z': np.float64(parts[6])
                })

    log_callback(f"Parsed {Path(filepath).name} with {len(data)} entries.")
    return pd.DataFrame(data)


def parse_nrt_file(filepath):
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            parts = line.strip().split()
            parts = [item for item in parts if nrt_keep_data(item)]

            try:
                # If the line doesn't have enough columns to contain CIUMBITR, skip it
                if (int(parts[6]) != 6):
                    continue

                data.append({
                    'datetime': datetime.strptime(parts[0], "%Y:%j:%H:%M:%S"),
                    'vcdu': int(parts[1]),               # VCDU count (should be corrected for rollovers later)
                    'num_days': int(parts[2]),           # number of days since epoch
                    'num_ms': int(parts[3]),             # number of milliseconds in the current day
                    'num_us_frac': int(parts[4]),        # microsecond fraction in current millisecond
                    'dss_id': int(parts[5]),             # DSS station ID number
                    'bit_rate_code': int(parts[6]),      # Code number of bit rate of the data
                    'measured_bit_rate': np.float32(parts[7]) # Measured bit rate (should be close to the nominal bit rate)
                })
            except (IndexError, ValueError):
                continue
    log_callback(f"Parsed {Path(filepath).name} with {len(data)} entries.")
    return pd.DataFrame(data)
