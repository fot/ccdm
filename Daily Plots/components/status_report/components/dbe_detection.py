"Module to detect DBE in the SSRs"

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from cxotime import CxoTime
from components.misc import format_doy
from components.status_report.components.limit_detection import (
    get_limit_reports_data)

@dataclass
class BEATData:
    "Dataclass for BEAT Data"
    ssr:       None
    submodule: int
    dbe_count: int
    ts:        None
    tp:        None

    def __init__(self, ssr, submodule, dbe_count, ts, tp):
        self.ssr= ssr
        self.submodule= submodule
        self.dbe_count= dbe_count
        self.ts= ts
        self.tp= tp


def check_attributes(obj):
    "Check if all attributes of an object are not None"
    for attr_name in obj.__dict__:
        if obj.__dict__[attr_name] is None:
            return False
    return True


def get_beat_report_dirs(user_vars):
    "Generate list of beat report files"
    print(" - Building SSR beat report directory list...")
    full_file_list, file_list= ([] for i in range(2))

    start_date= datetime.strptime(
        f"{user_vars.year_start}:{user_vars.doy_start}:000000","%Y:%j:%H%M%S")
    end_date= datetime.strptime(
        f"{user_vars.year_end}:{user_vars.doy_end}:235959","%Y:%j:%H%M%S")
    root_folder= ("/share/FOT/engineering/ccdm/Current_CCDM_Files/"
                  "Weekly_Reports/SSR_Short_Reports/")

    for year_diff in range((end_date.year-start_date.year) + 1):
        year= start_date.year + year_diff
        dir_path= Path(root_folder + "/" + str(year))
        full_file_list_path= list(x for x in dir_path.rglob('BEAT*.*'))

        for list_item in full_file_list_path:
            full_file_list.append(str(list_item))

    for day in range((end_date-start_date).days + 1):
        cur_day= start_date + timedelta(days=day)
        cur_year_str= cur_day.year
        cur_day_str= cur_day.strftime("%j")

        for list_item in full_file_list:
            if f"BEAT-{cur_year_str}{cur_day_str}" in list_item:
                file_list.append(list_item)

    return file_list


def parse_beat_report(beat_dir, user_vars):
    """
    Description: Parse a BEAT file
    Input: BEAT file directory path
    Output: Two dicts
    """
    data_point= BEATData(None,None,None,None,None)

    with open(beat_dir, 'r', encoding= "utf-8") as file:
        cur_state, data_list= "FIND_SSR", []
        for line in file:
            if cur_state == "FIND_SSR":
                if line[0:5] == "SSR =":
                    data_point.ssr= line[6]
                    cur_state= "FIND_SUBMOD"
            elif cur_state == "FIND_SUBMOD":
                if line[0:7] == "SubMod ":
                    cur_state= "REC_SUBMOD"
            elif cur_state == "REC_SUBMOD":
                if line[0].isdigit():
                    split_line= line.split()
                    data_point.submodule= int(split_line[0])
                    data_point.dbe_count= int(split_line[3])
                    data_point.ts=        CxoTime(split_line[4]).datetime
                    data_point.tp=        CxoTime(split_line[5]).datetime
                else:
                    cur_state = 'FIND_SSR'

            # Append data_list if data_point fills up.
            if ((check_attributes(data_point)) and (data_point.ts <= user_vars.tp)):
                data_list.append(data_point)
                data_point= BEATData(data_point.ssr,None,None,None,None)
        file.close()

    return data_list


def write_double_bit_errors(user_vars, dbe_data_list, file):
    "Write data parsed from BEAT reports into output file."
    previous_doy= None # Init previous day of year
    limit_reports= get_limit_reports_data(user_vars)

    # Write header info
    file.write(
        f"Detected DBEs for {user_vars.year_start}:{format_doy(user_vars.doy_start)} "
        f"thru {user_vars.year_end}:{format_doy(user_vars.doy_end)}\n\n" + ("-" * 87))

    if len(dbe_data_list) != 0:
        for data_point in dbe_data_list:
            current_doy= data_point.ts.strftime("%Y:%j")
            start_time= f'{data_point.ts.strftime("%H:%M:%S")}z'
            end_time= f'{data_point.tp.strftime("%H:%M:%S")}z'
            entry_string= (
                f"  - ({start_time} thru {end_time}) SSR-{data_point.ssr} | "
                f"submodule: {data_point.submodule} | DBEs: {data_point.dbe_count}")

            # Check for limit violations during DBE timeframe
            for limit_report in limit_reports:
                if data_point.ts <= limit_report.date <= data_point.tp:
                    entry_string += " ***Limit Violation Detected in Timeframe!***"
                    break

            # Add entry header if new day of year. Also write entry
            if current_doy != previous_doy:
                file.write(f"\nDBEs for {current_doy}:\n")
            file.write(f"{entry_string}\n")

            # Save previous_day for the next iteration
            previous_doy= current_doy
    else:
        file.write("\n  - No DBEs detected for the selected date/time range \U0001F63B.\n")


def get_beat_report_data(user_vars):
    "Parse SSR beat reports into data"
    print(" - Parsing SSR beat report data...")
    data_points, dbe_data_list= ([] for i in range(2))
    beat_report_dirs= get_beat_report_dirs(user_vars)

    for beat_report in beat_report_dirs:
        try:
            data_points= parse_beat_report(beat_report, user_vars)
        except FileNotFoundError:
            print(f"""     - Error parsing file "{beat_report[-34:]}"! Skipping file...""")

        for data_point in data_points:
            if data_point not in dbe_data_list:
                dbe_data_list.append(data_point)

    return dbe_data_list


def dbe_detection(user_vars, file):
    "Pull DBEs from BEAT files to populate into report file."
    print("\nAdding DBE data...")
    
    # Pulling and writing Double Bit Error Data
    dbe_data_list= get_beat_report_data(user_vars)

    # Write all DBE data to file
    write_double_bit_errors(user_vars, dbe_data_list, file)

    file.write("\n  ----------END OF DBE DETECTION----------")
    file.write("\n" + ("-" * 145) + "\n" + ("-" * 145) + "\n")
    print(""" - Done! Data written to "DBE section".""")
