import datetime
import json
import time
import urllib.request
from tqdm import tqdm
from pathlib import Path
from os import system
import io
import requests
import plotly.graph_objects as go
from plotly import subplots
import pandas as pd
from components.misc import create_dir


class DataObject:
    "Empty data object to save data to"


class UserVars:
    """
    Description: Gather use inputs
    """
    def __init__(self):
        while True:
            system("cls")
            self.start_year = get_start_year()
            self.start_doy = get_doy_start()
            self.end_year = get_end_year()
            self.end_doy = get_end_doy()
            self.start_date = doy_to_date(self.start_year, self.start_doy)
            self.end_date = doy_to_date(self.end_year, self.end_doy)
            input_status = input("\nAre these inputs correct? Y/N: ")

            if input_status in ("Y","y","Yes","yes"):
                break

            print("\nRestarting Inputs...\n\n")
            time.sleep(1.5)

def get_start_year():
    "Get user input for start year"
    while True:
        year_input = input("Enter the START year: XXXX ")
        if (len(str(year_input)) == 4) and (1998 <= int(year_input) <= 2040):
            break
        print(f"{year_input} was an invalid input, please try again")
    return year_input

def get_doy_start():
    "Get user in put for DOY start"
    while True:
        doy_input = input("Enter the START day: XXX ")
        if (len(str(doy_input)) == 3) and (1 <= int(doy_input) <= 366):
            break
        print(f"{doy_input} was an invalid input, please try again")
    return doy_input

def get_end_year():
    "Get user input for end year"
    while True:
        year_input = input("Enter the END year: XXXX ")
        if (len(str(year_input)) == 4) and (1998 <= int(year_input) <= 2040):
            break
        print(f"{year_input} was an invalid input, please try again")
    return year_input

def get_end_doy():
    "Get user input for DOY end"
    while True:
        doy_input = input("Enter the END day: XXX ")
        if (len(str(doy_input)) == 3) and (1 <= int(doy_input) <= 366):
            break
        print(f"{doy_input} was an invalid input, please try again\n")
    return doy_input

def doy_to_date(input_year, input_doy):
    """
    Description: Corrects data format acceptable to url query
    Input: User Variables with Year start/end & DOY start/end
    Output: String of formated date in format yyyy-MM-dd
    """
    time_object = datetime.datetime.strptime(f"{input_year} {input_doy}", "%Y %j")
    return time_object


def data_query(user_vars, dataset):
    """
    Description: Build query URL from user inputs, request data from "Space Weather Data Portal"
    Output: JSON of data
    """
    print(f"""   - Querying for "{dataset}" space weather data...""")
    base_url = "https://lasp.colorado.edu/space-weather-portal/latis/dap/"
    start_date = user_vars.start_date.strftime("%Y-%m-%d")
    end_date = user_vars.end_date.strftime("%Y-%m-%d")
    query_url = base_url + (
        f"{dataset}.json?time%3E={start_date}"
        f"&time%3C={end_date}&formatTime(yyyy-MM-dd%20HH:mm)"
    )
    while True:
        try:
            response = urllib.request.urlopen(query_url)
            html = response.read()
            break
        except TimeoutError:
            print("Query attempt failed, trying again...")
    return json.loads(html)


def write_html_file(user_vars, figure):
    "Write HTML output file after figure generation"
    print(" - Generating html output file.....")

    figure_title = (
        "Space Weather Data (GOES Spacecraft) " +
        f"({user_vars.start_year}{user_vars.start_doy}_{user_vars.end_year}{user_vars.end_doy})"
    )

    output_dir = ("//noodle/GRETA/rhoover/python/Code/Chandra_CCDM/"
                  "GOES Spacecraft Space Weather Plotter/Output")
    create_dir(output_dir)
    figure.write_html(f"{output_dir}/{figure_title}.html")
    print(f""" - Done! Data written to "{output_dir}{figure_title}.html" in output directory.""")


def add_plot_trace(figure,x_values,y_values,title,row,bar_graph=False,sec_y=None,opac=1):
    """
    Description: Add a trace to the plot
    Inputs: Figure, x_values list, y_values list, trace title string
    """
    if bar_graph:
        figure.add_trace(
        go.Bar(
            x = x_values,
            y = y_values,
            name = title,
            opacity = opac,
        ),
        row = row, col=1,
        secondary_y = sec_y,
        )
    else:
        figure.add_trace(
            go.Scatter(
                x = x_values,
                y = y_values,
                mode = "lines",
                name = title,
            ),
        row = row, col=1,
        secondary_y = sec_y,
        )


