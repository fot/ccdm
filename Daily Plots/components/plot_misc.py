"Plotting Misc Methods"

import plotly.graph_objects as go
from cxotime import CxoTime
from components.tlm_request import data_request


def format_times(raw_data,user_vars):
    """
    Description: Formats times list into a readable format.
    Input: Raw data dict
    Output: Builds new list of formated time items.
    """
    formated_times = []

    if user_vars.data_source in "MAUDE Web":
        times_list = raw_data["data-fmt-1"]["times"]
        time_format = "maude"
    else:
        times_list = raw_data.times
        time_format = None

    for time_item in times_list:
        new_list_item = CxoTime(time_item,format=time_format)
        formated_times.append(new_list_item.datetime)

    return formated_times


def format_plot_axes(figure,plot_title,yaxis_titles):
    """
    Description: Formats plot axies based on string inputs
    Input: Plot <object>, plot_title <str>, yaxis_titles <str>
    Output: None
    """
    print(" - Making things look pretty...")

    for yaxis_number, yaxis_label in yaxis_titles.items():
        figure["layout"][f"yaxis{yaxis_number}"]["title"] = yaxis_label

        figure.update_layout(
            {f"xaxis{yaxis_number}": {"matches": "x", "showticklabels": True}}
        )

    figure.update_xaxes(gridcolor="rgba(80,80,80,1)",autorange=True)
    figure.update_yaxes(gridcolor="rgba(80,80,80,1)",autorange=True)
    figure.update_layout(
        title=plot_title,
        font={
            "family": "Courier New, monospace",
            "size": 14,
            "color": "rgba(255,255,255,1)",
        },
        plot_bgcolor="rgba(0,0,0,1)",
        paper_bgcolor="rgba(0,0,0,1)",
        autosize=True,
        showlegend=False,
        hovermode="x unified",
    )


def add_plot_trace(user_vars,msid,figure,rows,cols,trace_title=False):
    "Add a plot trace per given MSID list and plot location"
    raw_data = data_request(user_vars, msid)
    formatted_times = format_times(raw_data, user_vars)

    if user_vars.data_source in "MAUDE Web":
        y_values = [eval(i) for i in (raw_data["data-fmt-1"]["values"])]
        title = raw_data["data-fmt-1"]["n"]
    else:
        y_values = raw_data.vals
        title = f"{raw_data.msid} ({raw_data.unit})"
    if trace_title:
        title = trace_title

    figure.add_traces(
        go.Scatter(
            x = formatted_times,
            y = y_values,
            mode = "lines",
            name = title
        ),
        rows = rows, cols = cols
    )
