"Limit Violation Detection"

from datetime import datetime, timedelta
from pathlib import Path
from components.misc import format_doy


def get_limit_report_dirs(user_vars):
    "Generate list of limits.txt report files"
    print("Limit Violation Detection...")
    print("   - Building list of limit reports...")
    start_date = datetime.strptime(
        f"{user_vars.start_year}:{user_vars.doy_start}:000000","%Y:%j:%H%M%S"
        )
    end_date = datetime.strptime(
        f"{user_vars.end_year}:{user_vars.doy_end}:235959","%Y:%j:%H%M%S"
        )
    root_folder = "/share/FOT/engineering/reports/dailies/"
    directory_list = []
    date_diff = timedelta(days=(end_date-start_date).days)

    for date_range in range(date_diff.days + 1):
        current_date = start_date + timedelta(date_range)
        year = current_date.year
        month = current_date.strftime("%b")
        day = current_date.strftime("%d")
        doy = format_doy(f"{current_date.timetuple().tm_yday}")
        dir_path = Path(
            f"{root_folder}/{year}/{month.upper()}/{month.lower()}{day}_{doy}/limits.txt")
        directory_list.append(dir_path)

    return directory_list


def get_limit_reports(file_list):
    "Parse limit reports into data"
    print("   - Parsing limit reports...")
    per_report_data, report_data, formatted_data = ({} for i in range(3))

    for file_dir in file_list:
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

    with open(file_dir, 'r', encoding="utf-8") as limit_file:
        for line in limit_file:
            parsed = line.split()
            msid, status = parsed[2], parsed[3]
            if ((msid.startswith("C") or msid.startswith("PA_")) and
                (status != 'NOMINAL') and (msid not in filtered_msids)
                ):
                data_dict.setdefault(
                    datetime.strptime(parsed[0],"%Y%j.%H%M%S"),[]).append(parsed[1:])
    return data_dict


def write_limit_violations(limit_data):
    "Write limit violations to perf_health_section string"
    print("   - Writing limit report...")
    return_string = ""
    for date, data_dict_list in limit_data.items():
        return_string += (
            """</div><ul><ul><li>"""
            """<p></p>"""
            """<button type="button" class="collapsible">"""
            f"""CCDM Limit Violations for {date}</button>"""
            """<div class="content">\n""")
        for data_dict in data_dict_list:
            for date_time, data_list in data_dict.items():
                for list_item in data_list:
                    time_item = date_time.strftime("%H:%M:%S")
                    try:
                        msid, error = list_item[1], list_item[2]
                        state, e_state = list_item[3], list_item[5]
                        return_string += (
                            f'<ul><li>({time_item} UTC)  MSID "{msid}", was "{error}" '
                            f'with a measured value of "{state}" with an expected '
                            f'state of "{e_state}".</li></ul>\n')
                    except BaseException:
                        if list_item[1] == "COTHIRTD": # MSID COTHIRTD has a different format
                            msid, error, state = list_item[1], list_item[2], list_item[4]
                            return_string += (
                                f'<ul><li>({time_item} EST) MSID "{msid}" was "{error}" '
                                f'with a measured value of "{state}" with an expected '
                                'state of "<BLANK>".</li></ul>\n')
        return_string += "</ul></ul></li>"
    return return_string
