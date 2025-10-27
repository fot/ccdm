"Module to detect CCDM limits"

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
from components.misc import format_doy

@dataclass
class LimitViolationData:
    "Dataclass for limit violation data"
    date=   None
    msid=   None
    status= None
    measured_value= None
    operator=       None
    expected_value= None

    def __init__(self,date, msid, status, measured_value, operator, expected_value):
        self.date=  date
        self.msid=  msid
        self.status= status
        self.measured_value= measured_value
        self.operator=       operator
        self.expected_value= expected_value


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


def parse_limit_report(file_dir):
    """
    Description: Parse limit error report
    """
    data_list= []
    data_point= LimitViolationData(None,None,None,None,None,None)

    try:
        with open(file_dir, "r", encoding="utf-8") as limit_file:
            for line in limit_file:
                split_line= line.split()

                if split_line[3] != "NOMINAL":
                    data_point.date=   datetime.strptime(split_line[0],"%Y%j.%H%M%S")
                    data_point.msid=   split_line[2]
                    data_point.status= split_line[3]
                    data_point.measured_value= split_line[4]
                    data_point.operator=       split_line[5]
                    data_point.expected_value= split_line[6]

                if data_point.msid is not None:
                    data_list.append(data_point)
                    data_point= LimitViolationData(None,None,None,None,None,None)

    except OSError:
        print(f""" - Error! File "{file_dir}" did not exist, will skip this file...""")

    return data_list


def get_limit_reports_data(user_vars):
    "Parse limit reports into data"
    print(" - Parsing Limit reports...")
    data_list= []

    # Get the limit report file directories
    limit_report_dirs= get_limit_report_dirs(user_vars)

    # Parse each limit report file & collect data
    for file_directory in tqdm(limit_report_dirs):
        data_list.extend(parse_limit_report(file_directory))

    return data_list


def write_limit_violations(limit_reports_data, file):
    """
    Description: Write the limit violations from a formatted dict
    Input: Report data, and file object
    Output: None
    """
    # Init previous_date
    previous_date= None
    filtered_msids= ["CTUDWLMD"]

    for data_point in limit_reports_data:

        # Filtered for CCDM MSIDs and Filtered MSIDs
        if ((data_point.msid.startswith("C") or data_point.msid.startswith("PA_"))
            and (data_point.msid not in filtered_msids)):
            # Write the date header if new day of year
            current_date= data_point.date.strftime("%Y:%j")
            if current_date != previous_date:
                file.write(f'\nCCDM limit violations for {current_date}:\n')

            file.write(
                f'  - ({data_point.date.strftime("%H:%M:%S")} EST): MSID "{data_point.msid}", '
                f'Status: "{data_point.status}", Measured Value: "{data_point.measured_value}" '
                f'{data_point.operator} Expected State: "{data_point.expected_value}".\n')

            previous_date= current_date


def write_limit_report_file(user_vars, file, limit_reports_data):
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
    if limit_reports_data:
        write_limit_violations(limit_reports_data, file)
    else:
        file.write("\n  - No limit violations detected \U0001F63B.\n")

    file.write("\n  ----------END OF LIMIT VIOLATIONS----------")
    file.write("\n" +line+line+line+line+line + "\n" +line+line+line+line+line + "\n")
    print(""" - Done! Data written to "limit violation section".""")


def limit_violation_detection(user_vars, file):
    """
    Description: Generate txt info file of limit violations
    Input: user_vars
    Output: None
    """
    print("\nAdding Limit Violation data...")
    limit_reports_data= get_limit_reports_data(user_vars)
    write_limit_report_file(user_vars, file, limit_reports_data)
