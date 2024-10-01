"Formatting Methods for MSID Plotter Tool"

from tqdm import tqdm
from cxotime import CxoTime


def format_times(raw_data, user_vars):
    "Formats a list of time into a plottable format."
    print("  - Formatting Data...")
    formated_times = []

    if user_vars.data_source in "MAUDE Web":
        times_list = raw_data["data-fmt-1"]["times"]
        time_format = "maude"
    else:
        times_list = raw_data.times
        time_format = None

    for time_item in tqdm(times_list, bar_format = "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        new_list_item = CxoTime(time_item, format=time_format)
        formated_times.append(new_list_item.datetime)

    return formated_times


def format_plot_axes(plot, user_vars):
    """
    Description: Formats plot axies based on string inputs
    Input: Plot, user variables
    Output: None
    """
    plot["layout"][f"xaxis{len(user_vars.msids)}"]["title"] = "Time/Date"

    for index, (msid) in enumerate(user_vars.msids):
        plot["layout"][f"yaxis{index + 1}"]["title"] = f"{msid}"

    plot.update_xaxes(gridcolor="rgba(80,80,80,1)")
    plot.update_yaxes(gridcolor="rgba(80,80,80,1)")
    plot.update_layout(
        title=user_vars.plot_title,
        font={
            "family": "Courier New, monospace",
            "size": 14,
            "color": "rgba(255,255,255,1)",
        },
        plot_bgcolor="rgba(0,0,0,1)",
        paper_bgcolor="rgba(0,0,0,1)",
        autosize=True,
        hoversubplots = "axis",
        hovermode = "x unified",
    )


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
