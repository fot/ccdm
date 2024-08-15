"MISC Methods for Daily Plots"

import os
import signal


def format_doy(doy_no_format):
    "Format the timetuple into a 3 digit string"
    if len(doy_no_format) == 3:
        doy_formatted = doy_no_format
    elif len(doy_no_format) == 2:
        doy_formatted = f"0{doy_no_format}"
    elif len(doy_no_format) == 1:
        doy_formatted = f"00{doy_no_format}"
    return doy_formatted


def make_output_dir(user_vars, auto_gen = False):
    "Generates the output directory"
    if auto_gen:
        set_dir = "/home/rhoover/python/General Trending/Daily Plots/Output/Auto-Gen/"
    else:
        base_dir = "/home/rhoover/python/General Trending/Daily Plots/Output/"

        if (user_vars.year_start == user_vars.year_end and
            user_vars.doy_start == user_vars.doy_end
            ):
            set_dir = base_dir + f"{user_vars.year_start}{user_vars.doy_start}/"
        else:
            set_dir = (
                base_dir + f"{user_vars.year_start}{user_vars.doy_start}_"
                f"{user_vars.year_end}{user_vars.doy_end}/"
            )
    try:
        os.mkdir(set_dir)
    except BaseException:
        pass
    return set_dir


def write_html_file(user_vars, figure, figure_title, auto_gen = False):
    "Write HTML output file after figure generation"
    print(" - Generating html output file.....")
    set_dir = make_output_dir(user_vars, auto_gen)
    figure.write_html(set_dir + f"{figure_title}" + ".html")
    print(f""" - Done! Data written to "{figure_title}""" + f""".html" in "{set_dir}".""")


def cleanup():
    """
    Description: Clean up processes after script execution
    """
    os.kill(os.getpid(), signal.SIGKILL)


def user_menu():
    """
    Descritpion: Prompts user which plots they want to generate, then returns answer.
    Input: None
    Output: Plot choice <str>
    """
    while True:
        user_input = input(
            "\nWhat do you wish to generate?\n"
            "  1) CCDM Daily Plots\n  2) Report .txt file\n"
            "  3) All (3x plots and .txt file)\n"
            "  4) Restart Inputs\n  0) Exit Tool\n  Input: "
        )
        if (len(str(user_input))) == 1 and (0 <= int(user_input) <= 4):
            choice_dict = {
                1:"CCDM Daily Plots",2:"Report",
                3:"All",4:"Restart",0:"Exit"}
            user_choice = choice_dict.get(int(user_input))
            break
        print(
            f"""\n"{user_input}" was an invalid input.\n"""
            "Please input a single digit interger that is 1, 2, 3, 4, or 0."
            )

    if user_choice == "CCDM Daily Plots":
        while True:
            user_input = input(
                "\n--------CCDM Daily Plot(s) Generator--------\n"
                "Which CCDM plot(s) do you want to generate?\n"
                "  1) Receiver Data\n  2) RF Power Data\n  3) Power Amplifier Data\n"
                "  4) All of them\n  5) Restart Inputs\n  0) Exit Script\n  Input: "
            )
            if (len(str(user_input)) == 1) and (0 <= int(user_input) <= 5):
                choice_dict = {
                    1: "Receiver Data", 2: "RF Power Data", 3: "Power Amplifier Data",
                    4: "All plots", 5: "Restart", 0: "Exit"
                }
                user_choice = choice_dict.get(int(user_input))
                break
            print(
                f"""\n"{user_input}" was an invalid input.\nplease input 
                a single digit interger that is 1, 2, 3, 4, 5, or 0."""
                )

    return user_choice
