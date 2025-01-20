"VCDU Rollover Detection for use in status_report.py"

from datetime import timedelta
from cxotime import CxoTime
from components.tlm_request import data_request


def vcdu_rollover_detection(user_vars, file):
    "Detect VCDU rollovers"
    print(" - VCDU Rollover Detection...")
    vcdu_data= data_request(user_vars.ts,user_vars.tp,"SKA High Rate","CCSDSVCD")

    # Parse the rollover data
    vcdu_rollover_dates= []
    for index, (value, time) in enumerate(zip(vcdu_data.vals, vcdu_data.times)):
        if (value < vcdu_data.vals[index - 1]) and (value < 5):
            vcdu_rollover_dates.append(f"{CxoTime(time).yday}")

    if vcdu_rollover_dates:
        for rollover in vcdu_rollover_dates:
            print(f"   - Found a VCDU rollover on {rollover}.")
            file.write(f"  - A VCDU rollover was detected on {rollover}\n")
    else:
        # Determine the estimated date of next rollover
        vcdus_until_rollover= 16777215 - vcdu_data.vals[-1]
        end_time= CxoTime(vcdu_data.times[-1])
        secs_in_daterange= ((end_time - user_vars.ts).datetime.seconds +
                            ((end_time - user_vars.ts).datetime.days * 86400))
        vcdus_per_sec= secs_in_daterange/(len(vcdu_data.vals))
        time_to_rollover= timedelta(seconds= vcdus_until_rollover * vcdus_per_sec)
        est_rollover_date= (end_time + time_to_rollover).yday

        print(f"   - No VCDU rollover detected. (Estimated rollover: {est_rollover_date})")
        file.write(f"  - No VCDU rollover deteccted. (Estimated rollover: {est_rollover_date})\n")
