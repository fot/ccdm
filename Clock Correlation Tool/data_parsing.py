from astropy.time import Time
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

from misc import log_callback


def nrt_keep_data(item):
    if ':' in item:
        return True

    if str(item).lower() in ["512k", "256k", "128k"]:
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


def parse_sto_file(filepath):
    """
    Parses an STO file into a standardized dataframe,
    mirroring the extraction pipeline for NRT files.
    """
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            parts = line.strip().split()
            parts = [item for item in parts if nrt_keep_data(item)]

            if len(parts) < 8:
                continue

            try:
                if str(parts[6].lower()) not in ["1024", "512k", "256k", "128k"]:
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


def parse_sto_contacts(df, time_col='datetime'):
    """
    Identifies all support contacts >= 2.0 minutes. Validates which
    contacts can support a 30-minute extraction with 5-minute margins.
    """
    df = df.sort_values(by=time_col).copy()
    df['time_diff'] = df[time_col].diff().dt.total_seconds()
    df['support_id'] = (df['time_diff'] > 60).cumsum()

    supports = []

    for support_id, group in df.groupby('support_id'):
        start_time = group[time_col].min()
        end_time = group[time_col].max()
        duration_sec = (end_time - start_time).total_seconds()

        # Minimum physical support duration matching contacts.pl
        if duration_sec >= 120:
            min_start = start_time + pd.Timedelta(minutes=2)
            window_start = min_start.ceil('10min')
            window_end = window_start + pd.Timedelta(minutes=30)
            max_end = end_time - pd.Timedelta(minutes=2)
            
            # Identify if it satisfies the specific extraction length constraint
            is_valid = window_end <= max_end
            
            supports.append({
                'start': start_time,
                'end': end_time,
                'duration_min': duration_sec / 60.0,
                'window_start': window_start if is_valid else None,
                'window_end': window_end if is_valid else None,
                'is_valid': is_valid
            })

    return supports
