"""
Spurious Command Lock Detection v1.1
 - Updated to adjust parsing of DSN comms to include day before/after date range
 - Updated to filter out data from 45min before/after an expected comm.
"""

from datetime import datetime, timedelta
from cxotime import CxoTime
from components.data_requests import maude_data_request as maude_data
from components.misc import format_wk


def parse_dsn_comms(user_vars):
    "Parse the inputted file directory of DSN comms to look for Chandra comms."
    print(" - Parsing DSN Comm files...")
    dsn_comm_times, dsn_comm_dirs = ([] for i in range(2))
    dsn_comm_base_dirs = "/home/mission/MissionPlanning/DSN/DSNweek/"
    date_range = []
    date_diff = user_vars.tp.datetime - user_vars.ts.datetime

    # Build file list to parse.
    for wk in range(1,53):
        dsn_comm_dirs.append(
            dsn_comm_base_dirs + f"{user_vars.start_year}_wk{format_wk(wk)}_all.txt")

    for value in range(date_diff.days + 3):
        date_value = (timedelta(-1) + user_vars.ts + value).strftime("%j")
        date_range.append(date_value)

    for dsn_comm in dsn_comm_dirs:
        try:
            with open(dsn_comm, "r", encoding="utf-8") as comm_file:
                for line in comm_file:
                    if "CHDR" in line:
                        split_line = line.split()
                        boa_time = datetime.strptime(split_line[3], "%Y:%j:%H:%M:%S.%f")
                        eoa_time = datetime.strptime(split_line[5], "%Y:%j:%H:%M:%S.%f")
                        if boa_time.strftime("%j") in date_range:
                            per_pass = [boa_time - timedelta(hours=0.75),
                                        eoa_time + timedelta(hours=0.75)]
                            dsn_comm_times.append(per_pass)
        except FileNotFoundError:
            print(f"""   - File: "{dsn_comm}" not found in base directory, skipping file...""")

    return dsn_comm_times


def spurious_cmd_lock_detection(user_vars):
    "Detect if a spurious command lock occured in date/time range"
    print("Spurious Command Lock Detection.")
    dsn_comm_times = parse_dsn_comms(user_vars)
    spurious_cmd_locks = {}

    for receiver in ("A","B"):
        print(f" - Checking for Receiver-{receiver} lock...")
        receiver_data = maude_data(user_vars.ts, user_vars.tp, f"CCMDLK{receiver}")
        values = receiver_data["data-fmt-1"]["values"]
        times =  receiver_data["data-fmt-1"]["times"]
        locked_times = []

        for time, value in zip(times, values):
            if value == "0":
                locked_times.append(CxoTime(time, format="maude").datetime)

        for locked_time in locked_times:
            value_out_of_comm = []

            for expected_comm in dsn_comm_times:
                if not expected_comm[0] < locked_time < expected_comm[1]:
                    value_out_of_comm.append(True)
                else:
                    value_out_of_comm.append(False)

            if all(i for i in value_out_of_comm):
                spurious_cmd_locks.setdefault(f"{receiver}",[]).append(locked_time)
                print(f"   - Spurious Command Lock on Receiver-{receiver} "
                      f"""found at "{locked_time.strftime("%Y:%j:%H:%M:%S.%f")}z".""")

    return spurious_cmd_locks


def write_spurious_cmd_locks(spurious_cmd_locks):
    """
    Description: Add all the spurious cmd locks the perf_health_section string
    Input: spurious_cmd_locks <dict>
    Ouput: Modified perf_health_section <str>
    """
    print("   - Writing Spurious CMD Locks...")
    return_string = ""
    for receiver, date_list in spurious_cmd_locks.items():
        for date in date_list:
            date_time = date.strftime("%Y:%j:%H:%M:%S.%f")
            if receiver:
                return_string += (
                    f"<li>Spurious Command Lock found on Receiver-{receiver} "
                    f"""at {date_time}z</li>\n""")
    return_string += "</ul>"
    return return_string
