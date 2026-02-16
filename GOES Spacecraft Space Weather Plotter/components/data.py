"Methods to query data for the Space Weather Plotter Tool"

import urllib.request
import json


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
