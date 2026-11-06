import pandas as pd
import urllib.request
import json
from datetime import datetime, timedelta
from tqdm import tqdm


def maude_data_request(ts, tp, msid):
    """Requests a particular MSID for an interval from MAUDE using urllib"""
    url = ("http://telemetry.cfa.harvard.edu/maude/mrest/"
           f"FLIGHT/msid.json?m={msid}&ts={ts.strftime('%Y%j%H%M%S')}"
           f"&tp={tp.strftime('%Y%j%H%M%S')}&ap=t")
    response = urllib.request.urlopen(url)
    html = response.read()
    return json.loads(html)


def get_data(ts, tp, msids):
    """Synchronous fetching with urllib, returning a single time-unified DataFrame"""
    dfs = []

    for msid in tqdm(msids):
        raw_times_accum = []
        raw_values_accum = []
        shift_time = timedelta(0)

        # Collect Data
        while True:
            raw_data = maude_data_request(ts + shift_time, tp, msid)

            chunk_times = raw_data.get('data-fmt-1', {}).get('times', [])
            chunk_values = raw_data.get('data-fmt-1', {}).get('values', [])

            if not chunk_times:
                break

            # Accumulate raw strings instantly without inner-loop logic
            raw_times_accum.extend(chunk_times)
            raw_values_accum.extend(chunk_values)

            # Parse ONLY the last timestamp to manage the loop logic
            last_time_str = str(chunk_times[-1])
            last_time_dt = datetime.strptime(last_time_str, "%Y%j%H%M%S%f")
            new_shift_time = last_time_dt - ts

            if last_time_dt >= tp or new_shift_time <= shift_time:
                break

            shift_time = new_shift_time

        # Handle edge case where no data was returned for the entire MSID
        if not raw_times_accum:
            continue

        # --- PANDAS VECTORIZATION ---
        col_name = msid.lower()
        df = pd.DataFrame({'datetime': raw_times_accum, col_name: raw_values_accum})

        # Vectorized deduplication and type casting
        df.drop_duplicates(subset=['datetime'], inplace=True)
        df['datetime'] = pd.to_datetime(df['datetime'].astype(str), format='%Y%j%H%M%S%f')
        df[col_name] = pd.to_numeric(df[col_name])

        # Set datetime as the index so pd.concat can auto-align all MSIDs perfectly
        df.set_index('datetime', inplace=True)
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    # Concatenate all individual MSID DataFrames side-by-side using the DatetimeIndex
    merged_df = pd.concat(dfs, axis=1)

    # Sort chronologically, forward fill missing values across the unified timeline, and extract index
    merged_df.sort_index(inplace=True)
    merged_df.ffill(inplace=True)
    merged_df.reset_index(inplace=True)

    return merged_df
