"""Module to detect telemetry corruption in the AORESZx MSIDs & other MSIDs"""

from datetime import timedelta
import pandas as pd
from tqdm import tqdm
from cxotime import CxoTime
from components.tlm_request import data_request
from components.misc import format_doy


def aca_corruption_detection(user_vars, msid, bound):
    """
    Description: Generate data for corruption on AORESZx MSIDs
    Input: user variables for dates/times
    Output: List of dictionaries containing corruption data
    """
    data_list = []
    raw_data = data_request(user_vars.ts, user_vars.tp, "SKA High Rate", msid)

    for time, val in zip(raw_data.times, raw_data.vals):
        # Trigger event if the value is out of bounds
        if not bound[0] <= val <= bound[1]:
            cxo_time = CxoTime(time)
            obc_ts = cxo_time - timedelta(seconds=5)
            obc_tp = cxo_time + timedelta(seconds=5)

            # Request subformat context
            obc_subformat_data = data_request(obc_ts, obc_tp, "SKA High Rate", "COTLRDSF")
            vals = obc_subformat_data.vals
            sub_times = obc_subformat_data.times

            # Default transition state
            found_transition = None

            # Look for a transition specifically at the corruption timestamp
            for i in range(1, len(vals)):
                obc_val = vals[i]
                prev_val = vals[i-1]

                # Check if a state change occurred
                if obc_val != prev_val:
                    # Convert the subformat timestamp to match the datetime format
                    transition_time = CxoTime(sub_times[i]).datetime

                    # Lock in the transition only if it happens at the exact moment of corruption
                    if transition_time == cxo_time.datetime:
                        found_transition = [prev_val, obc_val]
                        break

            # Log the corruption event
            data_list.append({
                "date": cxo_time.datetime,
                "msid": msid,
                "value": val,
                "transition": found_transition
            })

    return data_list


def get_corrupted_datapoints(user_vars, msid, bound):
    """
    Description: Queries data per MSID, then checks for corrupted values against bounds
    Input: User Variables, MSID <str>, Bound <list>
    Output: List of dictionaries containing corruption data
    """
    data_list = []
    raw_data = data_request(user_vars.ts, user_vars.tp, "SKA High Rate", msid)

    for val, time in zip(raw_data.vals, raw_data.times):
        if val == bound:
            data_list.append({
                "date": CxoTime(time).datetime,
                "msid": msid,
                "value": val,
                "transition": None
            })

    return data_list


def write_corr_report(user_vars, file, df_corrupted, msids_list):
    """
    Description: Write a txt file with tlm corruption findings sorted by date.
    Input: User Variables <object>, Pandas DataFrame of corrupted values, MSIDs <list>
    Output: None
    """
    print(" - Generating telemetry corruption report .txt file...")
    counter = 0

    file.write(
        "Detected corrupted telemetry data points for "
        f"{user_vars.year_start}:{format_doy(user_vars.doy_start)} "
        f"thru {user_vars.year_end}:{format_doy(user_vars.doy_end)}\n "
        f"\n{'-' * 89}\nMSID(s) monitored (Bound)\n"
    )

    for (msid, bound) in msids_list[0].items():
        counter += 1
        file.write(f"  {counter}) MSID: {msid}, Bound ({bound})\n")
    for (msid, bound) in msids_list[1].items():
        counter += 1
        file.write(f"  {counter}) MSID: {msid}, Lower Bound ({bound[0]:e}) | "
                   f"Upper Bound ({bound[1]:e})\n")

    file.write(f"\n{'-' * 89}\nMSID(s) with corruption detected:\n")

    if df_corrupted.empty:
        file.write("\n  - No corrupted data points found \U0001F63B.\n")
    else:
        # Iterate efficiently through the sorted Pandas DataFrame
        for row in df_corrupted.itertuples(index=False):
            date_str = row.date.strftime('%Y:%j:%H:%M:%S:%f')[:-3]

            # Combine msid and colon, then pad to 10 characters left-aligned (:<10)
            msid_str = f"{row.msid}:"

            # Pad the value to 26 characters left-aligned (:<26) to accommodate long floats
            # The base string now acts as a perfectly aligned row
            base_str = f"  - ({date_str}z) {msid_str:<8} {str(row.value):<22}"

            # Append transition context if it exists
            if isinstance(row.transition, list):
                file.write(f"{base_str} ({row.transition[0]} -> {row.transition[1]})\n")
            else:
                file.write(f"{base_str}\n")

    file.write("\n  ----------END OF TELEMETRY CORRUPTION----------")
    file.write(f"\n{'-' * 145}\n{'-' * 145}\n")
    print(" - Done! Data written to TLM corruption section.")


def tlm_corruption_detection(user_vars, file):
    """
    Description: Generate a .txt file with details on telemetry corruption for given MSIDs
    """
    corrupted_vals, aca_corrupted_vals = [], []

    msids = {"4ACCACL":"CLOS", "4ACCBCL":"CLOS", "4ACCAOP":"CLOS", "4ACCBOP":"CLOS",
             "4ALL1ALK":"LOCK", "4ALL1BLK":"LOCK", "4ALL1AUL":"LOCK", "4ALL1BUL":"LOCK",
             "4ALL1ACS":"CLOS", "4ALL2ACS":"CLOS", "4ALL1BCS":"CLOS", "4ALL2BCS":"CLOS",
             "4HLL1ACS":"CLOS", "4HLL1AUL":"LOCK", "4HLL1BUL":"LOCK", "4HLL1BLK":"LOCK",
             "4HLL1ALK":"LOCK"}

    aca_msids = {"AORESZ0":[-1e07,1e07], "AORESZ1":[-1e07,1e07],
                 "AORESZ2":[-1e07,1e07], "AORESZ3":[-1e07,1e07],
                 "AORESZ4":[-1e07,1e07], "AORESZ5":[-1e07,1e07], "AORESZ6":[-1e07,1e07]}

    print("\nLooking for corrupted AORESZx datapoints...")
    for msid, bound in tqdm(aca_msids.items(), bar_format="{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        aca_corrupted_vals.extend(aca_corruption_detection(user_vars, msid, bound))

    print("\nLooking for corrupted datapoints...")
    for msid, bound in tqdm(msids.items(), bar_format="{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        corrupted_vals.extend(get_corrupted_datapoints(user_vars, msid, bound))

    # Convert the unified list of dictionaries into a Pandas DataFrame
    all_data = corrupted_vals + aca_corrupted_vals
    df_corrupted = pd.DataFrame(all_data)

    # Sort chronologically (if the DataFrame isn't empty)
    if not df_corrupted.empty:
        df_corrupted.sort_values(by="date", inplace=True)

    write_corr_report(user_vars, file, df_corrupted, [msids, aca_msids])
