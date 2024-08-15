"SCS 107 Detection for CCDM Weekly"

from cxotime import CxoTime
from components.data_requests import ska_data_request as ska_data


def scs107_detection(user_vars):
    "Base method for SCS107 Detection"
    print("SCS 107 Detection...")
    scs107s = get_scs107s(user_vars)
    scs107s_string = gen_scs107s_string(scs107s)
    return scs107s_string if scs107s_string else None


def get_scs107s(user_vars):
    "Search SCS107 state data for if SCS107 was run"
    data = ska_data(user_vars.ts,user_vars.tp, "COSCS107S", True)
    all_times, return_data = [], []

    for data_point, time in zip(data.vals, data.times):
        if data_point == "DISA":
            corrected_time = CxoTime(time).datetime
            all_times.append(corrected_time)

    try:
        return_data = [all_times[0], all_times[len(all_times) - 1]]
    except IndexError:
        return_data = None

    return return_data


def gen_scs107s_string(scs107s):
    "Write found SCS107s if found."
    if scs107s:
        start_datetime = scs107s[0].strftime("%Y:%j %H:%M:%S.%f")
        end_datetime = scs107s[1].strftime("%Y:%j %H:%M:%S.%f")
        return_string = (
            f"""<li>SCS 107 ran on {start_datetime}z and was """
            f"""re-enabled on {end_datetime}z.</li>""")
        print(f"   - A run of SCS107 detected on {start_datetime}z "
              f"with SCS107 being re-enabled on {end_datetime}z.")
    else:
        return_string = None
        print("   - No run of SCS107 detected.")

    return return_string if return_string else None
