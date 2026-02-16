"Methods to format things for the Space Weather Plotter Tool"

from datetime import datetime


def format_times(times_list):
    "Formats a list of time into a plottable format."
    input_format = "%Y-%m-%d %H:%M"
    formatted_times = []

    for time_item in times_list:
        new_list_item = datetime.strptime(time_item, input_format)
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
