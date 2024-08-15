"Build SBE vs DBE by Date Plot w/ Sun Spots"

import datetime
import io
import requests
import pandas as pd
from plotly import subplots
import plotly.graph_objects as go


def add_solar_spots_data(user_vars):
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

            if user_vars.ts.datetime <= date <= user_vars.tp.datetime:
                dates.append(date)
                sunspots.append(sunspot_num)

        return dates, sunspots

    raw_data = solar_spot_data_query()
    dates, sunspots = format_data(raw_data, user_vars)

    return dates, sunspots


def format_plot(plot):
    "Format things"
    plot["layout"]["yaxis1"]["range"] = (0, 30)
    plot.update_layout(
        title = {
            "text": "SBE vs DBE by Date (SBE minus 42/104)<br>SSR-A: Feb 2024 - Jul 2024",
            "x":0.5,
            "y":0.95,
            "xanchor":"center",
            "yanchor": "top"
        },
        font = {
            "family": "Courier New, monospace",
            "size": 14,
        },
        # plot_bgcolor="rgba(0,0,0,1)",
        # paper_bgcolor="rgba(0,0,0,1)",
        autosize=True,
        showlegend=True,
        hovermode="x unified",
        barmode = "overlay",
        legend = {
            # "bgcolor": "rgba(57,57,57,1)",
            "bordercolor": "black",
            "borderwidth": 1,
            "yanchor":"top",
            "y":0.99,
            "xanchor":"left",
            "x":0.01,
            "font":{"size":20}
        },
    )


def add_plot_trace(plot, x, y, trace_name, opacity=1, secondary_y=False):
    "Add a plot trace as a bar trace"
    plot.add_trace(
    go.Bar(
        x = x,
        y = y,
        name = trace_name,
        opacity = opacity,
    ),
    secondary_y = secondary_y
)


def open_txt_file(base_dir, file):
    "Open a give file by pathway, return data as a dict"
    data = []
    with open(f"{base_dir}/Files/SSR/{file}", encoding = "utf-8") as open_file:
        for line in open_file:
            parsed = line.split()
            date = datetime.datetime.strptime(parsed[0],"%Y%j.%H%M%S%f")

            if parsed[1] == "None":
                error = 0
            else:
                error = int(parsed[1])

            data.append([date, error])

    return data


def truncate_data(user_vars, data_list):
    "Truncate data to date range modules"
    return_data = []
    for data in data_list:
        date, error = data[0], data[1]

        if user_vars.ts <= date <= user_vars.tp:
            return_data.append([date, error])

    return return_data


def process_sbe_data(sbe_mod104_data, sbe_mod042_data, sbe_all_data):
    "Determine how many SBE errors actually occured in the period minus modules 104 & 42"
    corrected_data = []

    for index in range(len(sbe_all_data)):
        corrected_date = sbe_all_data[index][0]
        corrected_data_point = (
            sbe_all_data[index][1] - sbe_mod104_data[index][1] - sbe_mod042_data[index][1])
        corrected_data.append([corrected_date, corrected_data_point])

    return corrected_data


def build_sbe_vs_dbe_solar_date_plot(user_vars):
    "Build the SBE vs DBE per date plot"
    print("Building SBE vs DBE vs Sunspots per date plot...")
    base_dir = user_vars.set_dir
    plot = subplots.make_subplots(
        rows = 1, shared_xaxes=True, row_heights=[1],
        specs = [[{"secondary_y": True}] for i in range(1)]
        )

    # Solar Spot Data
    dates, sunspots = add_solar_spots_data(user_vars)

    # SBE Data
    sbe_mod104_data = truncate_data(user_vars, open_txt_file(base_dir, "SBE-104-mission-daily.txt"))
    sbe_mod042_data = truncate_data(user_vars, open_txt_file(base_dir, "SBE-42-mission-daily.txt"))
    sbe_all_data = truncate_data(user_vars, open_txt_file(base_dir, "SBE-all-mission-daily.txt"))
    corrected_data = process_sbe_data(sbe_mod104_data, sbe_mod042_data, sbe_all_data)

    sbe_x, sbe_y = [],[]
    for data in corrected_data:
        sbe_x.append(datetime.datetime.strptime(data[0].strftime("%Y%j"), "%Y%j"))
        sbe_y.append(data[1])

    # DBE Data
    dbe_data = open_txt_file(base_dir, "DBE-dumped-period-daily.txt")

    dbe_x, dbe_y = [],[]
    for data in dbe_data:
        dbe_x.append(data[0])
        dbe_y.append(data[1])

    add_plot_trace(plot, sbe_x, sbe_y, "SBE by Date")
    add_plot_trace(plot, dbe_x, dbe_y, "DBE by Date")
    add_plot_trace(plot, dates, sunspots, "Sunspots", 0.2, True)
    format_plot(plot)
    plot.write_html(f"{base_dir}/Output/SBE_vs_DBE_by_Date.html")
