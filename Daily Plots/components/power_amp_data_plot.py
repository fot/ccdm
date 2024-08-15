"Power Amp Data Plot Gen"

from tqdm import tqdm
from plotly import subplots
from components.misc import write_html_file
from components.plot_misc import format_plot_axes, add_plot_trace
from components.range_data_plot import add_chandra_range_plots


def generate_power_amp_data_plots(user_vars, auto_gen = False):
    """
    Description: Generates Power Amplifier Data Plot
    Input: User input data
    Output: HTML output file of plots
    """
    print("\nGenerating Power Amplifier Data Plot...")
    figure = subplots.make_subplots(
        rows=4,cols=2,shared_xaxes="columns",row_heights=[10,1,10,2],
        subplot_titles=(
            "Power Amplifier Secondary Voltage Data","PA & PA Baseplate Thermal Data","","",
            "PA Power Data","Chandra Ranging Data"
            )
        )

    if auto_gen:
        figure_title = (
            "Chandra CCDM Daily Plots - Power Amplifier Data (Auto-Gen 14-Day Lookback)"
            )
    else:
        figure_title = (
            "Chandra CCDM Daily Plots - Power Amplifier Data" + 
            f" ({user_vars.year_start}" + f"{user_vars.doy_start}" + "_" +
            f"{user_vars.year_end}" + f"{user_vars.doy_end}" + f" {user_vars.data_source})"
            )

    yaxis_titles = {1:"Volts",2:"DegF",5:"dBm",6:"Range (km)",7:"High/Low",8:"High/Low"}

    add_pa_sec_volt_data_plot(user_vars,figure)
    add_pa_pabp_thrm_data_plot(user_vars,figure)
    add_pa_pwr_data_plot(user_vars,figure)
    add_chandra_range_plots(user_vars,figure,pa_plot=True)
    format_plot_axes(figure,figure_title,yaxis_titles)
    write_html_file(user_vars, figure, figure_title, auto_gen)


def add_pa_sec_volt_data_plot(user_vars,figure):
    """
    Description: Uses user inputs to generate PA Secondary Voltage Data plot.
    Input: User variables, figure to be populated.
    Output: None
    """
    print(" - (1/4) Generating Power Amplifier Secondary Voltage Data plot...")
    msids = ["CPA1V","CPA2V"]

    for msid in tqdm(msids, bar_format = "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        add_plot_trace(user_vars,msid,figure,rows=1,cols=1)

    figure.add_hline(y = 4.1, line_dash = "dash", line_color = "red", row=1, col=1)
    figure.add_hline(y = 3.7, line_dash = "dash", line_color = "red", row=1, col=1)
    figure.update_layout(yaxis_range=[3.7,4.3])


def add_pa_pabp_thrm_data_plot(user_vars,figure):
    """
    Description: Uses user inputs to generate PA & PA Baseplate Thermal Data plot.
    Input: User variables, figure to be populated.
    Output: None
    """
    print(" - (2/4) Generating PA & PA Baseplate Thermal Data plot...")
    msids = ["CPA1BPT","CPA2BPT","TCM_RFAS","CXPNAIT","CXPNBIT"]

    for msid in tqdm(msids, bar_format = "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        add_plot_trace(user_vars,msid,figure,rows=1,cols=2)

    figure.add_hline(y = 160, line_dash = "dash", line_color = "yellow", row=1, col=2)
    figure.add_hline(y = -4, line_dash = "dash", line_color = "yellow", row=1, col=2)
    figure.update_layout(yaxis_range=[-5,175])


def add_pa_pwr_data_plot(user_vars,figure):
    """
    Description: Uses user inputs to generate PA Power Data plot.
    Input: User variables, figure to be populated.
    Output: None
    """
    print(" - (3/4) Generating PA Power Data plot...")
    msids = ["CPA1PWR","CPA2PWR"]

    for msid in tqdm(msids, bar_format = "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        add_plot_trace(user_vars,msid,figure,rows=3,cols=1)

    figure.add_hline(y = 41.15, line_dash = "dash", line_color = "yellow", row=3, col=1)
