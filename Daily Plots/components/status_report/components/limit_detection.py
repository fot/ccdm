"Module to detect CCDM limits"

from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
from components.misc import format_doy


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
