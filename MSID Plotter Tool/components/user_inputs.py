"Methods for Collecting User Inputs used in MSID Plotter Tool"

import dataclasses
import time
from os import system
from components.formatting import get_titles
from components.data import check_msid_validity
from cxotime import CxoTime


@dataclasses.dataclass
class UserVariables:
    "Class to store user variable inputs."
    msids = []
    year_start = str()
    doy_start  = str()
    year_end   = str()
    doy_end    = str()
    data_source = str()
    plot_title = str()
    file_title = str()
    ts = None
    tp = None


def get_user_inputs(user_vars, state):
    "populate user_vars with data"
    system("clear")

    while True:
        if state == "all":
            user_vars.msids       = get_msids()
            user_vars.year_start  = get_year_start()
            user_vars.doy_start   = get_doy_start()
            user_vars.year_end    = get_year_end()
            user_vars.doy_end     = get_doy_end()
        elif state == "dates":
            user_vars.year_start  = get_year_start()
            user_vars.doy_start   = get_doy_start()
            user_vars.year_end    = get_year_end()
            user_vars.doy_end     = get_doy_end()
        elif state == "MSIDs":
            user_vars.msids       = get_msids()

        user_vars.data_source = get_data_source()
        user_vars.plot_title, user_vars.file_title = get_titles(user_vars)
        user_vars.ts = CxoTime(f"{user_vars.year_start}:{user_vars.doy_start}:00:00:00")
        user_vars.tp = CxoTime(f"{user_vars.year_end}:{user_vars.doy_end}:23:59:59.999")

        if input("\nAre these inputs correct? Y/N: ") in ("Y","y","Yes","yes"):
            break
        print("\nRestarting Inputs...\n\n")
        time.sleep(0.5)

    return user_vars


def get_msids():
    """
    Description: Build list of MSIDs from user inputs
    Input: User input string of MSID
    Output: List of inputted MSIDs
    """
    print("Enter the MSIDs you wish to plot, press ENTER after each MSID inputted. "
            "MSID1 -> enter, MSIDx -> enter\n"
            """-- A blank input will finish inputing MSID(s). --\n""")
    msid_list = []

    while True:
        msid_input = input("Enter MSID: ").upper()

        # Checking if user ending input of MSID(s)
        if msid_input in ("") and (len(msid_list) != 0):
            break

        # Check input for blank MSID input
        if (msid_input in ("")) and (len(msid_list) == 0):
            print(" - Error! You must enter at least one MSID...\n")

        # Check if input is a duplicate MSID input
        elif msid_input in msid_list:
            print(f""" - Error! MSID "{msid_input}" was already entered...\n""")

        # Check if an input is NOT an MSID
        elif not check_msid_validity(msid_input):
            print(f""" - Error! "{msid_input}" was an invalid MSID input """
                  "\U0001F62D. Please try again.\n"
                )

        # Check if input is a valid MSID, if so save input
        elif check_msid_validity(msid_input):
            msid_list.append(msid_input)

    return msid_list


def get_year_start():
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


def get_year_end():
    "Get user input for end year"
    while True:
        year_input = input("Enter the END year: XXXX ")
        if (len(str(year_input)) == 4) and (1998 <= int(year_input) <= 2040):
            break
        print(f"{year_input} was an invalid input, please try again")
    return year_input


def get_doy_end():
    "Get user input for DOY end"
    while True:
        doy_input = input("Enter the END day: XXX ")
        if (len(str(doy_input)) == 3) and (1 <= int(doy_input) <= 366):
            break
        print(f"{doy_input} was an invalid input, please try again\n")
    return doy_input


def get_data_source():
    "Get user input on whether to use high rate data or not"
    while True:
        data_source = input(
            """\n--Select Data Source--\n"""
            """   Enter "1" if you'd like high rate SKA data """
            """(Caution: will slow down plot generation).\n"""
            """   Enter "2" if you'd like abbreviated SKA data\n"""
            """   Enter "3" if you'd like MAUDE Web data\n"""
            """   Input: """
            )
        if "1" in data_source:
            return "High Rate SKA"
        if "2" in data_source:
            return "Abbreviated SKA"
        if "3" in data_source:
            return "MAUDE Web"
        print(f"""{data_source} was an invalid input \U0001F62D, please try again""")
