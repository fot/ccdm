"Generate the Status Report"

import dataclasses
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
from cxotime import CxoTime
from components.misc import make_output_dir, format_wk, format_doy
from components.tlm_request import data_request
from components.status_report.components.spurious_cmd_lock_detection import (
    spurious_cmd_lock_detection)
from components.status_report.components.vcdu_rollover_detection import (
    vcdu_rollover_detection)
from components.status_report.components.ssr_rollover_detection import (
    ssr_rollover_detection)
from components.status_report.components.sequencer_selftest_detection import (
    sequencer_selftest_detection)
from components.status_report.components.scs107_detection import scs107_detection


@dataclasses.dataclass
class BEATData:
    "Data class for BEAT data"
    file_list: list
    dbe_data: list

@dataclasses.dataclass
class BEATDataPoint:
    "Data class for a BEAT report data point."
    ssr: None
    start_date: None
    end_date: None
    submodule: None
    dbe: None

@dataclasses.dataclass
class OBCErrorDataPoint:
    "Data class for an obc error data point."
    doy: None
    time: None
    error_type: None
    error: None


def generate_status_report(user_vars, auto_gen= False):
    "write the status report file"
    print(" - Generating CCDM status report .txt file...")
    set_dir= make_output_dir(user_vars, auto_gen)

    if auto_gen:
        file_title= "CCDM Status Report (Auto-Gen 14-Day Lookback)"
    else:
        file_title= (
            f"CCDM Status Report ({user_vars.year_start}{user_vars.doy_start}_"
            f"{user_vars.year_end}{user_vars.doy_end})"
        )

    with open(f"{set_dir}/{file_title}.txt", "w+", encoding= "utf-8") as file:
        tlm_corruption_detection(user_vars, file)
        obc_error_detection(user_vars, file)
        limit_violation_detection(user_vars, file)
        dbe_detection(user_vars, file)
        misc_detection(user_vars, file)
        file.close()

    print(f"""\nDone! Data written to "{file_title}.txt" in "{set_dir}".""")


