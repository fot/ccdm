import os
import signal
from os import system
import time
import json
import urllib.request
from tqdm import tqdm
from cxotime import CxoTime
import plotly.graph_objects as go
from Ska.engarchive import fetch_eng as fetch


class UserVariables:
    "Class to store user variable inputs."
    def __init__(self):

        while True:
            system("clear")
            self.msids = get_msids()
            self.year_start = get_year_start()
            self.doy_start = get_doy_start()
            self.year_end = get_year_end()
            self.doy_end = get_doy_end()
            self.get_times()
            self.show_plot = get_show_plot()
            self.data_source = get_data_source()
            self.plot_title, self.file_title = get_titles(self)
            input_status = input("\nAre these inputs correct? Y/N: ")

            if input_status in ("Y","y","Yes","yes"):
                break
            print("\nRestarting Inputs...\n\n")
            time.sleep(1.5)

    def get_times(self):
        "Generate time objects from user inputs."
        self.ts = CxoTime(self.year_start+":"+self.doy_start+":00:00:00")
        self.tp = CxoTime(self.year_end+":"+self.doy_end+":23:59:59.999")


def get_msids():
    """
    Description: Build list of MSIDs from user inputs
    Input: User input string of MSID
    Output: List of inputted MSIDs
    """
    print("Enter the MSIDs you wish to plot, press ENTER after each MSID inputted. "
            "MSID1 -> enter, MSIDx -> enter\n"
            """-- A blank input will finish inputing MSID(s). --\n""")
    msid_list = []

    while True:
        msid_input = input("Enter MSID: ").upper()

        # Checking if user ending input of MSID(s)
        if msid_input in ("") and (len(msid_list) != 0):
            break

        # Check input for blank MSID input
        if (msid_input in ("")) and (len(msid_list) == 0):
            print(" - Error! You must enter at least one MSID...\n")

        # Check if input is a duplicate MSID input
        elif msid_input in msid_list:
            print(f""" - Error! MSID "{msid_input}" was already entered...\n""")

        # Check if an input is NOT an MSID
        elif not check_msid_validity(msid_input):
            print(f""" - Error! "{msid_input}" was an invalid MSID input """
                  "\U0001F62D. Please try again.\n"
                )

        # Check if input is a valid MSID, if so save input
        elif check_msid_validity(msid_input):
            msid_list.append(msid_input)

    return msid_list


def get_year_start():
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


def get_year_end():
    "Get user input for end year"
    while True:
        year_input = input("Enter the END year: XXXX ")
        if (len(str(year_input)) == 4) and (1998 <= int(year_input) <= 2040):
            break
        print(f"{year_input} was an invalid input, please try again")
    return year_input


def get_doy_end():
    "Get user input for DOY end"
    while True:
        doy_input = input("Enter the END day: XXX ")
        if (len(str(doy_input)) == 3) and (1 <= int(doy_input) <= 366):
            break
        print(f"{doy_input} was an invalid input, please try again\n")
    return doy_input


def get_show_plot():
    "Show plot toggle"
    return input("Do you wish to display plot? Y/N: ")


def get_data_source():
    "Get user input on whether to use high rate data or not"
    while True:
        data_source = input(
            """\n--Select Data Source--\n"""
            """   Enter "1" if you'd like high rate SKA data """
            """(Caution: will slow down plot generation).\n"""
            """   Enter "2" if you'd like abbreviated SKA data\n"""
            """   Enter "3" if you'd like MAUDE Web data\n"""
            """   Input: """
            )
        if "1" in data_source:
            return "High Rate SKA"
        if "2" in data_source:
            return "Abbreviated SKA"
        if "3" in data_source:
            return "MAUDE Web"
        print(f"""{data_source} was an invalid input \U0001F62D, please try again""")


def get_titles(self):
    """
    Descrition: Get user input for non-default file title
    Input: # of MSIDs inputted
    Output: [string] of file title
    """
    if len(self.msids) <= 5: # Just chose 5 MSIDs as max
        plot_title = (
            f"MSIDs {self.msids} from "
            f"{self.year_start}:{self.doy_start} to "
            f"{self.year_end}:{self.doy_end} ({self.data_source})"
        )
        file_title = ""
        for msid in self.msids:
            file_title += msid + "_"

        file_title += (
            f"({self.year_start}{self.doy_start}_"
            f"{self.year_end}{self.doy_end}) "
            f"({self.data_source}).html"
        )

    else:
        print("\nToo many MSIDs entered for default naming convention...")
        while True:
            plot_title = input(
                """ - Please input a new "PLOT TITLE". """
                "(Note: dates & data source will get auto added to name.)\n"
                " - Input: "
                )
            plot_title += (
                f" ({self.year_start}" + f"{self.doy_start}" + "_" +
                f"{self.year_end}" + f"{self.doy_end})" + f" ({self.data_source})"
            )
            if input(f""" - Accept "{plot_title}" as the plot title? Y/N: """) in ("Y", "y"):
                break

        while True:
            file_title = input(
                """\n - Please input a new FILE TITLE. """
                "(Note: dates & data source will get auto added to name.)\n"
                " - Input: "
                )
            file_title += (
                f" ({self.year_start}" + f"{self.doy_start}" + "_" +
                f"{self.year_end}" + f"{self.doy_end})" +
                f" ({self.data_source})" + ".html"
            )
            if input(f""" - Accept "{file_title}" as the file title? Y/N: """) in ("Y","y"):
                break

    return plot_title, file_title


