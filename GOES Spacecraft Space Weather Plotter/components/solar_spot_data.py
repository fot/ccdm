"Methods to add Solar Spot Data to Plot"

import requests
import io
import pandas as pd
from datetime import datetime
from components.plotting import add_plot_trace


def add_solar_spots_data(user_vars, figure, row):
    """
    Working On It
    """
    print(" - Adding Solar Spots Data...")
    raw_data = solar_spot_data_query()
    dates, sunspots = format_data(raw_data, user_vars)
    print("   - Adding data to plot traces...")
    add_plot_trace(figure,dates,sunspots,"Solar Spots",row,True,True,opac=0.5)


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
    "Format data for solar spots"
    dates, sunspots = ([] for i in range(2))
    zipped_data = zip(data["Year"],data["Month"],data["Day"],data["Sunspot Number"])

    print("   - Truncating data to date range...")
    for (year,month,day,sunspot_num) in zipped_data:
        date = datetime(year,month,day)

        if user_vars.start_date <= date <= user_vars.end_date:
            dates.append(date)
            sunspots.append(sunspot_num)

    return dates, sunspots
