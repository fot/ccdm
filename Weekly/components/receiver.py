"Receiver Data request methods for CCDM Weekly"

import urllib
import json
from urllib.error import HTTPError
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from cxotime import CxoTime
from components.data_requests import ska_data_request as ska_data
from components.data_requests import maude_data_request as maude_data
from components.misc import format_wk

class DataObject:
    "Empty data object to save data to"

@dataclass
class SupportTimes:
    "dataclass for support times"
    bot: None
    eot: None

@dataclass
class SpuriousCmdLockDataPoint:
    "Data class for spurious cmd lock event data"
    start_time: None
    end_time: None
    receiver: None


def jsontime2cxo(time_in):
    "sanitize input"
    time_str = str(time_in)
    return (
        CxoTime(time_str[0:4]+ ':' +time_str[4:7]+':' +time_str[7:9]+':'
                +time_str[9:11]+':' +time_str[11:13]+'.' +time_str[13:])
    )


def get_tx_on(ts,tp,tx):
    "returns 'ON' if specified transmitter was on during this interval."
    ctx = maude_data(ts,tp,f"STAT_5MIN_MIN_CTX{tx}X",False)
    ctx_val = map(int,ctx['data-fmt-1']['values'])
    if min(ctx_val) == 0:
        return 'ON'
    return 'OFF'


def get_nearest_mod(t):
    """ Returns surrounding M1050 monitor state"""
    #sanitize timeformats
    t.format = "yday"
    base_url = "https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m=M1050"
    url = base_url + "&ts=" +str(t) + "&nearest=t"
    with urllib.request.urlopen(url) as response:
        data_after= json.loads(response.read())
    mod_after = int(data_after['data-fmt-1']['values'][0]) # maybe shoudl check timestamp to gate missing data
    mod_time = jsontime2cxo(str(data_after['data-fmt-1']['times'][0]))
    after_dt = (mod_time - t)*86400  # CxoTime timedelta is in fractional days for yday format
    if abs(after_dt) > 60: # Ignore monitor data that is signficantly far away.  Just assume modulation is on during a pass
        mod_after = 2
    url = base_url + "&tp=" +str(t) + "&nearest=t"
    with urllib.request.urlopen(url) as response:
        data_before= json.loads(response.read())
    mod_before = int(data_before['data-fmt-1']['values'][0])
    mod_time = jsontime2cxo(str(data_after['data-fmt-1']['times'][0]))
    before_dt = (t - mod_time)*86400 # CxoTime timedelta is in fractional days for yday format
    if abs(before_dt) > 60:
        mod_before = 2
    if (mod_before == 1) or (mod_after ==1):
        return 'OFF'
    return 'ON'


def get_support_stats(ts,tp):
    """
    Description: returns two lists, one of BOT times, and EOT times in the 
                 interval as well as the number of supports
    Input: Times
    Output: list of strings [<str>], [<str>]
    """
    supports_list= np.array([])
    url= ("https://occweb.cfa.harvard.edu/occweb/web/webapps/ifot/ifot.php?r=home&t=qserver&format="
          "list&e=PASSPLAN.sched_support_time.ts_bot.eot&columns=type_desc,sheetlink,tstart&tstart="
          f"{ts}&tstop={tp}&ul=12"
          )

    with urllib.request.urlopen(url) as response:
        tmp_data = pd.read_html(response.read())

    for bot, eot in zip(tmp_data[0][4][1:],tmp_data[0][5][1:]):
        try:
            bot_time= CxoTime(bot)
            eot_time= CxoTime(f"{bot_time.datetime.year}:"
                            f"{bot_time.datetime.strftime("%j")}:{eot[:2]}:{eot[2:]}")
            if eot_time < bot_time:
                eot_time += timedelta(days= 1)
            supports_list= np.append(supports_list, SupportTimes(bot_time, eot_time))
        except ValueError:
            print("Error! Skipping data point.")

    return supports_list


