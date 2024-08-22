"Methods to process BEAT reports"

from datetime import datetime, timedelta
from pathlib import Path
from components.plotting import add_plot_trace


def add_dbe_data(user_vars, data, figure, row):
    """
    Description: Add dbe error data to plot
    Input: Data Object, figure
    Output: None
    """
    print(" - Adding DBE Data...")
    get_ssr_beat_reports(user_vars, data)
    ssra_x_data = list(data.doy_dict_a.keys())
    ssra_y_data = list(data.doy_dict_a.values())
    ssrb_x_data = list(data.doy_dict_b.keys())
    ssrb_y_data = list(data.doy_dict_b.values())

    print("   - Adding data to plot traces...")
    add_plot_trace(figure, ssra_x_data, ssra_y_data, "SSR-A DBEs", row)
    add_plot_trace(figure, ssrb_x_data, ssrb_y_data, "SSR-B DBEs", row)


def get_ssr_beat_reports(user_vars,data):
    "Parse SSR beat reports into data"
    print("   - Parsing SSR beat report data...")
    doy_dict_a, doy_dict_b = ({} for i in range(2))
    file_list = get_beat_report_dirs(user_vars)

    for beat_report in file_list:
        try:
            doy, submod_dbe = parse_beat_report(beat_report)
        except FileNotFoundError:
            print(f"""     - Error parsing file "{beat_report[-34:]}"! Skipping file...""")
        dbe_total_a, dbe_total_b = ([] for i in range(2))

        for data_a in submod_dbe["A"]:
            dbe_total_a += list(data_a.values())
        for data_b in submod_dbe["B"]:
            dbe_total_b += list(data_b.values())

        if sum(dbe_total_a) != 0: # Only record dates with DBEs
            doy_dict_a[f"{doy}"] = sum(dbe_total_a)
        else: # If no DBE on date, record zero for that day.
            doy_dict_a[f"{doy}"] = 0

        if sum(dbe_total_b) != 0:
            doy_dict_b[f"{doy}"] = sum(dbe_total_b)
        else:
            doy_dict_b[f"{doy}"] = 0

    # Record data to data object
    data.doy_dict_a = doy_dict_a
    data.doy_dict_b = doy_dict_b


def parse_beat_report(fname):
    """
    Description: Parse beat reports
    """
    ret_dict = {"A": [],"B": []}
    cur_state = 'FIND_SSR'
    with open(fname, 'r', encoding="utf-8") as beat_report:
        for line in beat_report:
            if line[0:10] ==  'Dump start': # Get DOY
                parsed = line.split()
                fulldate = parsed[3].split()
                doy = datetime.strptime(f"{fulldate[0][:-3]}", "%Y%j.%H%M%S")
            if cur_state == 'FIND_SSR':
                if line[0:5] == 'SSR =':
                    cur_ssr = line[6] # Character 'A' or 'B'
                    cur_state = 'FIND_SUBMOD'
            elif cur_state == 'FIND_SUBMOD':
                if line[0:7] =='SubMod ':
                    cur_state = 'REC_SUBMOD'
            elif cur_state == 'REC_SUBMOD':
                if line[0].isdigit():
                    parsed = line.split()
                    ret_dict[cur_ssr].append({int(parsed[0]): int(parsed[3])})
                else:
                    cur_state = 'FIND_SSR'
    return doy, ret_dict


def get_beat_report_dirs(user_vars):
    "Generate list of beat report files"
    print("     - Building SSR beat report directory list...")
    start_date = datetime.strptime(
        f"{user_vars.start_year}:{user_vars.start_doy}:000000","%Y:%j:%H%M%S"
        )
    end_date = datetime.strptime(
        f"{user_vars.end_year}:{user_vars.end_doy}:235959","%Y:%j:%H%M%S"
        )
    root_folder = (
        "/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/SSR_Short_Reports/"
        )
    full_file_list, file_list = ([] for i in range(2))

    for year_diff in range((end_date.year-start_date.year) + 1):
        year = start_date.year + year_diff
        dir_path = Path(root_folder + "/" + str(year))
        full_file_list_path = list(x for x in dir_path.rglob('BEAT*.*'))

        for list_item in full_file_list_path:
            full_file_list.append(str(list_item))

    for day in range((end_date-start_date).days + 1):
        cur_day = start_date + timedelta(days=day)
        cur_year_str = cur_day.year
        cur_day_str = cur_day.strftime("%j")

        for list_item in full_file_list:
            if f"BEAT-{cur_year_str}{cur_day_str}" in list_item:
                file_list.append(list_item)

    return file_list
