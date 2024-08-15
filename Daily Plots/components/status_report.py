"Generate the Status Report"

import itertools as it
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
from cxotime import CxoTime
from components.misc import make_output_dir
from components.tlm_request import data_request


def generate_status_report(user_vars, auto_gen = False):
    "write the status report file"
    print(" - Generating CCDM status report .txt file...")
    set_dir = make_output_dir(user_vars, auto_gen)

    if auto_gen:
        file_title = "CCDM Status Report (Auto-Gen 14-Day Lookback).txt"
    else:
        file_title = (
            f"CCDM Status Report ({user_vars.year_start}{user_vars.doy_start}_"
            f"{user_vars.year_end}{user_vars.doy_end}).txt"
        )

    with open(set_dir + file_title, "w+", encoding = "utf-8") as file:
        tlm_corruption_detection(user_vars, file)
        obc_error_detection(user_vars, file)
        limit_violation_detection(user_vars, file)

    print(f"""Done! Data written to "{file_title}" in "{set_dir}".""")


def tlm_corruption_detection(user_vars, file):
    """
    Description: Generate a .txt file with details on telemetry corruption for given MSIDs
    Input: user variables for dates/times
    Output: none
    """
    print("\nLooking for corrupted datapoints...")
    corrupted_values = {}
    msids = {
        "AORESZ0":["1e14","-1e14"], "AORESZ1":["1e14","-1e14"], 
        "AORESZ2":["1e14","-1e14"], "AORESZ3":["1e2","-1e14"],
        "AORESZ4":["1e14","-1e14"], "AORESZ5":["1e2","-1e14"], "AORESZ6":["1e14","-1e14"],
        "4ACCACL":["CLOS"], "4ACCBCL":["CLOS"], "4ACCAOP":["CLOS"], "4ACCBOP":["CLOS"],
        "4ALL1ALK":["LOCK"], "4ALL1BLK":["LOCK"], "4ALL1AUL":["LOCK"], "4ALL1BUL":["LOCK"],
        "4ALL1ACS":["CLOS"], "4ALL2ACS":["CLOS"], "4ALL1BCS":["CLOS"], "4ALL2BCS":["CLOS"],
        "4HLL1ACS":["CLOS"], "4HLL1AUL": ["LOCK"], "4HLL1BUL": ["LOCK"], "4HLL1BLK": ["LOCK"],
        "4HLL1ALK": ["LOCK"],
        }
    for msid, bound in tqdm(msids.items()):
        corrupted_values[f"{msid}"] = get_corrupted_datapoints(user_vars, msid, bound)

    write_corr_report(user_vars, file, corrupted_values, msids)


def get_corrupted_datapoints(user_vars, msid, bound):
    """
    Description: Queries data per MSID, then checks for corrupted values against bounds
    Input: User Variables, MSID <str>, Bound <list>
    Output: Dict of corrupted data points, format {MSID,["TIME", "DATA"]}
    """
    corrupted_values, org_data_source = {}, user_vars.data_source
    user_vars.data_source = "SKA High Rate" # Want all data points
    raw_data = data_request(user_vars, msid)
    user_vars.data_source = org_data_source # Restore to what it was

    for data_point, time_point in zip(raw_data.vals, raw_data.times):
        try:
            if float(bound[0]) <= data_point or data_point <= float(bound[1]):
                corrupted_values[CxoTime(time_point)] = data_point
        except ValueError:
            if data_point in (bound):
                corrupted_values[CxoTime(time_point)] = data_point

    return corrupted_values


def write_corr_report(user_vars, file, corrupted_values, msids):
    """
    Description: Write a txt file with tlm corruption findings.
    Input: User Variables <object>, Corrupted values <dict>, MSIDs <list>
    Output: None
    """
    print(" - Generating telemetry corruption report .txt file...")
    line = "-----------------------------"
    length_list = []

    for item in corrupted_values.values():
        length_list.append(len(item))

    file.write(
        "Detected corrupted telemetry data points for "
        f"{user_vars.year_start}:{user_vars.doy_start} "
        f"thru {user_vars.year_end}:{user_vars.doy_end}\n" +
        "\n" + line + line + line + "\n"
    )
    file.write("MSID(s) monitored (Bound)\n")
    for index, (msid, bound) in enumerate(msids.items()):
        try:
            file.write(
                f"  {index + 1}) MSID: {msid}, Upper Bound ({bound[0]}) "
                f"| Lower Bound ({bound[1]})\n"
                )
        except IndexError:
            file.write(f"  {index + 1}) MSID: {msid}, Bound ({bound[0]})\n")
    file.write("\n" + line + line + line + "\n")
    file.write("MSID(s) with corruption detected:\n")
    if not all([i == 0 for i in length_list]):
        for msid in corrupted_values:
            if len(corrupted_values[f"{msid}"]) != 0:
                file.write(
                    f"""  • MSID: "{msid}" had {len(corrupted_values[f"{msid}"])} """
                    "corrupted data points...\n"
                    )
                for index, (time_item, data) in enumerate(corrupted_values[f"{msid}"].items()):
                    file.write(
                        f"   {index + 1}) {time_item.strftime('%Y:%j %H:%M:%S.%f')}z  |  {data}\n")
    else:
        file.write("  • No corrupted data points found \U0001F63B.\n")

    file.write("\n  ----------END OF TELEMTRY CORRUPTION----------")
    file.write("\n" +line+line+line+line+line + "\n" +line+line+line+line+line + "\n")
    print(" - Done! Data written to TLM corruption section.")


