import pandas as pd
import urllib.request
import json
from datetime import datetime, timedelta
from tqdm import tqdm
from dataclasses import dataclass

@dataclass
class MSIDData:
    msid: str
    data: pd.DataFrame 

def maude_data_request(ts, tp, msid):
    """Requests a particular MSID for an interval from MAUDE using urllib"""
    url = ("http://telemetry.cfa.harvard.edu/maude/mrest/"
           f"FLIGHT/msid.json?m={msid}&ts={ts.strftime('%Y%j%H%M%S')}"
           f"&tp={tp.strftime('%Y%j%H%M%S')}&ap=t")
    response = urllib.request.urlopen(url)
    html = response.read()
    return json.loads(html)

def get_data(ts, tp, msids):
    """Synchronous fetching with urllib, vectorized Pandas processing"""
    data = []

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
            data.append(MSIDData(msid, pd.DataFrame(columns=['times', 'values'])))
            continue

        # --- PANDAS VECTORIZATION ---
        df = pd.DataFrame({'times': raw_times_accum, 'values': raw_values_accum})
        
        # Vectorized deduplication and type casting
        df.drop_duplicates(subset=['times'], inplace=True)
        df['times'] = pd.to_datetime(df['times'].astype(str), format='%Y%j%H%M%S%f')
        df['values'] = pd.to_numeric(df['values'])

        df.sort_values(by='times', inplace=True)
        df.reset_index(drop=True, inplace=True)

        data.append(MSIDData(msid, df))

    return data
