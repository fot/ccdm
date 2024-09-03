"VC0_VC1 Slip Detector Tool"

import urllib
import json
import time
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go
import selenium
from selenium import webdriver


class UserVariables():
    "Variables defined by the user!"

    def __init__(self):

        # Realtime
        self.ts, self.tp = datetime.now()-timedelta(seconds=10), datetime.now()

        # # bad comm (1) (2024:198:11:00:00 thru 2024:198:12:06:00)
        # self.tp = datetime.strptime("2024:198:11:50:00", "%Y:%j:%H:%M:%S")
        # self.ts = self.tp - timedelta(seconds=10)

        # # bad comm (2) (2024:200:10:20:00 thru 2024:200:11:30:00)
        # self.tp = datetime.strptime("2024:200:10:20:00", "%Y:%j:%H:%M:%S")
        # self.ts = self.tp - timedelta(seconds=10)

        # # A good comm (1) (2024:199:00:05:00 thru 2024:199:02:00:00)
        # self.tp = datetime.strptime("2024:199:00:05:00", "%Y:%j:%H:%M:%S")
        # self.ts = self.tp - timedelta(seconds=10)

        # # A good comm (2) (2024:199:10:27:00 thru 2024:199:11:47:00)
        # self.tp = datetime.strptime("2024:199:10:27:00", "%Y:%j:%H:%M:%S")
        # self.ts = self.tp - timedelta(seconds=10)


def data_request(user_vars, msid):
    """
    Description: Data request for a general timeframe and MSID, returns json or data dict
    Input: User Variables, MSID
    Output: Data dict or JSON
    """
    ts_greta = user_vars.ts.strftime("%Y%j.%H%M%S")
    tp_greta = user_vars.tp.strftime("%Y%j.%H%M%S")
    base_url = "https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m="
    url = f"{base_url}{msid}&ts={ts_greta}&tp={tp_greta}"

    try:
        response = urllib.request.urlopen(url)
    except urllib.error.URLError:
        print(" - Network error. Some data will be missing in plot")

    html = response.read()
    return json.loads(html)


def vc0_vc1_slip_detection(raw_data):
    "In work"
    values = raw_data["data-fmt-1"]["values"]
    times =  raw_data["data-fmt-1"]["times"]
    diff_list = []

    for index, (raw_value, raw_time) in enumerate(zip(values, times)):
        corrected_time = datetime.strptime(str(raw_time), "%Y%j%H%M%S%f")
        value = int(raw_value)
        previous_value = int(values[index - 1])
        diff = value-previous_value

        if value != 0:
            try:
                if (
                    (value != previous_value) and
                    (diff > 5) and
                    (diff in range(56,61) or diff in range(95,100))
                ):
                    diff_list.append([corrected_time, diff])
            except IndexError:
                pass

    return diff_list


def append_data_history(history_data, raw_data):
    "Save data history while tool is running"
    values = raw_data["data-fmt-1"]["values"]
    times =  raw_data["data-fmt-1"]["times"]

    for raw_time, value in zip(times, values):
        corrected_time = datetime.strptime(str(raw_time), "%Y%j%H%M%S%f")
        history_data.append([corrected_time, int(value)])

    return history_data


def generate_plot(detected_slips, data_history, base_dir):
    "Generate static image of dataframe"
    x_values, y_values = ([] for i in range(2))
    plot = go.Figure()

    # Slip Detected Plot
    if detected_slips:
        plot.add_annotation(
            text = "---VC0/VC1 Slip Detection---<br>      SLIP IS OCCURING",
            xref="paper", yref="paper",
            x=0.4, y=1.077, showarrow=False,
            align="left", bordercolor="black", borderwidth=2, borderpad=4,
            bgcolor="red", opacity=0.8,
            font = {"family": "Courier New, monospace", "size": 56, "color": "white"}
            )
    else:
        plot.add_annotation(
            text = "---VC0/VC1 Slip Detection---<br>      NO slip occuring",
            xref="paper", yref="paper",
            x=0.4, y=1.077, showarrow = False,
            align="left", bordercolor="black", borderwidth = 2, borderpad = 4,
            bgcolor="white", opacity = 0.8, 
            font = {"family": "Courier New, monospace", "size": 56, "color": "black"}
            )

    # Monitor Data History Plot
    for item in data_history:
        x_values.append(item[0])
        y_values.append(item[1])

    plot.add_traces(
        go.Scatter(
            x = x_values,
            y = y_values,
            mode = "lines",
            name = "VC0/VC1 Slip",
        )
    )

    plot["layout"]["xaxis"]["title"] = "Time/Date"
    plot["layout"]["yaxis"]["title"] = "Monitor Data (M0190)"
    plot.update_xaxes(gridcolor="rgba(80,80,80,1)")
    plot.update_yaxes(gridcolor="rgba(80,80,80,1)")
    plot.update_layout(
        font={
            "family": "Courier New, monospace",
            "size": 14,
            "color": "rgba(255,255,255,1)",
        },
        plot_bgcolor =  "rgba(0,0,0,1)",
        paper_bgcolor = "rgba(0,0,0,1)",
        width =  1920,
        height = 1080,
    )

    plot.write_image(f"{base_dir}/VC0_VC1_Slips_Detected.png")


def save_data(data_history, base_dir):
    "Clean up things"

    with open(f"{base_dir}/output.txt", "w", encoding = "utf-8") as file:
        file.write("-----------Time-----------  |  --Value--\n")
        for item in data_history:
            file.write(f"{item[0]}  |   {item[1]}\n")
        file.close()


def startup_cleanup(base_dir):
    "Clean up lingering files from previous run"
    try:
        os.remove(f"{base_dir}/VC0_VC1_Slips_Detected.png")
    except FileNotFoundError:
        pass

    try:
        os.remove(f"{base_dir}/output.txt")
    except FileNotFoundError:
        pass


def main():
    "Main Execution"
    print("---VC0/VC1 Slip Detection Tool---")
    base_dir = "//noodle/FOT/engineering/ccdm/Tools/VC0_VC1 Slip Detector"
    # base_dir = "/share/FOT/engineering/ccdm/Tools/VC0_VC1 Slip Detector"
    data_history = []
    driver = webdriver.Chrome()
    # user_vars = UserVariables()
    startup_cleanup(base_dir)

    try:
        while True:
            user_vars = UserVariables()
            print(f" - {user_vars.ts} (Enter ctrl + c to exit tool)")

            raw_data = data_request(user_vars, "M0190")
            data_history = append_data_history(data_history, raw_data)
            detected_slips = vc0_vc1_slip_detection(raw_data)
            generate_plot(detected_slips, data_history, base_dir)

            try:
                driver.get(f"{base_dir}/VC0_VC1_Slips_Detected.png")
            except selenium.common.exceptions.NoSuchWindowException:
                driver = webdriver.Chrome()
                driver.get(f"{base_dir}/VC0_VC1_Slips_Detected.png")
                print(" - Don't close the window. \U0001F440")

            # # Crude shifting time window (for testing)
            # user_vars.ts += timedelta(seconds=10)
            # user_vars.tp += timedelta(seconds=10)
            os.remove(f"{base_dir}/VC0_VC1_Slips_Detected.png")
            time.sleep(10)

    except KeyboardInterrupt:
        print("Ending Script!")
        save_data(data_history, base_dir)


main()
