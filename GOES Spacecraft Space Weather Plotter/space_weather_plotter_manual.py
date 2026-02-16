"Manual-Run Space Weather Tool"

import time
from os import system
from datetime import datetime
from plotly import subplots
from components.misc import write_html_file
from components.formatting import format_plot_axes
from components.particle_flux_data import add_particle_flux_data
from components.xray_flux_data import add_xray_flux_data
from components.magnetometer_data import add_magnetometer_data
from components.solar_spot_data import add_solar_spots_data
from components.kp_data import add_kp_data
from components.beat_reports import add_dbe_data


class DataObject:
    "Empty data object to save data to"


class UserVars:
    """
    Description: Gather use inputs
    """
    def __init__(self):
        while True:
            system("clear")
            self.start_year = get_start_year()
            self.start_doy = get_doy_start()
            self.end_year = get_end_year()
            self.end_doy = get_end_doy()
            self.start_date = doy_to_date(self.start_year, self.start_doy)
            self.end_date = doy_to_date(self.end_year, self.end_doy)
            input_status = input("\nAre these inputs correct? Y/N: ")

            if input_status in ("Y","y","Yes","yes"):
                break

            print("\nRestarting Inputs...\n\n")
            time.sleep(0.5)


def get_start_year():
    "Get user input for start year"
    while True:
        year_input = input("Enter the START year: XXXX ")
        if (len(str(year_input)) == 4) and (1998 <= int(year_input) <= 2040):
            break
        print(f"{year_input} was an invalid input, please try again")
    return year_input


def get_doy_start():
    "Get user in put for DOY start"
    while True:
        doy_input = input("Enter the START day: XXX ")
        if (len(str(doy_input)) == 3) and (1 <= int(doy_input) <= 366):
            break
        print(f"{doy_input} was an invalid input, please try again")
    return doy_input


def get_end_year():
    "Get user input for end year"
    while True:
        year_input = input("Enter the END year: XXXX ")
        if (len(str(year_input)) == 4) and (1998 <= int(year_input) <= 2040):
            break
        print(f"{year_input} was an invalid input, please try again")
    return year_input


def get_end_doy():
    "Get user input for DOY end"
    while True:
        doy_input = input("Enter the END day: XXX ")
        if (len(str(doy_input)) == 3) and (1 <= int(doy_input) <= 366):
            break
        print(f"{doy_input} was an invalid input, please try again\n")
    return doy_input


def doy_to_date(input_year, input_doy):
    """
    Description: Corrects data format acceptable to url query
    Input: User Variables with Year start/end & DOY start/end
    Output: String of formated date in format yyyy-MM-dd
    """
    time_object = datetime.strptime(f"{input_year} {input_doy}", "%Y %j")
    return time_object


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
        9: ["Kp Value", "# of Sunspots"],
        11: ["Recorded DBEs"],
        }
    figure = subplots.make_subplots(
        rows = len(yaxis_titles.keys()), shared_xaxes=True,
        row_heights = [2 for i in range(len(yaxis_titles.keys()))],
        specs = [[{"secondary_y": True}] for i in range(len(yaxis_titles.keys()))]
    )
    data = DataObject()

    add_particle_flux_data(user_vars, figure, 1, 2)
    add_xray_flux_data(user_vars, figure, 3)
    add_magnetometer_data(user_vars, figure, 4)
    add_solar_spots_data(user_vars, figure, 5)
    add_kp_data(user_vars, figure, 5)
    add_dbe_data(user_vars, data, figure, 6)
    format_plot_axes(user_vars, figure, yaxis_titles)
    return figure


def main():
    "Main Execution"
    while True:
        try:
            user_vars = UserVars()
            figure = generate_plot(user_vars)
            write_html_file(user_vars, figure)
            break
        except KeyboardInterrupt:
            system("clear")
            print("Interrupted plot generation....\n")


main()
