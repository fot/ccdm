"OBC Error Detection"
from datetime import datetime, timedelta
import itertools as it
from pathlib import Path


def get_obc_report_dirs(user_vars):
    "Generate list of OBC error report files"
    print("OBC Error Detection...")
    print("   - Building OBC Error Log report directory list...")
    start_date = datetime.strptime(
        f"{user_vars.start_year}:{user_vars.doy_start}:000000","%Y:%j:%H%M%S"
        )
    end_date = datetime.strptime(
        f"{user_vars.end_year}:{user_vars.doy_end}:235959","%Y:%j:%H%M%S"
        )
    root_folder = (
        "/share/FOT/engineering/flight_software/OBC_Error_Log_Dumps"
        )
    full_file_list, file_list = ([] for i in range(2))

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


def get_obc_error_reports(file_list):
    "Parse OBC error reports into data"
    print("   - Parsing OBC Error reports...")
    per_report_data, report_data, formatted_data = ({} for i in range(3))

    for file_dir in file_list:
        per_report_data = parse_obc_report(file_dir)
        report_data.update(per_report_data)

    for date_time, data in report_data.items():
        formatted_data.setdefault(f"{date_time.strftime('%Y:%j')}",[]).append({date_time:data})

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


def write_obc_errors(obc_error_report_data):
    """
    Description: Add all the OBC errors to the perf_health_section string
    Input: perf_health_section <str>
    Ouput: Modified perf_health_section <str>
    """
    print("   - Writing OBC Errors...")
    return_string = ""
    for date, data in obc_error_report_data.items():
        return_string += (
            """</ul></ul></li></div><ul><ul><li><p></p>"""
            f"""<button type="button" class="collapsible">OBC Errors for {date}</button>"""
            """<div class="content">\n""")
        for dict_list in data:
            for date_time, type_error_dict_list in dict_list.items():
                for type_error in type_error_dict_list:
                    for error_type, error in type_error.items():
                        item_time = date_time.strftime("%H:%M:%S")
                        return_string += (
                            f'<ul><li>({item_time} UTC)  Error Type: "{error_type}" '
                            f' |  Error: "{error}"</li></ul>\n'
                            )
        return_string += "</ul>"
    return return_string
