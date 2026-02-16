"Module to generate PA vs BPT plots for CCDM Biannual Report"

import plotly.graph_objects as go
from components.misc import parse_csv_file, write_png_file, write_html_file


def generate_pa_bpt_plots(user_vars):
    "Generate Power Amp versus Baseplate temp plot."

    print("Generating PA vs. BPT Plot...")

    df_means = parse_csv_file(f"{user_vars.set_dir}/Output/period_means.csv")
    txapwr = df_means.loc[:,'CTXAPWR']
    txbpwr = df_means.loc[:,'CTXBPWR']
    cpa1bpt = df_means.loc[:,'CPA1BPT']
    cpa2bpt = df_means.loc[:,'CPA2BPT']

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x = cpa1bpt, y = txapwr, name="TX-A Power vs. PA Baseplate Temp",
            mode="markers",marker={"size":12},line={"color":"blue", "width":3}
            )
        )
    figure.add_trace(
        go.Scatter(
            x = cpa2bpt, y = txbpwr, name="TX-B Power vs. PA Baseplate Temp",
            mode="markers",marker={"size":12},line={"color":"orange", "width":3}
            )
        )

    figure["layout"]["yaxis1"]["range"] = ((txapwr.min() - 0.05), (txbpwr.max() + 0.1))
    figure.update_layout(
            title = {
                "text": "Daily Mean Tx Output Power vs. Daily Mean Base Plate Temperature",
                "x":0.5, "y":0.95,
                "xanchor":"center", "yanchor": "top"
            },
            xaxis_title="Baseplate Temperature (degF)",
            yaxis_title="Tx Output Power (dBm)",
            autosize=True,
            legend={
                "yanchor":"top",
                "y":0.99,
                "xanchor":"left",
                "x":0.01
                },
            font={
                "family":"Courier New, monospace",
                "size":18,
                "color":"RebeccaPurple"
                }
            )

    write_html_file(user_vars, figure, f"{user_vars.end_year}b_TX_BPT.html")
