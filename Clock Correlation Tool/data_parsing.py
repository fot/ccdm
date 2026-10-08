import os
from astropy.time import Time
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

from misc import log_callback


def nrt_keep_data(item):
    if ':' in item:
        return True

    # Explicitly whitelist ALL expected string bitrates so they aren't deleted
    if str(item).lower() in ["1024", "512k", "256k", "128k"]:
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
                dt = datetime.strptime(parts[0], "%Y:%j:%H:%M:%S.%f")
                t_utc = Time(dt, scale="utc")
                abs_time = (t_utc.tai - epoch_1958_tai).sec

                data.append({
                    'datetime': dt,
                    'abs_time': abs_time,
                    'pos-x': np.float64(parts[1]),
                    'pos-y': np.float64(parts[2]),
                    'pos-z': np.float64(parts[3]),
                    'vel-x': np.float64(parts[4]),
                    'vel-y': np.float64(parts[5]),
                    'vel-z': np.float64(parts[6])
                })

    if len(data) > 0:
        log_callback(f"Parsed {Path(filepath).name} with {len(data)} entries.")

    return pd.DataFrame(data)


def parse_nrt_file(filepath):
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            parts = line.strip().split()
            parts = [item for item in parts if nrt_keep_data(item)]

            if len(parts) < 8:
                continue

            try:
                if (int(parts[6]) != 6):
                    continue

                data.append({
                    'datetime': datetime.strptime(parts[0], "%Y:%j:%H:%M:%S"),
                    'vcdu': int(parts[1]),
                    'num_days': int(parts[2]),
                    'num_ms': int(parts[3]),
                    'num_us_frac': int(parts[4]),
                    'dss_id': int(parts[5]),
                    'bit_rate_code': int(parts[6]),
                    'measured_bit_rate': np.float32(parts[7])
                })
            except (IndexError, ValueError):
                continue

    if len(data) > 0:
        log_callback(f"Parsed {Path(filepath).name} with {len(data)} entries.")

    return pd.DataFrame(data)


def parse_sto_file(filepath, progress_callback=None):
    """
    Parses a generic STO/NRT CSV file into a standardized dataframe.
    Periodically yields progress percentages if a callback is provided.
    """
    data = []
    total_bytes = os.path.getsize(filepath)
    processed_bytes = 0

    with open(filepath, 'r') as f:
        for count, line in enumerate(f):
            processed_bytes += len(line)

            if progress_callback and count % 2500 == 0:
                progress_pct = int((processed_bytes / total_bytes) * 100)
                if progress_pct >= 100:
                    progress_pct = 99

                if progress_callback(progress_pct) is False:
                    log_callback(f"Parsing of {Path(filepath).name} was cancelled by user.")
                    return pd.DataFrame()

            parts = line.strip().split()
            parts = [item for item in parts if nrt_keep_data(item)]

            if len(parts) < 8:
                continue

            try:
                rate_str = str(parts[6]).lower()

                if rate_str not in ["1024", "512k", "256k", "128k"]:
                    continue

                data.append({
                    'datetime': datetime.strptime(parts[0], "%Y:%j:%H:%M:%S"),
                    'vcdu': int(parts[1]),
                    'num_days': int(parts[2]),
                    'num_ms': int(parts[3]),
                    'num_us_frac': int(parts[4]),
                    'dss_id': int(parts[5]),
                    'bit_rate_code': int(parts[6]),
                    'measured_bit_rate': np.float32(parts[7])
                })
            except (IndexError, ValueError):
                continue

        if progress_callback:
            progress_callback(100)

    if len(data) > 0:
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

        if duration_sec >= 120:
            min_start = start_time + pd.Timedelta(minutes=5)
            window_start = min_start.ceil('10min')
            window_end = window_start + pd.Timedelta(minutes=30)
            max_end = end_time - pd.Timedelta(minutes=5)

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
