"Generate file with additional query data"

import warnings
import traceback
import dataclasses
import openpyxl as xl
from tqdm import tqdm
from datetime import timedelta
from cxotime import CxoTime
from components.data_requests import ska_data_request as ska_data
warnings.filterwarnings('ignore')

@dataclasses.dataclass
class SSRRolloverDataPoint:
    "Data class for SSR Rollover Data"
    prime_to_backup: None
    backup_to_prime: None

@dataclasses.dataclass
class DSNData:
    "Data class for DSN Data"
    year:  None
    month: None
    supports: None
    time: None


def get_ssr_rollover_data(user_vars):
    "Get SSR data for active dates and when rollover occured."

    if user_vars.prime_ssr == "A":
        backup= "B"
    else: backup= "A"

    print(f"Looking for when SSR-{backup} was active while SSR-{user_vars.prime_ssr} was prime...")
    ssr_data = ska_data(user_vars.ts, user_vars.tp, f"COS{user_vars.prime_ssr}RCEN", True)
    data_list= []
    data_point= SSRRolloverDataPoint(None, None)

    # Parse data for SSR record swap on prime SSR
    for index, (time, value) in tqdm(enumerate(zip(ssr_data.times, ssr_data.vals)),
                                     total= len(ssr_data.times),
                                     bar_format= "{l_bar}{bar:20}{r_bar}{bar:-10b}"):

        if index != 0:
            if value == "FALS" and ssr_data.vals[index - 1] == "TRUE":
                data_point.prime_to_backup= CxoTime(time).datetime
            elif value == "TRUE" and ssr_data.vals[index - 1] == "FALS":
                data_point.backup_to_prime= CxoTime(time).datetime

        # Append data_list if last sample w/ partially filled data_point
        if (index + 1 == len(ssr_data.vals) and
              ((data_point.prime_to_backup is not None) or
              (data_point.backup_to_prime is not None))):
            data_list.append(data_point)
        # Append data_list if data_point fills, then make a new data_point.
        elif data_point.prime_to_backup is not None and data_point.backup_to_prime is not None:
            data_list.append(data_point)
            data_point= SSRRolloverDataPoint(None, None)
        # Append data_list if a backup-to-prime swap occurs before a prime-to-backup swap.
        elif data_point.prime_to_backup is None and data_point.backup_to_prime is not None:
            data_list.append(data_point)
            data_point= SSRRolloverDataPoint(None, None)

    return data_list


def get_rollover_days(ssr_data):
    "Determine what days backup SSR was active"
    rollover_days= []

    for data_item in ssr_data:
        try:
            if (data_item.prime_to_backup.strftime("%j")) not in rollover_days:
                rollover_days.append(data_item.prime_to_backup.strftime("%j"))
        except AttributeError:
            pass

        try:
            if (data_item.backup_to_prime.strftime("%j")) not in rollover_days:
                rollover_days.append(data_item.backup_to_prime.strftime("%j"))
        except AttributeError:
            pass

    return rollover_days


def get_dsn_data(user_vars):
    "Get DSN data from DSN excel files."
    print("\nGet DSN Data from Marshall Monthly Files...")
    dsn_data= DSNData(None, None, None, None)
    dsn_data_list, year_months = [], []
    total_time, total_supports = 0, 0

    # Generate list of months
    time_delta = user_vars.tp.datetime - user_vars.ts.datetime
    for day in range(time_delta.days + 1):
        current_day = (user_vars.ts + timedelta(days=day)).datetime

        if ([f"{current_day.strftime('%Y')}",f"{current_day.strftime('%B')}"]) not in year_months:
            year_months.append([f"{current_day.strftime('%Y')}",f"{current_day.strftime('%B')}"])

    # Pull data by year/month
    for year_month in year_months:
        raw_time = timedelta(0)
        directory= f"{user_vars.set_dir}/Files/DSN/{year_month[1]}_{year_month[0]} Report.xlsx"

        try:
            dsn_excel = xl.load_workbook(directory, data_only= True)
            print(f"  - Processing {year_month[1]}_{year_month[0]} Report.xlsx...")

        except FileNotFoundError:
            print(f"  - File {year_month[1]}_{year_month[0]} Report.xlsx not found.")
            continue

        for cell in ("G3","H3"):
            raw_time += dsn_excel["Totals"][f"{cell}"].value

        # Record data
        dsn_data.year= year_month[0]
        dsn_data.month= year_month[1]
        dsn_data.time= round(raw_time.days*24 + raw_time.seconds/3600, 2)
        dsn_data.supports= dsn_excel["Totals"]["B3"].value

        # Running total of all
        total_supports += dsn_data.supports
        total_time += dsn_data.time

        # Append dsn_data_list and make a new dsn_data object
        dsn_data_list.append(dsn_data)
        dsn_data= DSNData(None,None,None,None)

    # Record totals
    dsn_data.supports= total_supports
    dsn_data.time= total_time
    dsn_data_list.append(dsn_data)

    return dsn_data_list