def tlm_corruption_detection(user_vars, file):
    """
    Description: Generate a .txt file with details on telemetry corruption for given MSIDs
    Input: user variables for dates/times
    Output: none
    """
    print("\nLooking for corrupted datapoints...")
    corrupted_values= {}
    msids= {
        "AORESZ0":["1e14","-1e14"], "AORESZ1":["1e14","-1e14"], 
        "AORESZ2":["1e14","-1e14"], "AORESZ3":["1e2","-1e14"],
        "AORESZ4":["1e14","-1e14"], "AORESZ5":["1e2","-1e14"], "AORESZ6":["1e14","-1e14"],
        "4ACCACL":["CLOS"], "4ACCBCL":["CLOS"], "4ACCAOP":["CLOS"], "4ACCBOP":["CLOS"],
        "4ALL1ALK":["LOCK"], "4ALL1BLK":["LOCK"], "4ALL1AUL":["LOCK"], "4ALL1BUL":["LOCK"],
        "4ALL1ACS":["CLOS"], "4ALL2ACS":["CLOS"], "4ALL1BCS":["CLOS"], "4ALL2BCS":["CLOS"],
        "4HLL1ACS":["CLOS"], "4HLL1AUL": ["LOCK"], "4HLL1BUL": ["LOCK"], "4HLL1BLK": ["LOCK"],
        "4HLL1ALK": ["LOCK"],
        }
    for msid, bound in tqdm(msids.items(), bar_format= "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        corrupted_values[f"{msid}"]= get_corrupted_datapoints(user_vars, msid, bound)

    write_corr_report(user_vars, file, corrupted_values, msids)


def get_corrupted_datapoints(user_vars, msid, bound):
    """
    Description: Queries data per MSID, then checks for corrupted values against bounds
    Input: User Variables, MSID <str>, Bound <list>
    Output: Dict of corrupted data points, format {MSID,["TIME", "DATA"]}
    """
    corrupted_values = {}
    raw_data= data_request(user_vars.ts,user_vars.tp,"SKA High Rate",msid)

    for data_point, time_point in zip(raw_data.vals, raw_data.times):
        try:
            if float(bound[0]) <= data_point or data_point <= float(bound[1]):
                corrupted_values[CxoTime(time_point)]= data_point
        except ValueError:
            if data_point in (bound):
                corrupted_values[CxoTime(time_point)]= data_point

    return corrupted_values


def write_corr_report(user_vars, file, corrupted_values, msids):
    """
    Description: Write a txt file with tlm corruption findings.
    Input: User Variables <object>, Corrupted values <dict>, MSIDs <list>
    Output: None
    """
    print(" - Generating telemetry corruption report .txt file...")
    line= "-----------------------------"
    length_list= []

    for item in corrupted_values.values():
        length_list.append(len(item))

    file.write(
        "Detected corrupted telemetry data points for "
        f"{user_vars.year_start}:{format_doy(user_vars.doy_start)} "
        f"thru {user_vars.year_end}:{format_doy(user_vars.doy_end)}\n" +
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
    if not all([i== 0 for i in length_list]):
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
    file_list= get_obc_report_dirs(user_vars)
    report_data= get_obc_error_reports(file_list)
    write_obc_error_report(user_vars, file, report_data)


def get_obc_report_dirs(user_vars):
    "Generate list of OBC error report files"
    print(" - Building OBC Error Log report directory list...")
    start_date= datetime.strptime(
        f"{user_vars.year_start}:{user_vars.doy_start}:000000","%Y:%j:%H%M%S"
        )
    end_date= datetime.strptime(
        f"{user_vars.year_end}:{user_vars.doy_end}:235959","%Y:%j:%H%M%S"
        )
    root_folder= (
        "/share/FOT/engineering/flight_software/OBC_Error_Log_Dumps"
        )
    full_file_list, file_list= ([] for i in range(2))
    for year_diff in range((end_date.year - start_date.year) + 1):
        year= start_date.year + year_diff
        dir_path= Path(root_folder + "/" + str(year))
        full_file_list_path= list(x for x in dir_path.rglob('SMF_ERRLOG*.*'))

        for list_item in full_file_list_path:
            full_file_list.append(str(list_item))

    for day in range((end_date - start_date).days + 1):
        cur_day= start_date + timedelta(days=day)
        cur_year_str= cur_day.year
        cur_day_str= cur_day.strftime("%j")

        for list_item in full_file_list:
            if f"SMF_ERRLOG_0164_{cur_year_str}{cur_day_str}" in list_item:
                file_list.append(list_item)
    return file_list


def get_obc_error_reports(file_list):
    "Parse OBC error reports into data"
    print(" - Parsing OBC Error reports...")
    report_data= []

    for file_dir in tqdm(file_list, bar_format= "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        report_data.extend(parse_obc_report(file_dir))

    return report_data


def parse_obc_report(file_dir):
    """
    Description: Parse OBC error report
    """
    data_list= []
    with open(file_dir, 'r', encoding="utf-8") as obc_error_log:
        for line in obc_error_log:
            parsed= line.split()
            try:
                if parsed[0].isnumeric() and parsed[1] != 'NONE':
                    data_point= OBCErrorDataPoint(None,None,None,None)
                    full_date= datetime.strptime(parsed[1],"%Y%j:%H%M%S")
                    data_point.doy= full_date.strftime("%Y:%j")
                    data_point.time= full_date.strftime("%H:%M:%S")
                    data_point.error_type= parsed[7]
                    try:
                        error= f"{parsed[8]} {parsed[9]} {parsed[10]} {parsed[11]}"
                    except IndexError:
                        error= f"{parsed[8]}"
                    data_point.error= error
                    data_list.append(data_point)
            except IndexError:
                pass

    return data_list if data_list else None


def write_obc_error_report(user_vars, file, report_data):
    """
    Description: Write txt file of OBC Errors found.
    Input: Data <dict>
    Output: None
    """
    line= "-----------------------------"
    file.write(
        "Detected OBC Errors for "
        f"{user_vars.year_start}:{format_doy(user_vars.doy_start)} thru "
        f"{user_vars.year_end}:{format_doy(user_vars.doy_end)}\n" +
        "\n" + line + line + line)

    if report_data:
        write_obc_errors(report_data, file)
    else:
        file.write("\n  - No OBC Errors detected \U0001F63B.\n")

    file.write("\n  ----------END OF OBC ERRORS----------")
    file.write("\n" +line+line+line+line+line + "\n" +line+line+line+line+line + "\n")
    print(" - Done! Data written to OBC error section.")


def write_obc_errors(report_data, file):
    """
    Description: Write the OBC errors from a formatted dict
    Input: Report data, and file object
    Output: None
    """
    for index, (data_point) in enumerate(report_data):
        doy= data_point.doy
        previous_doy= report_data[index - 1].doy
        time= data_point.time
        error= data_point.error
        error_type= data_point.error_type

        if doy != previous_doy:
            file.write(f"\nOBC Errors for {doy}:\n")

        file.write(f"  - ({time}) Error Type:{error_type}  |  Error:{error}\n")


def limit_violation_detection(user_vars, file):
    """
    Description: Generate txt info file of limit violations
    Input: user_vars
    Output: None
    """
    print("\nAdding Limit Violation data...")
    limit_dir_list= get_limit_report_dirs(user_vars)
    limit_data= get_limit_reports(limit_dir_list)
    write_limit_report_file(user_vars, file, limit_data)


def get_limit_report_dirs(user_vars):
    "Generate list of limits.txt report files"
    print(" - Building OBC Error Log report directory list...")
    start_date= datetime.strptime(
        f"{user_vars.year_start}:{user_vars.doy_start}:000000","%Y:%j:%H%M%S"
        )
    end_date= datetime.strptime(
        f"{user_vars.year_end}:{user_vars.doy_end}:235959","%Y:%j:%H%M%S"
        )
    root_folder= "/share/FOT/engineering/reports/dailies/"
    directory_list= []
    date_diff= timedelta(days=(end_date-start_date).days)

    for date_range in range(date_diff.days + 1):
        current_date= start_date + timedelta(days= date_range)
        year= current_date.year
        month= current_date.strftime("%b")
        day= current_date.strftime("%d")
        doy= format_doy(str(current_date.timetuple().tm_yday))
        dir_path= Path(
            f"{root_folder}/{year}/{month.upper()}/{month.lower()}{day}_{doy}/limits.txt")
        directory_list.append(dir_path)

    return directory_list


def get_limit_reports(file_list):
    "Parse limit reports into data"
    print(" - Parsing Limit reports...")
    per_report_data, report_data, formatted_data= ({} for i in range(3))

    for file_dir in tqdm(file_list, bar_format= "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        per_report_data= parse_limit_report(file_dir)
        report_data.update(per_report_data)

    for date_time, data in report_data.items():
        date= str(date_time.strftime("%Y:%j"))
        formatted_data.setdefault(date,[]).append({date_time:data})

    return formatted_data


def parse_limit_report(file_dir):
    """
    Description: Parse limit error report
    """
    data_dict= {}
    filtered_msids= ["CTUDWLMD"]

    try:
        with open(file_dir, 'r', encoding="utf-8") as limit_file:
            for line in limit_file:
                parsed= line.split()
                msid, status= parsed[2], parsed[3]
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
    line= "-----------------------------"
    file.write(
        "Detected CCDM limit violations for "
        f"{user_vars.year_start}:{format_doy(user_vars.doy_start)} "
        f"thru {user_vars.year_end}:{format_doy(user_vars.doy_end)}\n\n" + line + line + line)
    if report_data:
        write_limit_violations(report_data, file)
    else:
        file.write("\n  - No limit violations detected \U0001F63B.\n")

    file.write("\n  ----------END OF LIMIT VIOLATIONS----------")
    file.write("\n" +line+line+line+line+line + "\n" +line+line+line+line+line + "\n")
    print(""" - Done! Data written to "limit violation section".""")


def write_limit_violations(report_data, file):
    """
    Description: Write the limit violations from a formatted dict
    Input: Report data, and file object
    Output: None
    """
    for date, data_dict_list in report_data.items():
        file.write(f"\nCCDM limit violations for {date}:\n")
        for data_dict in data_dict_list:
            for date_time, data_list in data_dict.items():
                for list_item in data_list:
                    time= date_time.strftime("%H:%M:%S")
                    try:
                        msid, error= list_item[1], list_item[2]
                        state, e_state= list_item[3], list_item[5]
                        file.write(
                            f'  - ({time} EST) MSID "{msid}", was "{error}" with a measured value '
                            f'of "{state}" with an expected state of "{e_state}".\n')
                    except IndexError:
                        if list_item[1]== "COTHIRTD": # MSID COTHIRTD has a different format
                            msid, error, state= list_item[1],list_item[2],list_item[4]
                            file.write(
                                f'  - ({time} EST) MSID "{msid}", was "{error}" with a measured'
                                f' value of "{state}" with an expected state of "<BLANK>".\n')


def dbe_detection(user_vars, file):
    "Pull DBEs from BEAT files to populate into report file."
    print("\nAdding DBE data...")
    data= BEATData([],[])
    get_beat_report_dirs(user_vars, data)
    get_ssr_beat_reports(data)
    write_beat_report(user_vars, data, file)


def get_ssr_beat_reports(data):
    "Parse SSR beat reports into data"
    print(" - Parsing SSR beat report data...")

    for beat_report in data.file_list:
        try:
            data_point= parse_beat_report(beat_report)
        except FileNotFoundError:
            print(f"""     - Error parsing file "{beat_report[-34:]}"! Skipping file...""")

        if data_point:
            data.dbe_data+= data_point


def parse_beat_report(fname):
    """
    Description: Parse beat reports
    """
    cur_state, ssr, data_list = 'FIND_SSR', None, []

    with open(fname, 'r', encoding="utf-8") as beat_report:
        for line in beat_report:
            data_point= BEATDataPoint(None,None,None,None,None)
            if cur_state== 'FIND_SSR':
                if line[0:5]== 'SSR =':
                    ssr = str(line[6]) # Character 'A' or 'B'
                    cur_state= 'FIND_SUBMOD'
            elif cur_state== 'FIND_SUBMOD':
                if line[0:7]=='SubMod ':
                    cur_state= 'REC_SUBMOD'
            elif cur_state== 'REC_SUBMOD':
                if line[0].isdigit():
                    parsed= line.split()
                    data_point.ssr= ssr
                    data_point.start_date= datetime.strptime(f"{parsed[4]}", "%Y%j.%H%M%S")
                    data_point.end_date= datetime.strptime(f"{parsed[5]}", "%Y%j.%H%M%S")
                    data_point.submodule= int(parsed[0])
                    data_point.dbe= int(parsed[3])
                    data_list.append(data_point)
                else:
                    cur_state = 'FIND_SSR'

    return data_list if data_list else None


def get_beat_report_dirs(user_vars, data):
    "Generate list of beat report files"
    print(" - Building SSR beat report directory list...")
    start_date= datetime.strptime(
        f"{user_vars.year_start}:{user_vars.doy_start}:000000","%Y:%j:%H%M%S"
        )
    end_date= datetime.strptime(
        f"{user_vars.year_end}:{user_vars.doy_end}:235959","%Y:%j:%H%M%S"
        )
    root_folder= (
        "/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/SSR_Short_Reports/"
        )
    full_file_list, file_list= ([] for i in range(2))

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

    data.file_list= file_list


def write_beat_report_data(data, file):
    "Write data parsed from BEAT reports into output file."
    for index, (data_point) in enumerate(data.dbe_data):
        doy= data_point.start_date.strftime("%Y:%j")
        previous_doy= data.dbe_data[index - 1].start_date.strftime("%Y:%j")
        start_time= f"""{data_point.start_date.strftime("%H:%M:%S")}z"""
        end_time= f"""{data_point.end_date.strftime("%H:%M:%S")}z"""

        if doy != previous_doy or (len(data.dbe_data) == 1):
            file.write(f"\nDBEs for {doy}:\n")

        file.write(f"  - ({start_time} thru {end_time}) SSR-{data_point.ssr} | "
                   f"submodule: {data_point.submodule} | DBEs: {data_point.dbe}\n")


def write_beat_report(user_vars, data, file):
    "Write formatting for BEAT reports into output file."
    line= "-----------------------------"
    file.write(
        f"Detected DBEs for {user_vars.year_start}:{format_doy(user_vars.doy_start)} "
        f"thru {user_vars.year_end}:{format_doy(user_vars.doy_end)}\n\n" +line+line+line)

    if data.dbe_data:
        write_beat_report_data(data,file)
    else:
        file.write("\n  - No DBEs detected for the selected date/time range \U0001F63B.\n")

    file.write("\n  ----------END OF DBE DETECTION----------")
    file.write("\n" +line+line+line+line+line + "\n" +line+line+line+line+line + "\n")
    print(""" - Done! Data written to "DBE section".""")


def misc_detection(user_vars, file):
    "Add misc detection items to report file"
    print("\nMisc Detection Items...")
    line= "-----------------------------"
    file.write(
        f"Misc Detected Items for {user_vars.year_start}:{format_doy(user_vars.doy_start)} "
        f"thru {user_vars.year_end}:{format_doy(user_vars.doy_end)}\n\n" + line+line+line + "\n")

    vcdu_rollover_detection(user_vars,file)
    spurious_cmd_lock_detection(user_vars,file)
    ssr_rollover_detection(user_vars,file)
    sequencer_selftest_detection(user_vars,file)
    scs107_detection(user_vars,file)

    file.write("\n  ----------END OF MISC DETECTION----------")
    file.write("\n" +line+line+line+line+line + "\n" +line+line+line+line+line + "\n")
    print(" - Done! Data written to Misc section.")
