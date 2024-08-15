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
        self.start_date = datetime.datetime.now() - datetime.timedelta(14)
        self.end_date = datetime.datetime.now()
        self.start_doy = self.start_date.timetuple().tm_yday
        self.start_year = self.start_date.year
        self.end_doy = self.end_date.timetuple().tm_yday
        self.end_year = self.end_date.year


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
        "GOES Space Weather Plot (14-Day Lookback)"
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
        # 9: ["Kp Value", "# of Sunspots"],
        }

    figure = subplots.make_subplots(
        rows = len(yaxis_titles.keys()), shared_xaxes=True,
        row_heights = [2 for i in range(len(yaxis_titles.keys()))],
        specs = [[{"secondary_y": True}] for i in range(len(yaxis_titles.keys()))]
    )

    add_particle_flux_data(user_vars, figure, 1, 2)
    add_xray_flux_data(user_vars, figure, 3)
    add_magnetometer_data(user_vars, figure, 4)
    # add_solar_spots_data(user_vars, figure, 5)
    # add_kp_data(user_vars, figure, 5)
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
