"Methods to add the Magnetometer Flux Data to plot"

from components.data import data_query
from components.formatting import format_times
from components.plotting import add_plot_trace


def add_magnetometer_data(user_vars, figure, row):
    """
    Add data for GOES measured magnetometer values
    """
    print(" - Adding Magnetometer Data...")
    times, hp, he, hn = ([] for i in range (4))
    mag_data = data_query(user_vars, "goess_mag_p1m")

    print("   - Formatting data...")
    for list_item in mag_data['goess_mag_p1m']['samples']:
        times.append(list_item['time'])
        hp.append(float(list_item['Hp']))
        he.append(float(list_item['He']))
        hn.append(float(list_item['Hn']))

    formatted_times = format_times(times)
    print("   - Adding data to plot traces...")
    add_plot_trace(figure, formatted_times, hp, "Hp (northward)", row)
    add_plot_trace(figure, formatted_times, he, "He (earthward)", row)
    add_plot_trace(figure, formatted_times, hn, "Hn (eastward)", row)
