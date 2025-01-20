"SSR Rollover Detection for use in status_report.py"

import dataclasses
from cxotime import CxoTime
from components.tlm_request import data_request


@dataclasses.dataclass
class SSRRolloverDataPoint:
    "Data class for SSR Rollover Data"
    prime_to_backup: None
    backup_to_prime: None


def ssr_rollover_detection(user_vars, file):
    "ssr rollover detection"
    print(" - SSR Rollover Detection...")
    ssr_rollover_data = get_ssr_rollover_data(user_vars)
    response= "No SSR rollover detected."

    # Write Data to report file
    if user_vars.ssr_prime[0] == "A":
        backup = "B"
    else: backup = "A"

    if ssr_rollover_data:
        for data_item in ssr_rollover_data:
            if (data_item.prime_to_backup is not None) and (data_item.backup_to_prime is not None):
                response= (f"An SSR Rollover occured from SSR-{user_vars.ssr_prime[0]} to "
                           f"SSR-{backup} on {data_item.prime_to_backup}. "
                           f"SSR Recovery occured on {data_item.backup_to_prime}.")
            elif (data_item.prime_to_backup is not None) and (data_item.backup_to_prime is None):
                response= (f"An SSR Rollover occured from SSR-{user_vars.ssr_prime[0]} "
                           f"to SSR-{backup} on {data_item.prime_to_backup} "
                           "and SSR Recovery hasn't occured yet.")
            elif (data_item.prime_to_backup is None) and (data_item.backup_to_prime is not None):
                response= (f"Found a previous SSR Rollover from SSR-{user_vars.ssr_prime[0]} "
                           f"to SSR-{backup} outside of input date/time range, but "
                           f"SSR Recovery occured on {data_item.backup_to_prime}.")
            print(f"   - {response}")
            file.write(f"  - {response}\n")
    else:
        print(f"   - {response}")
        file.write(f"  - {response}\n")


def get_ssr_rollover_data(user_vars):
    """
    Description: Find datetimes and data points when SSRs rolled over
    Input: User variable dates
    Output: <dict>
    """
    ssr_data = data_request(user_vars.ts,user_vars.tp,"SKA Abreviated",
                            f"COS{user_vars.ssr_prime[0]}RCEN")
    data_list= []
    data_point= SSRRolloverDataPoint(None, None)

    # Parse data for SSR record swap on prime SSR
    for index, (time, value) in enumerate(zip(ssr_data.times, ssr_data.vals)):

        # Detect rollover from prime-to-backup & backup-to-prime
        if index != 0:
            if value == "FALS" and ssr_data.vals[index - 1] == "TRUE":
                data_point.prime_to_backup= CxoTime(time).yday
            elif value == "TRUE" and ssr_data.vals[index - 1] == "FALS":
                data_point.backup_to_prime= CxoTime(time).yday

        # Append data_list if last sample w/ partially filled data_point.
        if (index + 1 == len(ssr_data.vals) and
              ((data_point.prime_to_backup is not None) or
              (data_point.backup_to_prime is not None))):
            data_list.append(data_point)
        # Append data_list if data_point fills, then make a new data_point.
        elif data_point.prime_to_backup is not None and data_point.backup_to_prime is not None:
            data_list.append(data_point)
            data_point= SSRRolloverDataPoint(None, None)
        # Append data_list if a backup-to-prime swap occurs before a prime-to-backup swap.
        elif data_point.prime_to_backup is None and data_point.backup_to_prime is not None:
            data_list.append(data_point)
            data_point= SSRRolloverDataPoint(None, None)

    return data_list
