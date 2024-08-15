"MSID Plotter Tool"

from os import system
import time
from cxotime import CxoTime
from components.plot import generate_plot
from components.formatting import get_titles
from components.user_inputs import (get_msids, get_year_start, get_doy_start,
                                    get_year_end, get_doy_end, get_show_plot,
                                    get_data_source)
from components.misc import user_menu, generate_html_output, cleanup


class UserVariables:
    "Class to store user variable inputs."
    def __init__(self):

        while True:
            system("clear")
            self.msids = get_msids()
            self.year_start = get_year_start()
            self.doy_start = get_doy_start()
            self.year_end = get_year_end()
            self.doy_end = get_doy_end()
            self.ts = CxoTime(f"{self.year_start}:{self.doy_start}:00:00:00")
            self.tp = CxoTime(f"{self.year_end}:{self.doy_end}:23:59:59.999")
            self.show_plot = get_show_plot()
            self.data_source = get_data_source()
            self.plot_title, self.file_title = get_titles(self)
            input_status = input("\nAre these inputs correct? Y/N: ")

            if input_status in ("Y","y","Yes","yes"):
                break
            print("\nRestarting Inputs...\n\n")
            time.sleep(1.5)


def main():
    "Main execution"
    while True:
        user_vars = UserVariables()

        try:
            plot = generate_plot(user_vars)
            generate_html_output(user_vars, plot)
        except KeyboardInterrupt: # handle canceling plot generation
            system("clear")
            print("Interrupted plot generation....\n")

        if user_menu() in ("0"):
            break


main()
cleanup()
