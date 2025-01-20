"Spurious Command Lock Detection for use in status_report.py"

import dataclasses
from datetime import datetime, timedelta
from components.misc import format_wk
from components.tlm_request import data_request
from cxotime import CxoTime


@dataclasses.dataclass
class SpuriousCmdLockDataPoint:
    "Data class for spurious cmd lock event data"
    start_time: None
    end_time: None
    receiver: None


def spurious_cmd_lock_detection(user_vars,file):
    "detect spurious locks outside expected comm time"
    print(" - Spurious Lock Detection...")
    dsn_comm_times= parse_dsn_comms(user_vars)
    spurious_cmd_locks= get_spurious_cmd_locks(user_vars, dsn_comm_times)

    if spurious_cmd_locks:
        for spurious_cmd_lock in spurious_cmd_locks:
            receiver=   spurious_cmd_lock.receiver
            start_time= spurious_cmd_lock.start_time
            end_time=   spurious_cmd_lock.end_time
            file.write(f"  - Spurious Command Lock found on Receiver-{receiver} "
                       f"from ({start_time} thru {end_time}).\n")
    else:
        response= "  - No spurious command locks found.\n"
        file.write(response)


def parse_dsn_comms(user_vars):
    "Parse the inputted file directory of DSN comms to look for Chandra comms."
    dsn_comm_times, dsn_comm_dirs, date_range= ([] for i in range(3))
    date_diff= user_vars.tp.datetime - user_vars.ts.datetime

    # Build file list to parse.
    for year in (user_vars.year_start, user_vars.year_end):
        for wk in range(1,53):
            file_path= ("/home/mission/MissionPlanning/DSN/DSNweek/"
                        f"{year}_wk{format_wk(wk)}_all.txt")
            if file_path not in dsn_comm_dirs:
                dsn_comm_dirs.append(file_path)

    for value in range(date_diff.days + 3):
        date_value= (timedelta(days= -1) + user_vars.ts + value).strftime("%j")
        date_range.append(date_value)

    for dsn_comm in dsn_comm_dirs:
        try:
            with open(dsn_comm, "r", encoding="utf-8") as comm_file:
                for line in comm_file:
                    if "CHDR" in line:
                        split_line = line.split()
                        bot_time= datetime.strptime(split_line[3], "%Y:%j:%H:%M:%S.%f")
                        eot_time= datetime.strptime(split_line[5], "%Y:%j:%H:%M:%S.%f")
                        if bot_time.strftime("%j") in date_range:
                            per_pass = [bot_time - timedelta(days= 0.75/24),
                                        eot_time + timedelta(days= 0.75/24)]
                            dsn_comm_times.append(per_pass)
        except FileNotFoundError:
            print(f"""   - File: "{dsn_comm}" not found in base directory, skipping file...""")

    return dsn_comm_times


def get_spurious_cmd_locks(user_vars,dsn_comm_times):
    "from a know list of comm times, find spurious cmd locks"
    data_list= []

    def detect_start(course_start_datetime,data_point):
        "Detect high rate START of lock data"
        ts= (CxoTime(course_start_datetime) - timedelta(minutes= 2))
        tp= (CxoTime(course_start_datetime) + timedelta(minutes= 2))
        refined_data= data_request(ts,tp,"SKA High Rate",f"CCMDLK{receiver}")

        for r_index, (r_time, r_value) in enumerate(zip(refined_data.times, refined_data.vals)):
            r_time_object, r_counter = CxoTime(r_time), 0
            if ((r_value == "LOCK") and (r_index != 0) and
                (refined_data.vals[r_index - 1] == "NLCK")):
                for expected_comm in dsn_comm_times:
                    if not expected_comm[0] < (r_time_object.datetime) < expected_comm[1]:
                        r_counter += 1
                if r_counter == len(dsn_comm_times):
                    data_point.start_time= r_time_object.yday

    def detect_end(course_end_datetime,data_point):
        "Detect high rate END of lock data"
        ts= (CxoTime(course_end_datetime) - timedelta(minutes= 2))
        tp= (CxoTime(course_end_datetime) + timedelta(minutes= 2))
        refined_data= data_request(ts,tp,"SKA High Rate",f"CCMDLK{receiver}")

        for r_index, (r_time, r_value) in enumerate(zip(refined_data.times, refined_data.vals)):
            r_time_object, r_counter = CxoTime(r_time), 0
            if ((r_value == "NLCK") and (refined_data.vals[r_index - 1] == "LOCK") and
                (r_index != 0) and (data_point.start_time is not None)):
                for expected_comm in dsn_comm_times:
                    if not expected_comm[0] < (r_time_object.datetime) < expected_comm[1]:
                        r_counter += 1
                if r_counter == len(dsn_comm_times):
                    data_point.end_time= r_time_object.yday

    for receiver in ("A","B"):
        print(f"   - Checking for Receiver-{receiver} lock...")
        data_point= SpuriousCmdLockDataPoint(None, None, receiver)
        course_data= data_request(user_vars.ts,user_vars.tp,"SKA Abreviated",f"CCMDLK{receiver}")

        for index, (time, value) in enumerate(zip(course_data.times, course_data.vals)):
            time_object, counter = CxoTime(time), 0

            # Check course data for START of lock
            if (value == "LOCK") and (course_data.vals[index - 1] == "NLCK") and (index != 0):
                for expected_comm in dsn_comm_times:
                    if not expected_comm[0] < (time_object.datetime) < expected_comm[1]:
                        counter += 1
                if counter == len(dsn_comm_times):
                    detect_start(time_object,data_point)

            # Check course data for END of lock
            elif ((value == "NLCK") and (course_data.vals[index - 1] == "LOCK") and
                (index != 0) and (data_point.start_time is not None)):
                for expected_comm in dsn_comm_times:
                    if not expected_comm[0] < time_object.datetime < expected_comm[1]:
                        counter += 1
                if counter == len(dsn_comm_times):
                    detect_end(time_object,data_point)

            # Collect data_points
            # Append data_list if last sample /w partially filled data_point.
            if (index + 1 ==  len(course_data.times) and
                ((data_point.start_time is not None) or (data_point.end_time is not None))):
                data_list.append(data_point)
            # Append data_list if data_point fills, then make a new data_point.
            elif data_point.start_time is not None and data_point.end_time is not None:
                data_list.append(data_point)
                print(f"    - Spurious Command Lock found on Receiver-{receiver} "
                        f"from ({data_point.start_time} thru {data_point.end_time}).")
                data_point= SpuriousCmdLockDataPoint(None, None, receiver)

    return data_list
