"Generate Average SBE on Submodule 104 Plot (Used when SSR-A Was prime for the period)"

from datetime import datetime
import plotly.graph_objects as go


def format_plot(plot, user_vars):
    "fix the layout of things"

    plot_title = (f"Average Daily SBE for SSR-{user_vars.prime_ssr}<br>"
                   f"{user_vars.ts.datetime.strftime('%B %Y')} - "
                   f"{user_vars.tp.datetime.strftime('%B %Y')}")

    plot.update_layout(
        title = {"text": f"{plot_title}","x":0.5, "y":0.95,"xanchor":"center","yanchor": "top"},
        font = {"family": "Courier New, monospace","size": 14},
        autosize=True,
        showlegend=True,
        hovermode="x unified",
        legend = {"bordercolor": "black","borderwidth": 1,"yanchor":"top",
                  "y":0.99,"xanchor":"left","x":0.01,"font":{"size":20}},
        )
    plot.update_traces(marker = {"size":20})
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
        ["2012:214","2013:031"],["2013:031","2013:213"],["2013:213","2014:031"],
        ["2014:031","2014:213"],["2015:031","2015:213"],["2016:031","2016:214"],
        ["2017:031","2017:213"],["2018:031","2018:213"],["2019:031","2019:213"],
        ["2020:031","2020:214"],["2021:031","2021:213"],["2022:031","2022:213"],
        ["2023:031","2023:213"],["2024:031","2024:214"],["2025:031","2025:213"],
        ["2025:214","2026:031"]]

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
    format_plot(plot, user_vars)
    plot.write_html(f"{base_dir}/Output/Avg_SBE_Submod104.html")
