"Build SSR DBE & SEU by submodule plots"

import plotly.graph_objects as go


def format_plot(plot, user_vars):
    "Format things how I want them"

    plot_title = (f"SBE vs DBE by Submodule SSR-{user_vars.prime_ssr}<br>"
                   f"{user_vars.ts.datetime.strftime('%B %Y')} - "
                   f"{user_vars.tp.datetime.strftime('%B %Y')}")

    plot.update_yaxes(
        range=(-0.5, 18),
        constrain='domain'
        )
    plot.update_layout(
        title = {"text": f"{plot_title}","x":0.5,"y":0.95,"xanchor":"center","yanchor": "top"},
        font = {"family": "Courier New, monospace","size": 20},
        autosize=True,
        showlegend=True,
        hovermode="x unified",
        barmode = "overlay",
        legend = {"bordercolor": "black","borderwidth": 1,"yanchor":"top",
                  "y":0.99,"xanchor":"left","x":0.01,"font":{"size":20}}
        )
    plot.update_yaxes(title = {"text":"SBE/DBE Count","font":{"size":20}})
    plot.update_xaxes(title = {"text":"Submodule","font":{"size":20}})


def add_plot_trace(plot, x, y, trace_name):
    "Add a plot trace as a Bar graph"
    plot.add_trace(
    go.Bar(
        x = x,
        y = y,
        name = trace_name,
    ))


def build_sbe_vs_dbe_submod_plot(user_vars):
    "Build the SBE vs DBE per submodule plot"
    print("Building SBE vs DBE per submodule plot...")
    base_dir = user_vars.set_dir
    files = ["SBE-all-period-submod.txt","DBE-dumped-period-submod.txt"]
    data_dict = {}
    plot = go.Figure()

    for file in files:
        with open(f"{base_dir}/Files/SSR/{file}", encoding="utf-8") as open_file:
            for line in open_file:
                parsed = line.split()
                if "SBE" in file:
                    error_type = "SBE"
                elif "DBE" in file:
                    error_type = "DBE"
                else:
                    error_type = None
                data_dict.setdefault(f"{error_type}", []).append({int(parsed[0]):int(parsed[1])})

    sbe_x, sbe_y = [],[]
    for errors in data_dict["SBE"]:
        for submodule, sbe in errors.items():
            sbe_x.append(submodule)
            sbe_y.append(sbe)

    dbe_x, dbe_y = [],[]
    for errors in data_dict["DBE"]:
        for submodule, sbe in errors.items():
            dbe_x.append(submodule)
            dbe_y.append(sbe)

    add_plot_trace(plot, sbe_x, sbe_y, "SBE by Submodule")
    add_plot_trace(plot, dbe_x, dbe_y, "DBE by Submodule")
    format_plot(plot, user_vars)
    plot.write_html(f"{base_dir}/Output/SBE_vs_DBE_by_Submodule.html")
