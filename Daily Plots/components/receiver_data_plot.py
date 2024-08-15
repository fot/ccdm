"Methods to generate the Reveiver Data Plots"

from tqdm import tqdm
from plotly import subplots
from components.misc import write_html_file
from components.plot_misc import format_plot_axes, add_plot_trace
from components.range_data_plot import add_chandra_range_plots


def generate_receiver_data_plots(user_vars, auto_gen = False):
    """
    Description: Generates Receiver Data Plot
    Input: User input data
    Output: HTML output file of plots
    """
    print("\nGenerating Receiver Data Plot...")
    figure = subplots.make_subplots(
        rows=5,cols=2,shared_xaxes="columns",row_heights=[10,2,1,10,2],
        subplot_titles=(
            "Loop Stress Data","Receiver Signal Strength Data","","","","",
            "Receiver Secondary Voltage Data","Chandra Ranging Data"
            )
        )

    if auto_gen:
        figure_title = (
            "Chandra CCDM Daily Plots - Receiver Data (Auto-Gen 14-Day Lookback)"
            )
    else:
        figure_title = (
            "Chandra CCDM Daily Plots - Receiver Data" +
            f" ({user_vars.year_start}" + f"{user_vars.doy_start}" + "_" +
            f"{user_vars.year_end}" + f"{user_vars.doy_end}" + f" {user_vars.data_source})"
            )

    yaxis_titles = {
        1:"kHz",2:"dBm",3:"NLCK/LOCK",4:"NLCK/LOCK",
        7:"Volts",8:"Range (km)",10:"HIGH/LOW"
        }
    add_receiver_sec_volt_plots(user_vars, figure)
    add_loop_stress_plots(user_vars, figure)
    add_reciever_signal_plots(user_vars, figure)
    add_chandra_range_plots(user_vars, figure)
    format_plot_axes(figure, figure_title, yaxis_titles)
    write_html_file(user_vars, figure, figure_title, auto_gen)


def add_receiver_sec_volt_plots(user_vars,figure):
    """
    Utilize user input data to generate Receiver Secondary Voltage Data plot. Then writes HTML file.
    Input: user_vars
    Output: HTML plot file
    """
    print(" - (1/4) Generating Receiver Secondary Voltage Data Plot...")
    msids = ["CRXAV","CRXBV"]

    for msid in tqdm(msids, bar_format = "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        add_plot_trace(user_vars,msid,figure,rows=4,cols=1)

    figure.add_hline(y = 4.2, line_dash = "dash", line_color = "red")
    figure.add_hline(y = 3.8, line_dash = "dash", line_color = "red")
    figure.update_layout(yaxis_range=[3.7,4.3])


def add_loop_stress_plots(user_vars,figure):
    """
    Description: Utilizes user input data to generate Loop Stress Data plot. Then writes as HTML.
    Input: user_vars <object>, figure <object>
    Output: None
    """
    print(" - (2/4) Generating Loop Stress Data Plot...")
    msids = ["CRXALS","CRXBLS","CRXACL","CRXBCL"]

    for msid in tqdm(msids, bar_format = "{l_bar}{bar:20}{r_bar}{bar:-10b}"):

        if msid in ("CRXALS","CRXBLS"):
            rows, cols = 1, 1
        else:
            rows, cols, = 2, 1

        add_plot_trace(user_vars,msid,figure,rows,cols)


def add_reciever_signal_plots(user_vars,figure):
    """
    Utilizes user input data to generate Reciever Data Plot. Then writes HTML file.
    Input: user_vars
    Output: HTML plot file
    """
    print(" - (3/4) Generating Reciever Strength Data Plot...")
    msids = ["CRXASIG","CRXBSIG","CCMDLKA","CCMDLKB"]

    for msid in tqdm(msids, bar_format = "{l_bar}{bar:20}{r_bar}{bar:-10b}"):

        if msid in ("CRXASIG","CRXBSIG"):
            rows, cols = 1, 2
        else:
            rows, cols = 2, 2

        add_plot_trace(user_vars,msid,figure,rows,cols)
