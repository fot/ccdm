"SSR Rollover Detection Module"

from cxotime import CxoTime
from components.data_requests import maude_data_request as maude_data
from components.data_requests import ska_data_request as ska_data


def ssr_rollover_detection(user_vars):
    "ssr rollover detection"
    ssr_rollover_data = get_ssr_rollover_data(user_vars)
    return add_ssr_rollovers(user_vars,ssr_rollover_data)


def get_ssr_rollover_data(user_vars):
    """
    Description: Find datetimes and data points when SSRs rolled over
    Input: User variable dates
    Output: <dict>
    """
    print("SSR Rollover Detection...")
    ssr_data = ska_data(user_vars.ts, user_vars.tp, f"COS{user_vars.ssr_prime[0]}RCEN")
    ssr_times, ssr_values = ssr_data.times, ssr_data.vals
    ssr_rollover_datetimes = {}

    # Shorten data list to only when SSR Prime was not recording
    for index, (time, value) in enumerate(zip(ssr_times, ssr_values)):

        # Detect rollover from prime to backup
        if (ssr_values[index - 1] == "TRUE"
            and value == "FALS"
            and CxoTime(time).strftime("%j") != user_vars.doy_start
            and CxoTime(time).strftime("%j") != user_vars.doy_end
        ):
            ssr_rollover_datetimes.setdefault("Prime to Backup",[]).append(
                CxoTime(time).datetime)

        # Detect rollover from backup to prime (exclude last data point)
        try:
            if (value == "FALS"
                and ssr_values[index + 1] == "TRUE"
                and CxoTime(time).strftime("%j") != user_vars.doy_start
                and CxoTime(time).strftime("%j") != user_vars.doy_end
            ):
                ssr_rollover_datetimes.setdefault("Backup to Prime",[]).append(
                    CxoTime(time).datetime)
        except IndexError: # drop the last data point, can't look at index+1 on last value
            pass

    return ssr_rollover_datetimes


def add_ssr_rollovers(user_vars, rollover_data):
    "Add SSR rollover data to config_section string"
    return_string = ""
    zip_data = zip(rollover_data["Prime to Backup"],
                rollover_data["Backup to Prime"])

    if user_vars.ssr_prime[0] == "A":
        backup = "B"
    else:
        backup = "A"

    if rollover_data:

        for prime_to_backup, backup_to_prime in zip_data:
            rollover_date = prime_to_backup.strftime("%Y:%j:%H:%M:%S.%f")
            recovery_date = backup_to_prime.strftime("%Y:%j:%H:%M:%S.%f")

            # Assemble the final string
            return_string += (
                    f"<li>SSR Rollover from SSR-{user_vars.ssr_prime[0]} "
                    f"to SSR-{backup} on {rollover_date}z</li>")
            print(f"   - SSR Rollover from SSR-{user_vars.ssr_prime[0]} "
                  f"to SSR-{backup} on {rollover_date}")

            return_string += (
                    f"<li>SSR Recovery from SSR-{backup} "
                    f"to SSR-{user_vars.ssr_prime[0]} on {recovery_date}z</li>")
            print(f"   - SSR Recovery from SSR-{backup} "
                  f"to SSR-{user_vars.ssr_prime[0]} on {recovery_date}")

    else:
        print(" - No SSR rollover detected.")

    return_string += "</li></ul></div></div>"
    return return_string
