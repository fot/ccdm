"""
Daily Plots Tool v1.5
Change Notes
 - Moved methods to external modules to be shared with manual run variant.
"""

from datetime import datetime, timedelta
from cxotime import CxoTime
from components.misc import cleanup
from components.receiver_data_plot import generate_receiver_data_plots
from components.rf_power_data_plot import generate_rf_power_data_plots
from components.power_amp_data_plot import generate_power_amp_data_plots
from components.status_report import generate_status_report


class UserVariables:
    "User inputs object. Used to store input values."

    def __init__(self):
        self.start_date = datetime.now() - timedelta(14)
        self.end_date = datetime.now()
        self.year_start = str(self.start_date.year)
        self.doy_start = str(self.start_date.timetuple().tm_yday)
        self.year_end = str(self.end_date.year)
        self.doy_end = str(self.end_date.timetuple().tm_yday)
        self.ts = CxoTime(self.year_start+":"+self.doy_start+":00:00:00")
        self.tp = CxoTime(self.year_end+":"+self.doy_end+":23:59:59.999")
        self.data_source = "SKA Abreviated"


def main():
    "Main execution"
    user_vars = UserVariables()
    try:
        generate_receiver_data_plots(user_vars, True)
        generate_rf_power_data_plots(user_vars, True)
        generate_power_amp_data_plots(user_vars, True)
        generate_status_report(user_vars, True)
    except BaseException as err:
        print("Interrupted plot generation. Canceling auto-run for today....\n")
        print(err)


main()
cleanup()