def format_times(times_list):
    "Formats a list of time into a plottable format."
    input_format = "%Y-%m-%d %H:%M"
    formatted_times = []

    for time_item in times_list:
        new_list_item = datetime.datetime.strptime(time_item, input_format)
        formatted_times.append(new_list_item)

    return formatted_times


def format_plot_axes(user_vars, figure, yaxis_titles):
    """
    Description: Formats plot axies based on string inputs
    Input: Plot, plot_title
    Output: None
    """
    print(" - Making things look pretty...")
    figure_title = (
        "GOES Spacecraft Space Weather Data " +
        f"({user_vars.start_year}{user_vars.start_doy}_{user_vars.end_year}{user_vars.end_doy})"
    )

    for yaxis_number, yaxis_labels in yaxis_titles.items():
        for index, yaxis_label in enumerate(yaxis_labels):
            figure["layout"][f"yaxis{yaxis_number + index}"]["title"] = yaxis_label

    for xaxis_number in range(len(yaxis_titles)):
        figure.update_layout({f"xaxis{xaxis_number + 1}": {"matches": "x", "showticklabels": True}})

    figure["layout"][f"xaxis{len(yaxis_titles)}"]["title"] = "Time/Date"
    figure.update_xaxes(gridcolor="rgba(80,80,80,1)",autorange=True)
    figure.update_yaxes(gridcolor="rgba(80,80,80,1)",autorange=True)
    figure.update_layout(
        title =  figure_title,
        font = {
            "family": "Courier New, monospace",
            "size": 12,
            "color": "rgba(255,255,255,1)",
        },
        plot_bgcolor = "rgba(0,0,0,1)",
        paper_bgcolor = "rgba(0,0,0,1)",
        autosize = True,
        showlegend = True,
        grid = {"xgap": 0.15, "ygap": 0.15},
        legend = {
            "bgcolor": "rgba(57,57,57,1)",
            "bordercolor": "white",
            "borderwidth": 1,
        },
        hovermode="x unified",
    )


def check_data_validity(data):
    """
    Description: Check that data is valid
    Input: Data point
    Output: Data point or zero if data not valid
    """
    if data >= 0:
        return data
    return 0


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
                doy = datetime.datetime.strptime(f"{fulldate[0][:-3]}", "%Y%j.%H%M%S")
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
    start_date = datetime.datetime.strptime(
        f"{user_vars.start_year}:{user_vars.start_doy}:000000","%Y:%j:%H%M%S"
        )
    end_date = datetime.datetime.strptime(
        f"{user_vars.end_year}:{user_vars.end_doy}:235959","%Y:%j:%H%M%S"
        )
    root_folder = (
        "//noodle/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/SSR_Short_Reports/"
        )
    full_file_list, file_list = ([] for i in range(2))

    for year_diff in range((end_date.year-start_date.year) + 1):
        year = start_date.year + year_diff
        dir_path = Path(root_folder + "/" + str(year))
        full_file_list_path = list(x for x in dir_path.rglob('BEAT*.*'))

        for list_item in full_file_list_path:
            full_file_list.append(str(list_item))

    for day in range((end_date-start_date).days + 1):
        cur_day = start_date + datetime.timedelta(days=day)
        cur_year_str = cur_day.year
        cur_day_str = cur_day.strftime("%j")

        for list_item in full_file_list:
            if f"BEAT-{cur_year_str}{cur_day_str}" in list_item:
                file_list.append(list_item)

    return file_list


def get_ssr_beat_reports(user_vars,data):
    "Parse SSR beat reports into data"
    print("   - Parsing SSR beat report data...")
    doy_dict_a, doy_dict_b = ({} for i in range(2))
    file_list = get_beat_report_dirs(user_vars)

    for beat_report in file_list:
        try:
            doy, submod_dbe = parse_beat_report(beat_report)
        except BaseException:
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


def add_electron_flux_data(figure, data, formatted_times, row):
    "Description: Add electron flux data to the plot"
    print("   - Adding Electron Flux Data...")
    electron_08mev, electron_2mev, electron_4mev = ([] for i in range(3))

    print("     - Formatting data...")
    for list_item in data['goesp_part_flux_P5M']['samples']:
        electron_08mev.append(float(check_data_validity(list_item['E_8'])))
        electron_2mev.append(float(check_data_validity(list_item['E2_0'])))
        electron_4mev.append(float(check_data_validity(list_item['E4_0'])))

    for list_id in ("08","2","4"):
        data_list = eval(f"electron_{list_id}mev")
        if list_id == ("08"):
            list_label = "0.8"
        else: list_label = list_id
        if not all([v == 0 for v in data_list]):
            print(f"""     - Adding Electron Flux > {list_label} Mev to plot...""")
            add_plot_trace(
                figure,formatted_times,data_list,f"Electron Flux > {list_label} MeV", row)
        else:
            print(f"""     - Omitting "Electron Flux > {list_label} MeV" trace due to no data...""")