def get_receiver_data(user_vars):
    "Working on it"

    print("Fetching Receiver Data...\n")
    supports_list= get_support_stats(user_vars.ts,user_vars.tp)
    data = DataObject()

    a_bad, b_bad = {}, {}
    tx_a_on, tx_b_on = 0, 0

    # Now iterate through each BOT-EOT interval and look for transitions...
    for support in supports_list:
        # Trim supports by +/- 300sec
        support.bot += timedelta(seconds=300)
        support.eot -= timedelta(seconds=300)

        try:
            # Transmitter on/off statistics
            if get_tx_on(support.bot,support.eot,'A') == 'ON':
                tx_a_on += 1
            if get_tx_on(support.bot,support.eot,'B') == 'ON':
                tx_b_on += 1

            # Bad Visibility Processing
            ccmdlka = maude_data(support.bot,support.eot,'TR_CCMDLKA',False)
            for time, value in zip(ccmdlka['data-fmt-1']['times'],
                                        ccmdlka['data-fmt-1']['values']):
                ccmdlka_val= int(value)
                ccmdlka_time= jsontime2cxo(time)

                if (ccmdlka_val == 1 and support.bot < ccmdlka_time < support.eot and
                    get_nearest_mod(ccmdlka_time) == 'ON'):
                    a_bad[ccmdlka_time.date[5:8]] = 1

            ccmdlkb = maude_data(support.bot,support.eot,'TR_CCMDLKB',False)
            for time, value in zip(ccmdlkb['data-fmt-1']['times'],
                                        ccmdlkb['data-fmt-1']['values']):
                ccmdlkb_val= int(value)
                ccmdlkb_time= jsontime2cxo(time)

                if (ccmdlkb_val == 1 and support.bot < ccmdlkb_time < support.eot and
                    get_nearest_mod(ccmdlkb_time) == 'ON'):
                    b_bad[ccmdlkb_time.date[5:8]] = 1

        except HTTPError:
            print(f"IFOT ERR Pass {support.bot.greta} - {support.eot.greta}. "
                  "Stats not processed for this pass.")

    data.a_bad, data.b_bad = a_bad, b_bad
    data.tx_a_on, data.tx_b_on = tx_a_on, tx_b_on
    data.num_supports = len(supports_list)

    bot, eot= [],[]
    for support in supports_list:
        bot.append(support.bot)
        eot.append(support.eot)
    data.bot = bot
    data.eot = eot

    return data


def spurious_cmd_lock_detection(user_vars):
    "from a know list of comm times, find spurious cmd locks"

    def detect_start(course_start_datetime,data_point):
        "Detect high rate START of lock data"
        ts= (CxoTime(course_start_datetime) - timedelta(minutes= 2))
        tp= (CxoTime(course_start_datetime) + timedelta(minutes= 2))
        refined_data= ska_data(ts,tp,f"CCMDLK{receiver}",True,print_message= False)

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
        refined_data= ska_data(ts,tp,f"CCMDLK{receiver}",True,print_message= False)

        for r_index, (r_time, r_value) in enumerate(zip(refined_data.times, refined_data.vals)):
            r_time_object, r_counter = CxoTime(r_time), 0
            if ((r_value == "NLCK") and (refined_data.vals[r_index - 1] == "LOCK") and
                (r_index != 0) and (data_point.start_time is not None)):
                for expected_comm in dsn_comm_times:
                    if not expected_comm[0] < (r_time_object.datetime) < expected_comm[1]:
                        r_counter += 1
                if r_counter == len(dsn_comm_times):
                    data_point.end_time= r_time_object.yday

    # Get DSN comm times
    dsn_comm_times= parse_dsn_comms(user_vars.ts,user_vars.tp)
    data_list= []

    for receiver in ("A","B"):
        print(f"   - Checking for Receiver-{receiver} lock...")
        data_point= SpuriousCmdLockDataPoint(None, None, receiver)
        course_data= ska_data(user_vars.ts,user_vars.tp,f"CCMDLK{receiver}")

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
                        f"from {data_point.start_time}z thru {data_point.end_time}z.")
                data_point= SpuriousCmdLockDataPoint(None, None, receiver)

    return data_list


def parse_dsn_comms(ts,tp):
    "Parse the inputted file directory of DSN comms to look for Chandra comms."
    dsn_comm_times, dsn_comm_dirs, date_range= ([] for i in range(3))

    # Build file list to parse.
    for year in (ts.datetime.year, tp.datetime.year):
        for wk in range(1,53):
            file_path= ("/home/mission/MissionPlanning/DSN/DSNweek/"
                        f"{year}_wk{format_wk(wk)}_all.txt")
            if file_path not in dsn_comm_dirs:
                dsn_comm_dirs.append(file_path)

    for value in range((tp.datetime - ts.datetime).days + 3):
        date_value= (timedelta(days= -1) + ts + value).strftime("%j")
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


def write_spurious_cmd_locks(spurious_cmd_locks):
    "write the events found into html string format"
    print("   - Writing Spurious CMD Locks...")
    return_string= ""

    if spurious_cmd_locks:
        for spurious_cmd_lock in spurious_cmd_locks:
            receiver=   spurious_cmd_lock.receiver
            start_time= spurious_cmd_lock.start_time
            end_time=   spurious_cmd_lock.end_time
            return_string += (
                    f"<li>Spurious Command Lock found on Receiver-{receiver} "
                    f"from {start_time}z thru {end_time}z</li>\n")

    return_string += "</ul>"

    return return_string
