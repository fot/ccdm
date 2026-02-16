"Plotting Methods for MSID Plotter Tool"

import plotly.graph_objects as go
from plotly import subplots
from components.formatting import format_times, format_plot_axes
from components.data import data_request


def generate_plot(user_vars):
    """
    Description: Generates plot using user inputed variables for MSIDs
    Input: User Variables
    Output: Plot object
    """
    print("""\nGenerating plot ("ctrl + c" to cancel)...""")
    plot = subplots.make_subplots(
        rows = len(user_vars.msids), shared_xaxes = "columns",
        specs = [[{}] for i in range(len(user_vars.msids))], vertical_spacing = 0.05)

    for index, (msid) in enumerate(user_vars.msids):
        raw_data = data_request(user_vars, msid)
        formated_times = format_times(raw_data, user_vars)

        if user_vars.data_source in "MAUDE Web":
            y_values = [eval(i) for i in (raw_data["data-fmt-1"]["values"])]
            title = raw_data["data-fmt-1"]["n"]
        else:
            y_values = raw_data.vals
            title = f"{raw_data.msid} ({raw_data.unit})"

        plot.add_trace(
            go.Scatter(
                x = formated_times,
                y = y_values,
                mode = "lines",
                name = title,
            ),
            row = index + 1, col = 1,
            )

    format_plot_axes(plot, user_vars)

    return plot