def get_ssr_b_on_mean(user_vars):
    "Get the mean value for MSID CSSR2CBV for the biannaual period when SSR-B ON"
    print("\nFinding the mean value of CSSR2CBV for the biannaul period...")
    data= ska_data(user_vars.ts, user_vars.tp, "CSSR2CBV", True)
    values= data.vals
    sum_of_values, counter= 0, 0

    for value in values:
        if value != 0: # Only include values when SSR was ON.
            sum_of_values += value
            counter += 1

    return sum_of_values / counter


def write_ssr_rollover_data(file, ssr_data):
    "Write SSR data to data file"

    for data_point in ssr_data:
        try:
            prime_to_backup= data_point.prime_to_backup.strftime('%Y:%j:%H:%M:%S.%f')[:-3]
            backup_to_prime= data_point.backup_to_prime.strftime('%Y:%j:%H:%M:%S.%f')[:-3]
            file.write(f"  • SSR rollover on {prime_to_backup}z "
                       f"with a recovery on {backup_to_prime}z.\n")
        except AttributeError:
            pass


def write_rollover_days_data(file, user_vars, ssr_data):
    "write the rollover days data to the data file"
    rollover_days= get_rollover_days(ssr_data)

    if user_vars.prime_ssr == "A":
        backup = "B"
    else: backup = "A"

    file.write(f"  • Days that SSR-{backup} was active during the "
               f"biannual period {rollover_days}\n")


def write_ssr_b_mean(file, user_vars):
    "Write the SSR-B ON mean value to the file."
    mean_value= get_ssr_b_on_mean(user_vars)
    file.write("SSR-B ON time mean value\n")
    file.write(f"  • The mean value for MSID CSSR2CBV was: {mean_value}\n")


def write_dsn_data(file, user_vars):
    "Write the DSN data to the file."
    dsn_data= get_dsn_data(user_vars)
    file.write("DSN Comm Data\n")

    for index, (data) in enumerate(dsn_data):
        if not (index + 1) == len(dsn_data):
            file.write(f"  • In {data.year}:{data.month} there were {data.supports} supports with "
                       f"a total time of {data.time} hours.\n")
        else:
            file.write(f"  • In Total there were {data.supports} supports with "
                       f"a total time of {data.time} hours.\n")


def build_query_data_file(user_vars):
    "Build the query data file"
    try:
        with open(f"{user_vars.set_dir}/Output/query_data.txt", "w+", encoding="utf-8") as file:
            ssr_data= get_ssr_rollover_data(user_vars)

            # Write SSR Data
            file.write("SSR Active Data\n")
            write_ssr_rollover_data(file, ssr_data)
            write_rollover_days_data(file, user_vars, ssr_data)
            file.write("-" * 74 + "\n\n")

            # Write SSR-B ON mean value
            if user_vars.prime_ssr == "A":
                write_ssr_b_mean(file, user_vars)
                file.write("-" * 74 + "\n\n")

            # Write DSN Data
            write_dsn_data(file, user_vars)
            file.write("-" * 74 + "\n\n")

            print("\n - Query Data File Created!")
            file.close()

    except (IndexError, TypeError) as error:
        print(f"Error ({error}) while building data file, file partially written.")
        traceback.print_exc()
        file.close()
