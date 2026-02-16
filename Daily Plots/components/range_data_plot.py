"Chandra Range Data Plot Gen"

from tqdm import tqdm
from components.plot_misc import add_plot_trace


def add_chandra_range_plots(user_vars,figure,pa_plot=False):
    """
    Utilizes user input data to generate Antenna & Transmitter Temp plot. Then writes HTML file.
    Input: user_vars
    Output: HTML plot file
    """
    print(" - (4/4) Generating Chandra Ranging Data Plot...")
    msids = ["CALC_AXAF_RANGE","CPA1MODE","CPA2MODE"]

    for msid in tqdm(msids, bar_format = "{l_bar}{bar:20}{r_bar}{bar:-10b}"):
        if pa_plot:
            if msid in "CALC_AXAF_RANGE":
                add_plot_trace(user_vars,msid,figure,{"rows":3,"cols":2},"Chandra Range")
            else:
                add_plot_trace(user_vars,msid,figure,{"rows":4,"cols":2})
        else:
            if msid in "CALC_AXAF_RANGE":
                add_plot_trace(user_vars,msid,figure,{"rows":4,"cols":2},"Chandra Range")
            else:
                add_plot_trace(user_vars,msid,figure,{"rows":5,"cols":2})