def obc_error_detection(user_vars, file):
    """
    Description: Add dbe error data to plot
    Input: Data Object, figure
    Output: None
    """
    print("\nAdding OBC Error Data...")
    file_list = get_obc_report_dirs(user_vars)
    report_data = get_obc_error_reports(file_list)
    write_obc_error_report(user_vars, file, report_data)


def get_obc_report_dirs(user_vars):
    "Generate list of OBC error report files"
    print(" - Building OBC Error Log report directory list...")
    start_date = datetime.strptime(
        f"{user_vars.year_start}:{user_vars.doy_start}:000000","%Y:%j:%H%M%S"
        )
    end_date = datetime.strptime(
        f"{user_vars.year_end}:{user_vars.doy_end}:235959","%Y:%j:%H%M%S"
        )
    root_folder = (
        "/share/FOT/engineering/flight_software/OBC_Error_Log_Dumps"
        )
    full_file_list, file_list = ([] for i in range(2))
    for year_diff in range((end_date.year - start_date.year) + 1):
        year = start_date.year + year_diff
        dir_path = Path(root_folder + "/" + str(year))
        full_file_list_path = list(x for x in dir_path.rglob('SMF_ERRLOG*.*'))

        for list_item in full_file_list_path:
            full_file_list.append(str(list_item))

    for day in range((end_date - start_date).days + 1):
        cur_day = start_date + timedelta(days=day)
        cur_year_str = cur_day.year
        cur_day_str = cur_day.strftime("%j")

        for list_item in full_file_list:
            if f"SMF_ERRLOG_0164_{cur_year_str}{cur_day_str}" in list_item:
                file_list.append(list_item)
    return file_list


def get_obc_error_reports(file_list):
    "Parse OBC error reports into data"
    print(" - Parsing OBC Error reports...")
    per_report_data, report_data, formatted_data = ({} for i in range(3))

    for file_dir in tqdm(file_list):
        per_report_data = parse_obc_report(file_dir)
        report_data.update(per_report_data)

    for date_time, data in report_data.items():
        formatted_data.setdefault(date_time,[]).append({date_time:data})

    return formatted_data


def parse_obc_report(file_dir):
    """
    Description: Parse OBC error report
    """
    data_dict = {}
    with open(file_dir, 'r', encoding="utf-8") as obc_error:
        for index, (line) in enumerate(obc_error):
            if index in it.chain(range(6,38), range(45,77)): # Only parse error lines 1-32 & 33-64
                parsed = line.split()
                try:
                    date = datetime.strptime(parsed[1],"%Y%j:%H%M%S")
                    error_type = parsed[7]
                    try:
                        error = f"{parsed[8]} {parsed[9]} {parsed[10]} {parsed[11]}"
                    except BaseException:
                        error = f"{parsed[8]}"
                    data_dict.setdefault(date,[]).append({f"{error_type}":f"{error}"})
                except BaseException:
                    pass
    return data_dict


def write_obc_error_report(user_vars, file, report_data):
    """
    Description: Write txt file of OBC Errors found.
    Input: Data <dict>
    Output: None
    """
    line = "-----------------------------"
    file.write(
        f"Detected OBC Errors for {user_vars.year_start}:{user_vars.doy_start} thru "
        f"{user_vars.year_end}:{user_vars.doy_end}\n" +
        "\n" + line + line + line + "\n"
    )
    if report_data:
        write_obc_errors(report_data, file)
    else:
        file.write("No OBC Errors detected for the selected date/time range \U0001F63B.\n\n")

    file.write("  ----------END OF OBC ERRORS----------")
    file.write("\n" +line+line+line+line+line + "\n" +line+line+line+line+line + "\n")
    print(" - Done! Data written to OBC error section.")


def write_obc_errors(report_data, file):
    """
    Description: Write the OBC errors from a formatted dict
    Input: Report data, and file object
    Output: None
    """
    for date, data in report_data.items():
        file.write(f'OBC Errors for {date.strftime("%Y:%j")}:\n')
        for dict_list in data:
            for date_time, type_error_dict_list in dict_list.items():
                for type_error in type_error_dict_list:
                    for error_type, error in type_error.items():
                        item_time = date_time.strftime("%H:%M:%S")
                        file.write(
                            f' • ({item_time}z) Error Type:"{error_type}"'
                            f'  |  Error:"{error}"\n'
                        )
        file.write("\n")