def add_proton_flux_data(figure, data, formatted_times, row):
    "Description: Add proton flux data to the plot."
    print("   - Adding Proton Flux Data...")
    proton_1mev, proton_5mev, proton_10mev, proton_30mev = ([] for i in range(4))
    proton_50mev, proton_100mev, proton_60mev, proton_500mev = ([] for i in range(4))

    print("     - Formatting data...")
    for list_item in data['goesp_part_flux_P5M']['samples']:
        proton_1mev.append(float(check_data_validity(list_item['P1'])))
        proton_5mev.append(float(check_data_validity(list_item['P5'])))
        proton_10mev.append(float(check_data_validity(list_item['P10'])))
        proton_30mev.append(float(check_data_validity(list_item['P30'])))
        proton_50mev.append(float(check_data_validity(list_item['P50'])))
        proton_60mev.append(float(check_data_validity(list_item['P60'])))
        proton_100mev.append(float(check_data_validity(list_item['P100'])))
        proton_500mev.append(float(check_data_validity(list_item['P500'])))

    for list_id in ("1","5","10","30","50","60","100","500"):
        data_list = eval(f"proton_{list_id}mev")
        if not all([v == 0 for v in data_list]):
            print(f"""     - Adding Proton Flux > {list_id} Mev to plot...""")
            if list_id == "1":
                add_plot_trace(
                    figure, formatted_times, data_list,
                    f"Proton Flux > {list_id} MeV", row, sec_y=True)
            else:
                add_plot_trace(
                    figure, formatted_times, data_list,
                    "Proton Flux > 5 MeV", row)
        else:
            print(f"""     - Omitting "Proton Flux > {list_id} MeV" """
                  "trace due to no data being collected...")


def add_particle_flux_data(user_vars, figure, e_row, p_row):
    """
    Working On it
    """
    print(" - Adding Particle Flux Data...")
    times = []
    goes_particle_data = data_query(user_vars,"goesp_part_flux_P5M")

    for list_item in goes_particle_data['goesp_part_flux_P5M']['samples']:
        times.append(list_item['time'])

    formatted_times = format_times(times)
    add_proton_flux_data(figure,goes_particle_data,formatted_times,p_row)
    add_electron_flux_data(figure,goes_particle_data,formatted_times,e_row)


def add_xray_flux_data(user_vars, figure, row):
    """
    Working On It
    """
    print(" - Adding X-Ray Flux Data...")
    xray_short_wave, xray_long_wave, times = ([] for i in range(3))
    goes_xray_data = data_query(user_vars, "goesp_xray_flux_P1M")

    print("   - Formatting data...")
    for list_item in goes_xray_data['goesp_xray_flux_P1M']['samples']:
        times.append(list_item['time'])
        xray_short_wave.append(float(list_item['Short_Wave']))
        xray_long_wave.append(float(list_item['Long_Wave']))

    formatted_times = format_times(times)
    print("   - Adding data to plot traces...")
    add_plot_trace(figure, formatted_times, xray_short_wave, "X-Ray Flux (Short Wave)", row)
    add_plot_trace(figure, formatted_times, xray_long_wave, "X-Ray Flux (Long Wave)", row)


def add_magnetometer_data(user_vars, figure, row):
    """
    Add data for GOES measured magnetometer values
    """
    print(" - Adding Magnetometer Data...")
    times, hp, he, hn = ([] for i in range (4))
    mag_data = data_query(user_vars, "goess_mag_p1m")

    print("   - Formatting data...")
    for list_item in mag_data['goess_mag_p1m']['samples']:
        times.append(list_item['time'])
        hp.append(float(list_item['Hp']))
        he.append(float(list_item['He']))
        hn.append(float(list_item['Hn']))

    formatted_times = format_times(times)
    print("   - Adding data to plot traces...")
    add_plot_trace(figure, formatted_times, hp, "Hp (northward)", row)
    add_plot_trace(figure, formatted_times, he, "He (earthward)", row)
    add_plot_trace(figure, formatted_times, hn, "Hn (eastward)", row)


