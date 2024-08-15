"RF Power Data Plots Gen"

from tqdm import tqdm
from plotly import subplots
from components.misc import write_html_file
from components.plot_misc import format_plot_axes, add_plot_trace


def generate_rf_power_data_plots(user_vars, auto_gen = False):
    """
    Description: Generates TX/PA Power Plot
    Input: User input data
    Output: HTML output file of plots
    """
    print("\nGenerating RF Power Data Plot...")
    figure = subplots.make_subplots(
        rows=5,cols=2,shared_xaxes="columns",row_heights=[10,2,1,10,2],
        subplot_titles=(
            "Tranmitter RF Power Output (Counts)","Power Amplifier Power Data","","","","",
            "Tranmitter RF Power Output (dBm)","Antenna & Transmitter Temps"
            )
        )

    if auto_gen:
        figure_title = (
            "Chandra CCDM Daily Plots - RF Power Data (Auto-Gen 14-Day Lookback)"
            )
    else:
        figure_title = (
            "Chandra CCDM Daily Plots - RF Power Data" + 
            f" ({user_vars.year_start}" + f"{user_vars.doy_start}" + "_" +
            f"{user_vars.year_end}" + f"{user_vars.doy_end}" + f" {user_vars.data_source})"
            )

    yaxis_titles = {
        1:"Counts",2:"dBm",3:"Off/On",4:"Off/On",
        7:"dBm",8:"Temp (f)",9:"Off/On"
        }
    add_trans_rf_pwr_cnts_plot(user_vars, figure)
    add_pa_power_data_plot(user_vars, figure)
    add_trans_rf_pwr_output_plot(user_vars, figure)
    add_antenna_trans_temp_plot(user_vars, figure)
    format_plot_axes(figure, figure_title, yaxis_titles)
    write_html_file(user_vars, figure, figure_title, auto_gen)


def add_trans_rf_pwr_cnts_plot(user_vars,figure):
    """
    Description: Utilizes user input data to generate Antenna & Transmitter Temp plot.
    Input: User variables, figure to be populated.
    Output: None
    """
    print(" - (1/4) Generating Transmitter RF Power Output (Counts) Plot...")
    msids = ["RAW_CTXAPWR","RAW_CTXBPWR","CTXAX","CTXBX"]

    for msid in tqdm(msids, bar_format = "{l_bar}{bar:20}{r_bar}{bar:-10b}"):

        if msid in ("CTXAX","CTXBX"):
            rows, cols = 2, 1
        else:
            rows, cols = 1, 1

        add_plot_trace(user_vars,msid,figure,rows,cols)


def add_pa_power_data_plot(user_vars,figure):
    """
    Description: Uses user inputs to generate Power Amplifier Power Data plot.
    Input: User variables, figure to be populated.
    Output: None
    """
    print(" - (2/4) Generating Power Amplifier Power Data plot...")
    msids = ["CPA1PWR","CPA2PWR","CTXAX","CPA1","CPA1MODE","CTXBX","CPA2","CPA2MODE"]

    for msid in tqdm(msids, bar_format = "{l_bar}{bar:20}{r_bar}{bar:-10b}"):

        if msid in ("CPA1PWR","CPA2PWR"):
            rows, cols = 1, 2
        else:
            rows, cols = 2, 2

        add_plot_trace(user_vars,msid,figure,rows,cols)


def add_trans_rf_pwr_output_plot(user_vars,figure):
    """
    Description: Uses user inputs to generate Transmitter RF Power Output plot.
    Input: User variables, figure to be populated.
    Output: None
    """
    print(" - (3/4) Generating Transmitter RF Power Output (dBm) plot...")
    msids = ["CTXAPWR","CTXBPWR","CTXAX","CTXBX"]

    for msid in tqdm(msids, bar_format = "{l_bar}{bar:20}{r_bar}{bar:-10b}"):

        if msid in ("CTXAPWR","CTXBPWR"):
            rows, cols = 4, 1
        else:
            rows, cols = 5, 1

        add_plot_trace(user_vars,msid,figure,rows,cols)


def add_antenna_trans_temp_plot(user_vars,figure):
    """
    Description: Uses user inputs to generate Antenna & Transmitter Temps plot.
    Input: User variables, figure to be populated.
    Output: None
    """
    print(" - (4/4) Generating Antenna & Transmitter Temps plot...")
    msids = ["TCM_RFAS","TPZLGABM","TMZLGABM","TCM_TX1","TCM_TX2"]

    for msid in tqdm(msids, bar_format = "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        add_plot_trace(user_vars,msid,figure,rows=4,cols=2)
