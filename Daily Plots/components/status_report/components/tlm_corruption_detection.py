"Module to detect telemetry corruption in the AORESZx MSIDs & other MSIDs"
from datetime import timedelta
from dataclasses import dataclass
from tqdm import tqdm
from cxotime import CxoTime
from components.tlm_request import data_request
from components.misc import format_doy


@dataclass
class TLMCorrptionDataPoint:
    "Data class for a telemetry corruption data point."
    date: None
    msid: None
    value: None
    transition: None


def check_attributes(obj):
    "Check if all attributes of an object are not None"
    for attr_name in obj.__dict__:
        if obj.__dict__[attr_name] is None:
            return False
    return True


def aca_corruption_detection(user_vars, msid, bound):
    """
    Description: Generate data for corruption on AORESZx MSIDs
    Input: user variables for dates/times
    Output: none
    """
    data_list= []
    raw_data= data_request(user_vars.ts, user_vars.tp, "SKA High Rate", msid)

    for time, val in zip(raw_data.times, raw_data.vals):
        # Check if MSID value was outside bounds
        if not bound[0] <= val <= bound[1]:
            obc_ts= CxoTime(time) - timedelta(seconds= 5)
            obc_tp= CxoTime(time) + timedelta(seconds= 5)
            obc_subformat_data= data_request(obc_ts, obc_tp, "SKA High Rate", "COTLRDSF")

            for i, (obc_val) in enumerate(obc_subformat_data.vals):
                try:
                    if obc_val == "NORM" and obc_subformat_data.vals[i-1] in ("NONE", "OFFL"):
                        data_point= TLMCorrptionDataPoint(
                                        CxoTime(time).datetime, msid, val,
                                        [obc_subformat_data.vals[i-1], obc_val])
                except IndexError:
                    pass

            if check_attributes(data_point):
                data_list.append(data_point)
                data_point= TLMCorrptionDataPoint(None, None, None, None)

    return data_list


def get_corrupted_datapoints(user_vars, msid, bound):
    """
    Description: Queries data per MSID, then checks for corrupted values against bounds
    Input: User Variables, MSID <str>, Bound <list>
    Output: Dict of corrupted data points, format {MSID,["TIME", "DATA"]}
    """
    data_list= []
    raw_data= data_request(user_vars.ts, user_vars.tp, "SKA High Rate", msid)
    data_point= TLMCorrptionDataPoint(None, None, None, None)

    for val, time in zip(raw_data.vals, raw_data.times):
        # Check if MSID value was outside bound
        if val == bound:
            data_point= TLMCorrptionDataPoint(CxoTime(time).datetime, msid, val, False)

        if check_attributes(data_point):
            data_list.append(data_point)
            data_point= TLMCorrptionDataPoint(None, None, None, None)

    return data_list


def write_corr_report(user_vars, file, corrupted_vals, aca_corrupted_vals, msids_list):
    """
    Description: Write a txt file with tlm corruption findings.
    Input: User Variables <object>, Corrupted values <dict>, MSIDs <list>
    Output: None
    """
    print(" - Generating telemetry corruption report .txt file...")
    line= "-----------------------------"
    counter= 0

    # Format Section Title
    file.write(
        "Detected corrupted telemetry data points for "
        f"{user_vars.year_start}:{format_doy(user_vars.doy_start)} "
        f"thru {user_vars.year_end}:{format_doy(user_vars.doy_end)}\n "
        f"\n{line}{line}{line}\nMSID(s) monitored (Bound)\n")

    # Write the MSID(s) and their bounds
    for (msid, bound) in msids_list[0].items():
        counter += 1
        file.write(f"  {counter}) MSID: {msid}, Bound ({bound})\n")
    for (msid, bound) in msids_list[1].items():
        counter += 1
        file.write(f"  {counter}) MSID: {msid}, Lower Bound ({bound[0]:e}) | "
                   f"Upper Bound {bound[1]:e})\n")
    file.write(f"\n{line}{line}{line}\nMSID(s) with corruption detected:\n")

    # Write the corrupted values
    if len(corrupted_vals) != 0:
        for corrupted_val in corrupted_vals:
            file.write(f"  - ({corrupted_val.date.strftime("%Y:%j:%H:%M:%S:%f")[:-3]}z) "
                       f"{corrupted_val.msid}: {corrupted_val.value}")

    # Write the ACA corrupted values
    if len(aca_corrupted_vals) != 0:
        for corrupted_val in aca_corrupted_vals:
            file.write(f"  - ({corrupted_val.date.strftime("%Y:%j:%H:%M:%S:%f")[:-3]}z) "
                       f"{corrupted_val.msid}: {corrupted_val.value} "
                       f"({corrupted_val.transition[0]} -> {corrupted_val.transition[1]})\n")

    if len(corrupted_vals) == 0 and len(aca_corrupted_vals) == 0:
        file.write("\n  - No corrupted data points found \U0001F63B.\n")

    file.write("\n  ----------END OF TELEMTRY CORRUPTION----------")
    file.write(f"\n{line}{line}{line}{line}{line}\n{line}{line}{line}{line}{line}\n")
    print(" - Done! Data written to TLM corruption section.")


def tlm_corruption_detection(user_vars, file):
    """
    Description: Generate a .txt file with details on telemetry corruption for given MSIDs
    Input: user variables for dates/times
    Output: none
    """
    corrupted_vals, aca_corrupted_vals= ([] for i in range(2))
    msids= {"4ACCACL":"CLOS", "4ACCBCL":"CLOS", "4ACCAOP":"CLOS", "4ACCBOP":"CLOS",
            "4ALL1ALK":"LOCK", "4ALL1BLK":"LOCK", "4ALL1AUL":"LOCK", "4ALL1BUL":"LOCK",
            "4ALL1ACS":"CLOS", "4ALL2ACS":"CLOS", "4ALL1BCS":"CLOS", "4ALL2BCS":"CLOS",
            "4HLL1ACS":"CLOS", "4HLL1AUL":"LOCK", "4HLL1BUL":"LOCK", "4HLL1BLK":"LOCK",
            "4HLL1ALK":"LOCK"}
    aca_msids= {"AORESZ0":[-1e14,1e14], "AORESZ1":[-1e14,1e14],
                "AORESZ2":[-1e14,1e14], "AORESZ3":[-1e14,1e14],
                "AORESZ4":[-1e14,1e14], "AORESZ5":[-1e14,1e14], "AORESZ6":[-1e14,1e14]}

    # ACA MSID TLM Corrpution
    print("\nLooking for corrupted AORESZx datapoints...")
    for msid, bound in tqdm(aca_msids.items(), bar_format= "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        aca_corrupted_vals += aca_corruption_detection(user_vars, msid, bound)

    # All other MSIDs
    print("\nLooking for corrupted datapoints...")
    for msid, bound in tqdm(msids.items(), bar_format= "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        corrupted_vals += get_corrupted_datapoints(user_vars, msid, bound)

    write_corr_report(user_vars, file, corrupted_vals, aca_corrupted_vals, [msids, aca_msids])
