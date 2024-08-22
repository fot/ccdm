"Methods to add Kp Data to Plot"

from components.data import data_query
from components.formatting import format_times
from components.plotting import add_plot_trace


def add_kp_data(user_vars, figure, row):
    """
    Add data for GOES measured magnetometer values
    """
    print(" - Adding Kp Data...")
    times, kp_value = ([] for i in range (2))
    kp_data = data_query(user_vars, "kp")

    print("   - Formatting data...")
    for list_item in kp_data['kp']['samples']:
        times.append(list_item['time'])
        kp_value.append(list_item['kp_value'])

    formatted_times = format_times(times)

    print("   - Adding data to plot traces...")
    add_plot_trace(figure, formatted_times, kp_value, "Kp Value", row, True)
