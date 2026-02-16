"Methods to plot things"

import plotly.graph_objects as go


def add_plot_trace(figure,x_values,y_values,title,row,bar_graph=False,sec_y=None,opac=1):
    """
    Description: Add a trace to the plot
    Inputs: Figure, x_values list, y_values list, trace title string
    """
    if bar_graph:
        figure.add_trace(
        go.Bar(
            x = x_values,
            y = y_values,
            name = title,
            opacity = opac,
        ),
        row = row, col=1,
        secondary_y = sec_y,
        )
    else:
        figure.add_trace(
            go.Scatter(
                x = x_values,
                y = y_values,
                mode = "lines",
                name = title,
            ),
        row = row, col=1,
        secondary_y = sec_y,
        )
