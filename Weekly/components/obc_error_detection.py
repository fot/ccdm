"OBC Error Detection"
from datetime import datetime, timedelta
import itertools as it
from pathlib import Path
from tqdm import tqdm
from dataclasses import dataclass


@dataclass
class OBCErrorDataPoint:
    "Data class for an obc error data point."
    doy: None
    time: None
    error_type: None
    error: None


def get_obc_report_dirs(user_vars):
    "Generate list of OBC error report files"
    print("OBC Error Detection...")
    print("   - Building OBC Error Log report directory list...")
    start_date= user_vars.ts.datetime
    end_date= user_vars.tp.datetime
    root_folder= "/share/FOT/engineering/flight_software/OBC_Error_Log_Dumps"
    full_file_list,file_list= ([] for i in range(2))

    for year_diff in range((end_date.year-start_date.year)+1):
        year = start_date.year + year_diff
        dir_path = Path(root_folder + "/" + str(year))
        full_file_list_path = list(x for x in dir_path.rglob('SMF_ERRLOG*.*'))

        for list_item in full_file_list_path:
            full_file_list.append(f"{list_item}")

    for day in range((end_date-start_date).days + 1):
        cur_day = start_date + timedelta(days=day)
        cur_year_str = cur_day.year
        cur_day_str = cur_day.strftime("%j")

        for list_item in full_file_list:
            if f"SMF_ERRLOG_0164_{cur_year_str}{cur_day_str}" in list_item:
                file_list.append(list_item)

    return file_list


def get_obc_error_reports(file_list, user_vars):
    "Parse OBC error reports into data"
    print("   - Parsing OBC Error reports...")
    report_data = []

    for file_dir in tqdm(file_list, bar_format= "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        report_data.extend(parse_obc_report(file_dir, user_vars))

    return report_data


def parse_obc_report(file_dir, user_vars):
    """
    Description: Parse OBC error report
    """
    data_list= []
    # start_date= datetime.strptime(f"{user_vars.year_start}:{user_vars.doy_start}:"
    #                               "000000","%Y:%j:%H%M%S")
    # end_date=   datetime.strptime(f"{user_vars.year_end}:{user_vars.doy_end}:"
    #                               "235959","%Y:%j:%H%M%S")

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
                    if user_vars.ts <= full_date <= user_vars.tp:
                        data_list.append(data_point)
            except IndexError:
                pass

    return data_list


def write_obc_errors(obc_error_report_data):
    """
    Description: Add all the OBC errors to the perf_health_section string
    Input: perf_health_section <str>
    Ouput: Modified perf_health_section <str>
    """
    print("   - Writing OBC Errors...")
    return_string = ""
    for i, (data_point) in enumerate(obc_error_report_data):
        doy= data_point.doy
        prev_doy= obc_error_report_data[i-1].doy if i > 0 else None

        # Add Year:DoY header if the day has changed
        if doy != prev_doy:
            return_string += (
                """</ul></ul></li></div><ul><ul><li><p></p>"""
                f"""<button type="button" class="collapsible">OBC Errors for {doy}</button>"""
                """<div class="content">\n""")

        # Add the error
        return_string += (f'<ul><li>({data_point.time} UTC) Error Type: "{data_point.error_type}"'
                          f' |  Error: "{data_point.error}"</li></ul>\n')

    return f"{return_string}</ul>"