def format_doy(doy_no_format):
    "Format the timetuple into a 3 digit string"
    if len(doy_no_format) == 3:
        doy_formatted = doy_no_format
    elif len(doy_no_format) == 2:
        doy_formatted = f"0{doy_no_format}"
    elif len(doy_no_format) == 1:
        doy_formatted = f"00{doy_no_format}"
    return doy_formatted


def limit_violation_detection(user_vars, file):
    """
    Description: Generate txt info file of limit violations
    Input: user_vars
    Output: None
    """
    print("\nGenerating Limit Violation .txt file...")
    limit_dir_list = get_limit_report_dirs(user_vars)
    limit_data = get_limit_reports(limit_dir_list)
    write_limit_report_file(user_vars, file, limit_data)


def get_limit_report_dirs(user_vars):
    "Generate list of limits.txt report files"
    print(" - Building OBC Error Log report directory list...")
    start_date = datetime.strptime(
        f"{user_vars.year_start}:{user_vars.doy_start}:000000","%Y:%j:%H%M%S"
        )
    end_date = datetime.strptime(
        f"{user_vars.year_end}:{user_vars.doy_end}:235959","%Y:%j:%H%M%S"
        )
    root_folder = "/share/FOT/engineering/reports/dailies/"
    directory_list = []
    date_diff = timedelta(days=(end_date-start_date).days)

    for date_range in range(date_diff.days + 1):
        current_date = start_date + timedelta(date_range)
        year = current_date.year
        month = current_date.strftime("%b")
        day = current_date.strftime("%d")
        doy = format_doy(str(current_date.timetuple().tm_yday))
        dir_path = Path(
            f"{root_folder}/{year}/{month.upper()}/{month.lower()}{day}_{doy}/limits.txt")
        directory_list.append(dir_path)

    return directory_list


def get_limit_reports(file_list):
    "Parse limit reports into data"
    print(" - Parsing Limit reports...")
    per_report_data, report_data, formatted_data = ({} for i in range(3))

    for file_dir in tqdm(file_list):
        per_report_data = parse_limit_report(file_dir)
        report_data.update(per_report_data)

    for date_time, data in report_data.items():
        date = str(date_time.strftime("%Y:%j"))
        formatted_data.setdefault(date,[]).append({date_time:data})

    return formatted_data


def parse_limit_report(file_dir):
    """
    Description: Parse limit error report
    """
    data_dict = {}
    filtered_msids = ["CTUDWLMD"]

    try:
        with open(file_dir, 'r', encoding="utf-8") as limit_file:
            for line in limit_file:
                parsed = line.split()
                msid, status = parsed[2], parsed[3]
                if ((msid.startswith("C") or msid.startswith("PA_")) and
                    status != 'NOMINAL' and (msid not in filtered_msids)
                    ):
                    data_dict.setdefault(
                        datetime.strptime(parsed[0],"%Y%j.%H%M%S"),[]).append(parsed[1:])
    except OSError:
        print(f""" - Error! File "{file_dir}" did not exist, will skip this file...""")

    return data_dict


def write_limit_report_file(user_vars, file, report_data):
    """
    Description: Write txt file of limit violations found.
    Input: Data <dict>
    Output: None
    """
    line = "-----------------------------"
    file.write(
        f"Detected CCDM limit violations for {user_vars.year_start}:{user_vars.doy_start} "
        f"thru {user_vars.year_end}:{user_vars.doy_end}\n\n" + line + line + line + "\n")
    if report_data:
        write_limit_violations(report_data, file)
    else:
        file.write("No Limit Violations detected for the selected date/time range \U0001F63B.")

    file.write("  ----------END OF LIMIT VIOLATIONS----------")
    file.write("\n" +line+line+line+line+line + "\n" +line+line+line+line+line + "\n")
    print(""" - Done! Data written to "limit violation section".""")


def write_limit_violations(report_data, file):
    """
    Description: Write the limit violations from a formatted dict
    Input: Report data, and file object
    Output: None
    """
    for date, data_dict_list in report_data.items():
        file.write(f'CCDM limit violations for {date}:\n')
        for data_dict in data_dict_list:
            for date_time, data_list in data_dict.items():
                for list_item in data_list:
                    time = date_time.strftime("%H:%M:%S")
                    try:
                        msid, error = list_item[1], list_item[2]
                        state, e_state = list_item[3], list_item[5]
                        file.write(
                            f'  - ({time} EST) MSID "{msid}", was "{error}" with a measured value '
                            f'of "{state}" with an expected state of "{e_state}".\n')
                    except BaseException:
                        if list_item[1] == "COTHIRTD": # MSID COTHIRTD has a different format
                            msid, error, state = list_item[1],list_item[2],list_item[4]
                            file.write(
                                f'  - ({time} EST) MSID "{msid}", was "{error}" with a measured'
                                f' value of "{state}" with an expected state of "<BLANK>".\n')
        file.write("\n")
