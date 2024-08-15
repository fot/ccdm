"Plotting Methods for MSID Plotter Tool"

import plotly.graph_objects as go
from components.formatting import format_times, format_plot_axes
from components.data import data_request


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
