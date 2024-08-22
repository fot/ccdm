"Misc Methods for Space Weather Plotter Tool"

import os


def create_dir(input_dir):
    """
    Description: Create the given directory path
    Input: <str>
    Output: None
    """
    try:
        os.makedirs(input_dir)
    except FileExistsError:
        pass


def write_html_file(user_vars, figure, auto = False):
    "Write HTML output file after figure generation"
    print(" - Generating html output file.....")

    if auto:
        figure_title = (
            "GOES Space Weather Plot (14-Day Lookback)"
        )
    else:
        figure_title = (
            "GOES Space Weather Plot " +
            f"({user_vars.start_year}{user_vars.start_doy}_{user_vars.end_year}{user_vars.end_doy})"
        )

    output_dir = "/share/FOT/engineering/ccdm/Tools/GOES Spacecraft Space Weather Tool/Output/"
    create_dir(output_dir)
    figure.write_html(f"{output_dir}/{figure_title}.html")
    print(f""" - Done! Data written to "{output_dir}{figure_title}.html" in output directory.""")


def check_data_validity(data):
    """
    Description: Check that data is valid
    Input: Data point
    Output: Data point or zero if data not valid
    """
    if data >= 0:
        return data
    return 0
