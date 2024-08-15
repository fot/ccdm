"Methods for Collecting User Inputs used in MSID Plotter Tool"

from components.data import check_msid_validity


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


def get_show_plot():
    "Show plot toggle"
    return input("Do you wish to display plot? Y/N: ")


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
