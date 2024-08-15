"""
Daily Plots Tool (Manual Run) v1.5
 - Fixed so this works again
 - Now shares modules with auto run variant
"""

from os import system
import time
from cxotime import CxoTime
from components.misc import user_menu, cleanup
from components.receiver_data_plot import generate_receiver_data_plots
from components.rf_power_data_plot import generate_rf_power_data_plots
from components.power_amp_data_plot import generate_power_amp_data_plots
from components.status_report import generate_status_report


class UserVariables:
    "User inputs object. Used to store input values."

    def __init__(self):
        while True:
            system("clear")
            print("----Daily Plots Tool v1.4----")
            self.year_start = get_year_start()
            self.doy_start = get_doy_start()
            self.year_end = get_year_end(self)
            self.doy_end = get_doy_end(self)
            self.data_source = get_data_source()
            self.input_status = input("\nAre these inputs correct? Y/N: ")
            self.ts = CxoTime(self.year_start+":"+self.doy_start+":00:00:00")
            self.tp = CxoTime(self.year_end+":"+self.doy_end+":23:59:59.999")

            if self.input_status in ("Y","y","Yes","yes"):
                break
            print("\nRestarting Inputs...\n\n")


def get_year_start():
    "Takes user input for start year and checks validity, then returns"
    while True:
        year_start = input("Enter the START year: XXXX ")
        if (len(str(year_start)) == 4) and (1998 <= int(year_start) <= 2027):
            break
        print(f"{year_start} was an invalid input, please try again")
    return year_start


def get_doy_start():
    "Takes user input for start DOY and checks validity, then returns"
    while True:
        start_doy = input("Enter the START day: XXX ")
        if (len(str(start_doy)) == 3) and (1 <= int(start_doy) <= 366):
            break
        print(f"{start_doy} was an invalid input, please try again")
    return start_doy


def get_year_end(self):
    "Takes user input for end year and checks validity, then returns"
    while True:
        end_year = input("Enter the END year: XXXX ")
        if (len(str(end_year)) == 4) and (1999 <= int(end_year) <= 2030):
            if end_year < self.year_start:
                print(
                " - Ugh oh! "
                f""""{end_year}" was less than the START year """
                f"""input "{self.year_start}". Please try again."""
                )
            else: break
        else: print(f""" - "{end_year}" was an invalid input, please try again...""")
    return end_year


def get_doy_end(self):
    "Takes user input for end DOY and checks validity, then returns"
    while True:
        doy_input = input("Enter the END day: XXX ")
        if len(str(doy_input)) == 3 and 1 <= int(doy_input) <= 366:
            if (self.year_start == self.year_end) and (doy_input < self.doy_start):
                print(
                " - Ugh Oh! "
                f""""{doy_input}" was less than the START DOY """
                f"""input "{self.doy_start}". Please try again."""
                )
            else: break
        else: print(f""" - "{doy_input}" was an invalid input, please try again...""")
    return doy_input


def get_data_source():
    "Takes user input to determine data source"
    while True:
        data_source_input = input(
            """Default data source: "MAUDE Web Data".\n"""
            " - Press ENTER to continue or enter ANY VALUE to change data source...\n"
            " - Input: "
            )
        if data_source_input == "":
            data_source_input = "MAUDE Web"
            break
        while True:
            data_source_input = input(
                "\n  Choose a non-default data source:\n"
                "      1) SKA Abreviated (slower generation, more detail over default)\n"
                "      2) SKA High Rate  (much slower generation, max detail)\n"
                "      3) MAUDE Web (Default)\n"
                "      Input: "
                )
            if data_source_input in ("1","2","3"):
                if data_source_input == "1":
                    data_source_input = "SKA Abreviated"
                elif data_source_input == "2":
                    data_source_input = "SKA High Rate"
                else:
                    data_source_input = "MAUDE Web"
                break
            print("Invalid input, please try again.")
        break
    return data_source_input


def main():
    "Main execution"
    user_vars = UserVariables()

    while True:
        try:
            user_choice = user_menu()
            if user_choice == "Receiver Data":
                generate_receiver_data_plots(user_vars)
            elif user_choice == "RF Power Data":
                generate_rf_power_data_plots(user_vars)
            elif user_choice == "Power Amplifier Data":
                generate_power_amp_data_plots(user_vars)
            elif user_choice == "Report":
                generate_status_report(user_vars)
            elif user_choice == "CCDM Daily Plots":
                generate_receiver_data_plots(user_vars)
                generate_rf_power_data_plots(user_vars)
                generate_power_amp_data_plots(user_vars)
            elif user_choice == "All":
                generate_receiver_data_plots(user_vars)
                generate_rf_power_data_plots(user_vars)
                generate_power_amp_data_plots(user_vars)
                generate_status_report(user_vars)
            elif user_choice == "Restart":
                user_vars = UserVariables()
            elif user_choice == "Exit":
                print("Goodbye!")
                time.sleep(0.5)
                break
        except KeyboardInterrupt:
            system("clear")
            print("Interrupted plot generation....\n")


main()
cleanup()
