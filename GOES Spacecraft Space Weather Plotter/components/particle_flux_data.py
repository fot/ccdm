"Methods to add the Particle Flux Data to plot"

from components.data import data_query
from components.formatting import format_times
from components.misc import check_data_validity
from components.plotting import add_plot_trace


def add_particle_flux_data(user_vars, figure, e_row, p_row):
    """
    Working On it
    """
    print(" - Adding Particle Flux Data...")
    times = []
    goes_particle_data = data_query(user_vars,"goesp_part_flux_P5M")

    for list_item in goes_particle_data['goesp_part_flux_P5M']['samples']:
        times.append(list_item['time'])

    formatted_times = format_times(times)
    add_proton_flux_data(figure,goes_particle_data,formatted_times,p_row)
    add_electron_flux_data(figure,goes_particle_data,formatted_times,e_row)


def add_proton_flux_data(figure, data, formatted_times, row):
    "Description: Add proton flux data to the plot."
    print("   - Adding Proton Flux Data...")
    proton_1mev, proton_5mev, proton_10mev, proton_30mev = ([] for i in range(4))
    proton_50mev, proton_100mev, proton_60mev, proton_500mev = ([] for i in range(4))

    print("     - Formatting data...")
    for list_item in data['goesp_part_flux_P5M']['samples']:
        proton_1mev.append(float(check_data_validity(list_item['P1'])))
        proton_5mev.append(float(check_data_validity(list_item['P5'])))
        proton_10mev.append(float(check_data_validity(list_item['P10'])))
        proton_30mev.append(float(check_data_validity(list_item['P30'])))
        proton_50mev.append(float(check_data_validity(list_item['P50'])))
        proton_60mev.append(float(check_data_validity(list_item['P60'])))
        proton_100mev.append(float(check_data_validity(list_item['P100'])))
        proton_500mev.append(float(check_data_validity(list_item['P500'])))

    for list_id in ("1","5","10","30","50","60","100","500"):
        data_list = eval(f"proton_{list_id}mev")
        if not all([v == 0 for v in data_list]):
            print(f"""     - Adding Proton Flux > {list_id} Mev to plot...""")
            if list_id == "1":
                add_plot_trace(
                    figure, formatted_times, data_list,
                    f"Proton Flux > {list_id} MeV", row, sec_y=True)
            else:
                add_plot_trace(
                    figure, formatted_times, data_list,
                    "Proton Flux > 5 MeV", row)
        else:
            print(f"""     - Omitting "Proton Flux > {list_id} MeV" """
                  "trace due to no data being collected...")


def add_electron_flux_data(figure, data, formatted_times, row):
    "Description: Add electron flux data to the plot"
    print("   - Adding Electron Flux Data...")
    electron_08mev, electron_2mev, electron_4mev = ([] for i in range(3))

    print("     - Formatting data...")
    for list_item in data['goesp_part_flux_P5M']['samples']:
        electron_08mev.append(float(check_data_validity(list_item['E_8'])))
        electron_2mev.append(float(check_data_validity(list_item['E2_0'])))
        electron_4mev.append(float(check_data_validity(list_item['E4_0'])))

    for list_id in ("08","2","4"):
        data_list = eval(f"electron_{list_id}mev")
        if list_id == ("08"):
            list_label = "0.8"
        else: list_label = list_id
        if not all([v == 0 for v in data_list]):
            print(f"""     - Adding Electron Flux > {list_label} Mev to plot...""")
            add_plot_trace(
                figure,formatted_times,data_list,f"Electron Flux > {list_label} MeV", row)
        else:
            print(f"""     - Omitting "Electron Flux > {list_label} MeV" trace due to no data...""")