def check_msid_validity(msid_input):
    """
    Description: Check if an MSID is valid. Do a mini MAUDE url request on MSID.
    Input: MSID
    Output: True/False
    """
    url = (
        f"https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/"
        f"msid.json?m={msid_input}&ts=2024:001:00:00:00.000&tp=2024:001:00:00:05.000"
    )
    try:
        urllib.request.urlopen(url)
        return True
    except BaseException:
        return False


def data_request(user_vars,msid):
    """
    Description: Data request for a general timeframe and MSID, returns json or data dict
    Input: User Variables, MSID
    Output: Data dict or JSON
    """
    print(f" - Requesting {user_vars.data_source} data for {msid}...")
    user_vars.ts.format = "yday"
    user_vars.tp.format = "yday"
    base_url = "https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m="

    if user_vars.data_source in ("High Rate SKA","Abbreviated SKA"):
        fetch.data_source.set("maude")
        if user_vars.data_source in ("High Rate SKA"):
            fetch.data_source.set("maude allow_subset=False")
        else:
            fetch.data_source.set("maude allow_subset=True")
        data = fetch.MSID(f"{msid}",user_vars.ts,user_vars.tp)
    else:
        url = base_url + msid + "&ts=" +str(user_vars.ts.value) + "&tp=" + str(user_vars.tp.value)
        response = urllib.request.urlopen(url)
        html = response.read()

    return data if not user_vars.data_source in ("MAUDE Web") else json.loads(html)


def format_times(raw_data,user_vars):
    "Formats a list of time into a plottable format."
    print("  - Formatting Data...")
    formated_times = []

    if user_vars.data_source in "MAUDE Web":
        times_list = raw_data["data-fmt-1"]["times"]
        time_format = "maude"
    else:
        times_list = raw_data.times
        time_format = None

    for time_item in tqdm(times_list):
        new_list_item = CxoTime(time_item,format=time_format)
        formated_times.append(new_list_item.datetime)

    return formated_times


def format_plot_axes(plot, plot_title):
    """
    Description: Formats plot axies based on string inputs
    Input: Plot, Plot title (string)
    Output: None
    """
    plot["layout"]["xaxis"]["title"] = "Time/Date"
    plot["layout"]["yaxis"]["title"] = "MSID Value"
    plot.update_xaxes(gridcolor="rgba(80,80,80,1)")
    plot.update_yaxes(gridcolor="rgba(80,80,80,1)")
    plot.update_layout(
        title=plot_title,
        font={
            "family": "Courier New, monospace",
            "size": 14,
            "color": "rgba(255,255,255,1)",
        },
        plot_bgcolor="rgba(0,0,0,1)",
        paper_bgcolor="rgba(0,0,0,1)",
        autosize=True,
        hovermode="x unified",
    )


def generate_plot(user_vars):
    """
    Description: Generates plot using user inputed variables for MSIDs
    Input: User Variables
    Output: Plot object
    """
    print("""\nGenerating plot ("ctrl + c" to cancel)...""")
    plot = go.Figure()

    for msid in user_vars.msids:
        raw_data = data_request(user_vars,msid)
        formated_times = format_times(raw_data,user_vars)

        if user_vars.data_source in "MAUDE Web":
            y_values = [eval(i) for i in (raw_data["data-fmt-1"]["values"])]
            title = raw_data["data-fmt-1"]["n"]
        else:
            y_values = raw_data.vals
            title = f"{raw_data.msid} ({raw_data.unit})"

        plot.add_traces(
            go.Scatter(
                x = formated_times,
                y = y_values,
                mode = "lines",
                name = title,
            )
        )

    format_plot_axes(plot, user_vars.plot_title)

    if user_vars.show_plot in ("Y","y","Yes","yes"):
        plot.show()

    return plot


def generate_html_output(user_vars,plot):
    "Takes plot object and write to an HTML file in output directory."

    print("\nGenerating html output file.....")
    plot.write_html(
        f"/home/rhoover/python/General Trending/MSID Plotter/Output/{user_vars.file_title}"
    )
    print(f""" - Done! Data written to "{user_vars.file_title}" in output directory.""")


def user_menu():
    "User menu for some choices"
    while True:
        user_choice = input(
            """\nWhat would you like to do next? Input to continue.\n"""
            """1) Restart Inputs\n"""
            """0) Exit Tool\n"""
            """Input: """
        )
        if user_choice in ("1","0"):
            break
        print(
            f"""\n"{user_choice}" was an invalid input.\nplease input 
            a single digit interger that is 1 or 0."""
            )

    return user_choice


def cleanup():
    """
    Description: Clean up processes after script execution
    """
    print("\nScript Cleanup...")
    os.kill(os.getpid(), signal.SIGKILL)


def main():
    "Main execution"
    while True:
        user_vars = UserVariables()

        try:
            plot = generate_plot(user_vars)
            generate_html_output(user_vars, plot)
        except KeyboardInterrupt: # handle canceling plot generation
            system("clear")
            print("Interrupted plot generation....\n")

        if user_menu() in ("0"):
            break


main()
cleanup()
