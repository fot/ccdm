"Module to collect OBC errors from the OBC error logs and create a report."

from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from tqdm import tqdm
from components.misc import format_doy


@dataclass
class OBCErrorDataPoint:
    "Data class for an obc error data point."
    doy: None
    time: None
    error_type: None
    error: None


def get_obc_report_dirs(user_vars):
    "Generate list of OBC error report files"
    print(" - Building OBC Error Log report directory list...")
    start_date= datetime.strptime(f"{user_vars.year_start}:{user_vars.doy_start}:"
                                  "000000","%Y:%j:%H%M%S")
    end_date=   datetime.strptime(f"{user_vars.year_end}:{user_vars.doy_end}:"
                                  "235959","%Y:%j:%H%M%S")
    root_folder= ("/share/FOT/engineering/flight_software/OBC_Error_Log_Dumps")

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


def get_obc_error_reports(file_list, user_vars):
    "Parse OBC error reports into data"
    print(" - Parsing OBC Error reports...")
    report_data= []

    for file_dir in tqdm(file_list, bar_format= "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        report_data.extend(parse_obc_report(file_dir, user_vars))

    return report_data


def parse_obc_report(file_dir, user_vars):
    """
    Description: Parse OBC error report
    """
    data_list= []
    start_date= datetime.strptime(f"{user_vars.year_start}:{user_vars.doy_start}:"
                                  "000000","%Y:%j:%H%M%S")
    end_date=   datetime.strptime(f"{user_vars.year_end}:{user_vars.doy_end}:"
                                  "235959","%Y:%j:%H%M%S")

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
                    if start_date <= full_date <= end_date:
                        data_list.append(data_point)
            except IndexError:
                pass

    return data_list


def write_obc_error_report(user_vars, file, report_data):
    """
    Description: Write txt file of OBC Errors found.
    Input: Data <dict>
    Output: None
    """
    file.write(
        "Detected OBC Errors for "
        f"{user_vars.year_start}:{format_doy(user_vars.doy_start)} thru "
        f"{user_vars.year_end}:{format_doy(user_vars.doy_end)}\n" +
        "\n" + ("-"*87) + "\n")

    if report_data:
        write_obc_errors(report_data, file)
    else:
        file.write("\n  - No OBC Errors detected \U0001F63B.\n")

    file.write("\n  ----------END OF OBC ERRORS----------")
    file.write("\n" + ("-"*145) + "\n" + ("-"*145) + "\n")
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


def obc_error_detection(user_vars, file):
    """
    Description: Add dbe error data to plot
    Input: Data Object, figure
    Output: None
    """
    print("\nAdding OBC Error Data...")
    file_list= get_obc_report_dirs(user_vars)
    report_data= get_obc_error_reports(file_list, user_vars)
    write_obc_error_report(user_vars, file, report_data)
