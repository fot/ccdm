"Generate file with additional query data"

import warnings
import openpyxl as xl
from datetime import timedelta
from cxotime import CxoTime
from components.data_requests import ska_data_request as ska_data
warnings.filterwarnings('ignore')


def get_ssr_rollover_data(user_vars):
    "Get SSR data for active dates and when rollover occured."

    if user_vars.prime_ssr == "A":
        prime, backup = "A", "B"
    else:
        prime, backup = "B", "A"

    print(f"Looking for when SSR-{backup} was active while SSR-{prime} was prime...")
    ssr_data = ska_data(user_vars.ts, user_vars.tp, f"COS{prime}RCEN")
    ssr_times, ssr_values = ssr_data.times, ssr_data.vals
    ssr_not_recording_doy = []
    ssr_not_recording_datetimes = {}

    # Shorten list to only when SSR Prime was not recording
    for index, (time, value) in enumerate(zip(ssr_times, ssr_values)):

        # Detect rollover from prime to backup
        if (ssr_values[index - 1] == "TRUE"
            and value == "FALS"
            and CxoTime(time).strftime("%j") != user_vars.start_doy
            and CxoTime(time).strftime("%j") != user_vars.end_doy
        ):
            ssr_not_recording_datetimes.setdefault("Prime to Backup",[]).append(
                CxoTime(time).datetime)

        # Detect rollover from backup to prime (exclude last data point)
        try:
            if (value == "FALS"
                and ssr_values[index + 1] == "TRUE"
                and CxoTime(time).strftime("%j") != user_vars.start_doy
                and CxoTime(time).strftime("%j") != user_vars.end_doy
            ):
                ssr_not_recording_datetimes.setdefault("Backup to Primary",[]).append(
                    CxoTime(time).datetime)
        except IndexError: # drop the last data point, can't look at index+1 on last value
            pass

    # Pull out DOYs backup SSR was active & remove many duplicate entries
    for rollover_type, date_list in ssr_not_recording_datetimes.items():
        for date in date_list:
            doy_item = date.strftime("%j")

            if doy_item not in ssr_not_recording_doy:
                ssr_not_recording_doy.append(date.strftime("%j"))

    return ssr_not_recording_doy, ssr_not_recording_datetimes


def write_ssr_data(file, user_vars, ssr_not_recording_doy, ssr_not_recording_datetimes):
    "Write SSR data to data file"
    file.write("SSR Active Data\n")

    if user_vars.prime_ssr == "A":
        backup = "B"
    else:
        backup = "A"

    file.write(f"  • Days that SSR-{backup} was active during the "
               f"biannual period {ssr_not_recording_doy}\n")

    zip_data = zip(ssr_not_recording_datetimes["Prime to Backup"],
                   ssr_not_recording_datetimes["Backup to Primary"])

    for prime_to_backup, backup_to_prime in zip_data:
        rollover_date = prime_to_backup.strftime("%Y:%j:%H:%M:%S.%f")
        recovery_date = backup_to_prime.strftime("%Y:%j:%H:%M:%S.%f")
        file.write(f"  • SSR rollover on {rollover_date} with a recovery on {recovery_date}\n")

    file.write("-------------------------------------------------------------------------\n\n")


def get_dsn_data(user_vars):
    "Get DSN data from DSN excel files."
    print("Get DSN Data...")
    data_dict = {}
    total_time, total_contacts = 0, 0
    months = []

    # Generate list of months
    time_delta = user_vars.tp.datetime - user_vars.ts.datetime
    for day in range(time_delta.days + 1):
        current_day = (user_vars.ts + timedelta(days=day)).datetime

        if current_day.strftime("%B") not in months:
            months.append(current_day.strftime("%B"))

    # Pull data by month
    for month in months:
        raw_time = timedelta(0)
        directory = (f"/share/FOT/operations/Marshall Monthly/{user_vars.start_year} Reports/"
                    f"{month}_{user_vars.start_year} Report.xlsx")
        data_per_month = xl.load_workbook(directory)

        for cell in ("G3","H3"):
            raw_time += data_per_month["Totals"][f"{cell}"].value

        per_month = {"34m month total": (raw_time.days*24 + raw_time.seconds/3600),
                    "34m contacts": data_per_month["Totals"]["B3"].value}
        data_dict.setdefault(f"{month}",per_month)

        # Running total of all
        total_time += (raw_time.days*24 + raw_time.seconds/3600)
        total_contacts += data_per_month["Totals"]["B3"].value

    # Record totals
    data_dict.setdefault("Total",{"34m month total": total_time, "34m contacts": total_contacts})

    return data_dict


def write_dsn_data(file, dsn_data):
    "Write the DSN data to the file."
    file.write("DSN Comm Data\n")

    for month, value in dsn_data.items():
        contacts = value["34m contacts"]
        total_time = value["34m month total"]
        file.write(f"  • In {month} there were {contacts} supports with "
                   f"a total time of {total_time} hours.\n")

    file.write("-------------------------------------------------------------------------\n\n")


def get_ssr_b_on_mean(user_vars):
    "Get the mean value for MSID CSSR2CBV for the biannaual period when SSR-B ON"
    print("Finding the mean value of CSSR2CBV for the biannaul period...")
    data = ska_data(user_vars.ts, user_vars.tp, "CSSR2CBV", True)
    values = data.vals
    sum_of_values, counter = 0, 0

    for value in values:
        if value != 0: # Only include values when SSR was ON.
            sum_of_values += value
            counter += 1

    return sum_of_values / counter


def write_ssr_b_mean(file, mean_value):
    "Write the SSR-B ON mean value to the file."
    file.write("SSR-B ON time mean value\n")
    file.write(f"  • The mean value for MSID CSSR2CBV was: {mean_value}")


def build_query_data_file(user_vars):
    "Build the query data file"
    ssr_not_recording_doy, ssr_not_recording_datetimes = get_ssr_rollover_data(user_vars)
    dsn_data = get_dsn_data(user_vars)
    mean_value = get_ssr_b_on_mean(user_vars)

    # Open the output file
    with open(f"{user_vars.set_dir}/Output/query_data.txt", "w+", encoding="utf-8") as file:
        file.write(f"Query Data for {user_vars.start_year}:{user_vars.start_doy} through "
                   f"{user_vars.end_year}:{user_vars.end_doy}\n")
        file.write("-------------------------------------------------------------------------\n\n")
        write_ssr_data(file, user_vars, ssr_not_recording_doy, ssr_not_recording_datetimes)
        write_dsn_data(file, dsn_data)
        write_ssr_b_mean(file, mean_value)
