"Generate Average SBE on Submodule 104 Plot (Used when SSR-A Was prime for the period)"

from datetime import datetime
import plotly.graph_objects as go


def format_plot(plot):
    "fix the layout of things"
    plot.update_layout(
        title = {
            "text": "Average Daily SBE for SSR-A Submodule 104<br>(Aug 2012 - Jul 2024)",
            "x":0.5, "y":0.95,
            "xanchor":"center",
            "yanchor": "top"
        },
        font = {
            "family": "Courier New, monospace",
            "size": 14,
        },
        # plot_bgcolor="rgba(0,0,0,1)",
        # paper_bgcolor="rgba(0,0,0,1)",
        autosize=True,
        showlegend=True,
        hovermode="x unified",
        legend = {
            # "bgcolor": "rgba(57,57,57,1)",
            "bordercolor": "black",
            "borderwidth": 1,
            "yanchor":"top",
            "y":0.99,
            "xanchor":"left",
            "x":0.01,
            "font":{"size":20}
        },
    )
    plot.update_traces(
        marker = {"size":20}
    )
    plot.update_yaxes(title = {"text":"Average Daily SBE Count"})
    plot.update_xaxes(title = {"text":"Biannual Period"})


def add_plot_trace(plot, x, y, trace_name):
    "Write a trace as a scatter plot"
    plot.add_trace(
    go.Scatter(
        x = x,
        y = y,
        name = trace_name,
        mode = "markers"
    )
)


def open_txt_file(base_dir, file):
    "Open a give file by pathway, return data as a dict"
    data = []
    with open(f"{base_dir}/Files/SSR/{file}", encoding="utf-8") as open_file:
        for line in open_file:
            parsed = line.split()
            date = datetime.strptime(parsed[0],"%Y%j.%H%M%S%f")

            if parsed[1] == "None":
                error = 0
            else:
                error = int(parsed[1])

            data.append([date, error])

    return data


def truncate_data(user_vars, data_list):
    "Truncate data to date range modules"
    return_data = []
    for data in data_list:
        date, error = data[0], data[1]
        start_date = datetime.strptime("2012:214:00:00:00", "%Y:%j:%H:%M:%S")

        if start_date <= date <= user_vars.tp:
            return_data.append([date, error])

    return return_data


def build_sbe_mod104_avg_plot(user_vars):
    "build the Average SBEs on submodule 104 plot"
    print("Building Average SBE perday for Submodule 104 Plot...")

    base_dir = user_vars.set_dir
    plot = go.Figure()

    # Mission sbe submodule 104 data.
    sbe_mod104_data = truncate_data(user_vars, open_txt_file(base_dir, "SBE-104-mission-daily.txt"))

    period_range = [
        ["2012:214","2013:032"],["2013:032","2013:213"],["2013:213","2014:032"],
        ["2014:032","2014:213"],["2015:032","2015:213"],["2016:032","2016:214"],
        ["2017:032","2017:213"],["2018:032","2018:213"],["2019:032","2019:213"],
        ["2020:032","2020:214"],["2021:032","2021:213"],["2022:032","2022:213"],
        ["2023:032","2023:213"],["2024:032","2024:214"]]

    # Build averages per period
    sbe_average = []
    for period in period_range:
        count, sum_value = 0, 0
        for data in sbe_mod104_data:
            date = data[0]
            sbe  = data[1]
            period_start_date = datetime.strptime(period[0],"%Y:%j")
            period_end_date   = datetime.strptime(period[1],"%Y:%j")

            if period_start_date <= date <= period_end_date:
                count += 1
                sum_value += sbe

        sbe_average.append([period,sum_value/count])

    sbe_avg_x, sbe_avg_y = [],[]
    for data in sbe_average:
        sbe_avg_x.append(f"{data[0][0]} thru {data[0][1]}")
        sbe_avg_y.append(data[1])

    add_plot_trace(plot, sbe_avg_x, sbe_avg_y, "Average SBE for SSR-A Submodule 104")
    format_plot(plot)
    plot.write_html(f"{base_dir}/Output/Avg_SBE_Submod104.html")
