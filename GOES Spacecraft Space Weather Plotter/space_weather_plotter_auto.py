"Auto-Run Space Weather Tool"

from datetime import datetime, timedelta
from os import system
from plotly import subplots
from components.misc import write_html_file
from components.formatting import format_plot_axes
from components.particle_flux_data import add_particle_flux_data
from components.xray_flux_data import add_xray_flux_data
from components.magnetometer_data import add_magnetometer_data


class DataObject:
    "Empty data object to save data to"


class UserVars:
    """
    Description: Gather use inputs
    """
    def __init__(self):
        self.start_date = datetime.now() - timedelta(14)
        self.end_date = datetime.now()
        self.start_doy = self.start_date.timetuple().tm_yday
        self.start_year = self.start_date.year
        self.end_doy = self.end_date.timetuple().tm_yday
        self.end_year = self.end_date.year


def generate_plot(user_vars):
    """
    Utilizes user input data to generate Loop Stress Data plot. Then writes as HTML.
    Input: user_vars
    Output: Figure object
    """
    print("\nGenerating GOES Spacecraft Space Weather Data Plot...")

    yaxis_titles = {
        1: ["Electron Flux</br></br>(e-/cm^2-s-sr)"],
        3: ["Proton Flux</br></br>(p+/cm^2-s-sr)", "1 Mev"],
        5: ["Xray Flux</br></br>(W/m^2)"],
        7: ["Magnetometer</br></br>(nT)"],
        }

    figure = subplots.make_subplots(
        rows = len(yaxis_titles.keys()), shared_xaxes=True,
        row_heights = [2 for i in range(len(yaxis_titles.keys()))],
        specs = [[{"secondary_y": True}] for i in range(len(yaxis_titles.keys()))]
    )

    add_particle_flux_data(user_vars, figure, 1, 2)
    add_xray_flux_data(user_vars, figure, 3)
    add_magnetometer_data(user_vars, figure, 4)
    format_plot_axes(user_vars, figure, yaxis_titles)
    return figure


def main():
    "Main Execution"
    while True:
        try:
            user_vars = UserVars()
            figure = generate_plot(user_vars)
            write_html_file(user_vars, figure, True)
            break
        except KeyboardInterrupt:
            system("clear")
            print("Interrupted plot generation....\n")


main()
