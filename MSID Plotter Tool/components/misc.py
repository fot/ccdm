"Misc Methods used in MSID Plotter Tool"

import os
import signal


def user_menu():
    "User menu for some choices"
    while True:
        user_choice = input(
            """\nWhat would you like to do next? Input to continue.\n"""
            """1) Restart Inputs\n"""
            """0) Exit Tool\n"""
            """Input: """
        )
        if user_choice in ("1","0"):
            break
        print(
            f"""\n"{user_choice}" was an invalid input.\nplease input 
            a single digit interger that is 1 or 0."""
            )

    return user_choice


def create_dir(input_dir):
    "Generates a directory"
    try:
        os.makedirs(input_dir)
    except FileExistsError:
        pass


def generate_html_output(user_vars,plot):
    "Takes plot object and write to an HTML file in output directory."

    print("\nGenerating html output file.....")
    set_dir = "/home/rhoover/python/Code/ccdm/MSID Plotter Tool/"
    create_dir(f"{set_dir}/Output")
    plot.write_html(f"{set_dir}/Output/{user_vars.file_title}")
    print(f""" - Done! Data written to "{user_vars.file_title}" in output directory.""")


def cleanup():
    """
    Description: Clean up processes after script execution
    """
    print("\nScript Cleanup...")
    os.kill(os.getpid(), signal.SIGKILL)
