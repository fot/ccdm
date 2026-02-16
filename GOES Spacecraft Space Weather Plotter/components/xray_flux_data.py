"Methods to add the X-Ray Flux Data to plot"

from components.data import data_query
from components.formatting import format_times
from components.misc import check_data_validity
from components.plotting import add_plot_trace


def add_xray_flux_data(user_vars, figure, row):
    """
    Working On It
    """
    print(" - Adding X-Ray Flux Data...")
    xray_short_wave, xray_long_wave, times = ([] for i in range(3))
    goes_xray_data = data_query(user_vars, "goesp_xray_flux_P1M")

    print("   - Formatting data...")
    for list_item in goes_xray_data['goesp_xray_flux_P1M']['samples']:
        times.append(list_item['time'])
        xray_short_wave.append(float(list_item['Short_Wave']))
        xray_long_wave.append(float(list_item['Long_Wave']))

    formatted_times = format_times(times)
    print("   - Adding data to plot traces...")
    add_plot_trace(figure, formatted_times, xray_short_wave, "X-Ray Flux (Short Wave)", row)
    add_plot_trace(figure, formatted_times, xray_long_wave, "X-Ray Flux (Long Wave)", row)
