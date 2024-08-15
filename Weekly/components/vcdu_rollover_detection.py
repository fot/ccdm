"VCDU Rollover Detection"

from cxotime import CxoTime
from components.data_requests import ska_data_request as ska_data


def vcdu_rollover_detection(user_vars):
    "Detect VCDU rollovers"
    print("VCDU Rollover Detection...")
    vcdu_data = ska_data(user_vars.ts,user_vars.tp,"CCSDSVCD")
    vcdu_rollover_date = get_vcdu_rollover(vcdu_data)

    if vcdu_rollover_date:
        vcdu_rollover_string = f"""<li>VCDU rollover detected on {vcdu_rollover_date}z.</li>"""
    else:
        vcdu_rollover_string = None

    return vcdu_rollover_string if vcdu_rollover_string else None


def get_vcdu_rollover(vcdu_data):
    "Parse vcdu_data and locate a VCDU rollover if it occured."
    for index, (value, time) in enumerate(zip(vcdu_data.vals, vcdu_data.times)):
        # if (value < vcdu_data.vals[index - 1]) and (index > 0) and (value <= 10000):
        if (value < vcdu_data.vals[index - 1]) and (index > 0):
            date = CxoTime(time)
            vcdu_rollover_date = f"{date.yday}"
            break
        vcdu_rollover_date = None

    if vcdu_rollover_date:
        print(f"   - Found a VCDU rollover on {vcdu_rollover_date}.")
    else:
        print("   - No VCDU rollover detected.")

    return vcdu_rollover_date