def add_kp_data(user_vars, figure, row):
    """
    Add data for GOES measured magnetometer values
    """
    print(" - Adding Kp Data...")
    times, kp_value = ([] for i in range (2))
    kp_data = data_query(user_vars, "kp")

    print("   - Formatting data...")
    for list_item in kp_data['kp']['samples']:
        times.append(list_item['time'])
        kp_value.append(list_item['kp_value'])

    formatted_times = format_times(times)

    print("   - Adding data to plot traces...")
    add_plot_trace(figure, formatted_times, kp_value, "Kp Value", row, True)


def add_dbe_data(user_vars, figure, row):
    """
    Description: Add dbe error data to plot
    Input: Data Object, figure
    Output: None
    """
    print(" - Adding DBE Data...")
    data = DataObject()
    get_ssr_beat_reports(user_vars, data)
    ssra_x_data = list(data.doy_dict_a.keys())
    ssra_y_data = list(data.doy_dict_a.values())
    ssrb_x_data = list(data.doy_dict_b.keys())
    ssrb_y_data = list(data.doy_dict_b.values())

    print("   - Adding data to plot traces...")
    add_plot_trace(figure, ssra_x_data, ssra_y_data, "SSR-A DBEs", row)
    add_plot_trace(figure, ssrb_x_data, ssrb_y_data, "SSR-B DBEs", row)


def add_solar_spots_data(user_vars, figure, row):
    """
    Working On It
    """
    print(" - Adding Solar Spots Data...")

    def solar_spot_data_query():
        """
        Description: Build query URL from user inputs, request data from "Solar Influences 
                     Data Analysis Center Site"
        Output: Panda df of data
        """
        print("""   - Querying for Sun Spot data...""")
        query_url = "https://www.sidc.be/SILSO/INFO/sndtotcsv.php"

        while True:
            try:
                csv_data = requests.get(query_url, timeout=30).content
                break
            except TimeoutError:
                print(" - Error! Data query timed-out, trying again...")

        df = pd.read_csv(io.StringIO(
            csv_data.decode('utf-8')), header=None,
                names=["Year","Month","Day","1","Sunspot Number","2","3","4"],
                delimiter=";"
            )
        df = df.drop(columns = ["1","2","3","4"])
        data_dict = df.to_dict(orient = "list")
        return data_dict

    def format_data(data, user_vars):
        dates, sunspots = ([] for i in range(2))
        zipped_data = zip(data["Year"],data["Month"],data["Day"],data["Sunspot Number"])

        print("   - Truncating data to date range...")
        for (year,month,day,sunspot_num) in zipped_data:
            date = datetime.datetime(year,month,day)

            if user_vars.start_date <= date <= user_vars.end_date:
                dates.append(date)
                sunspots.append(sunspot_num)

        return dates, sunspots

    raw_data = solar_spot_data_query()
    dates, sunspots = format_data(raw_data, user_vars)

    print("   - Adding data to plot traces...")
    add_plot_trace(figure,dates,sunspots,"Solar Spots",row,True,True,opac=0.5)


def generate_plot(user_vars):
    """
    Utilizes user input data to generate Loop Stress Data plot. Then writes as HTML.
    Input: user_vars
    Output: Figure object
    """
    print("\nGenerating GOES Spacecraft Space Weather Data Plot...")

    yaxis_titles = {
        1: ["Electron Flux</br></br>(e-/cm^2-s-sr)"],
        3: ["Proton Flux</br></br>(p+/cm^2-s-sr)", "1 Mev"],
        5: ["Xray Flux</br></br>(W/m^2)"],
        7: ["Magnetometer</br></br>(nT)"],
        9: ["Kp Value", "# of Sunspots"],
        11: ["Recorded DBEs"],
        }

    figure = subplots.make_subplots(
        rows = len(yaxis_titles.keys()), shared_xaxes=True,
        row_heights = [2 for i in range(len(yaxis_titles.keys()))],
        specs = [[{"secondary_y": True}] for i in range(len(yaxis_titles.keys()))]
    )

    add_particle_flux_data(user_vars, figure, 1, 2)
    add_xray_flux_data(user_vars, figure, 3)
    add_magnetometer_data(user_vars, figure, 4)
    add_solar_spots_data(user_vars, figure, 5)
    add_kp_data(user_vars, figure, 5)
    add_dbe_data(user_vars, figure, 6)
    format_plot_axes(user_vars, figure, yaxis_titles)
    return figure


def main():
    "Main Execution"
    while True:
        try:
            user_vars = UserVars()
            figure = generate_plot(user_vars)
            write_html_file(user_vars, figure)
            break
        except KeyboardInterrupt:
            system("clear")
            print("Interrupted plot generation....\n")


main()
