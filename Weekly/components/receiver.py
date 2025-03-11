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


@dataclass
class SupportTimes:
    "dataclass for support times"
    bot: None
    eot: None


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
        bot_time= CxoTime(bot)
        eot_time= CxoTime(f"{bot_time.datetime.year}:"
                          f"{bot_time.datetime.strftime("%j")}:{eot[:2]}:{eot[2:]}")
        if eot_time < bot_time:
            eot_time += timedelta(days= 1)
        supports_list= np.append(supports_list, SupportTimes(bot_time, eot_time))

    return supports_list


def get_receiver_data(user_vars,data):
    "Working on it"

    print("\nFetching Receiver Data...\n")
    supports_list= get_support_stats(user_vars.ts,user_vars.tp)

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


def parse_dsn_comms(user_vars):
    "Parse the inputted file directory of DSN comms to look for Chandra comms."
    print(" - Parsing DSN Comm files...")
    date_range, dsn_comm_times, dsn_comm_dirs = ([] for i in range(3))
    date_diff = user_vars.tp.datetime - user_vars.ts.datetime

    # Build file list to parse.
    for user_date in (user_vars.ts, user_vars.tp):
        week_of_year= user_date.datetime.isocalendar().week
        year= user_date.datetime.isocalendar().year
        dsn_comm_dirs.append(
            "/home/mission/MissionPlanning/DSN/DSNweek/"
            f"{year}_wk{format_wk(week_of_year)}_all.txt")

    for value in range(date_diff.days + 3):
        date_value = (timedelta(-1) + user_vars.ts + value).strftime("%j")
        date_range.append(date_value)

    for dsn_comm in dsn_comm_dirs:
        try:
            with open(dsn_comm, "r", encoding="utf-8") as comm_file:
                for line in comm_file:
                    if "CHDR" in line:
                        split_line = line.split()
                        boa_time = datetime.strptime(split_line[3], "%Y:%j:%H:%M:%S.%f")
                        eoa_time = datetime.strptime(split_line[5], "%Y:%j:%H:%M:%S.%f")
                        if boa_time.strftime("%j") in date_range:
                            per_pass = [boa_time - timedelta(hours=0.75),
                                        eoa_time + timedelta(hours=0.75)]
                            dsn_comm_times.append(per_pass)
        except FileNotFoundError:
            print(f"""   - File: "{dsn_comm}" not found in base directory, skipping file...""")

    return dsn_comm_times


def spurious_cmd_lock_detection(user_vars, high_rate = False):
    "Detect if a spurious command lock occured in date/time range"
    print("Spurious Command Lock Detection.")
    dsn_comm_times = parse_dsn_comms(user_vars)
    spurious_cmd_locks = {}

    for receiver in ("A","B"):
        print(f" - Checking for Receiver-{receiver} lock...")
        raw_data = ska_data(user_vars.ts, user_vars.tp, f"CCMDLK{receiver}", high_rate)
        values, times = raw_data.vals, raw_data.times
        locked_times = []

        # Purge raw data into dates when receiver was locked only.
        for time, value in zip(times, values):
            if value == "LOCK":
                locked_times.append(CxoTime(time).datetime)

        # Check if times when locked was outside of expected comm
        for locked_time in locked_times:
            value_out_of_comm = []

            for expected_comm in dsn_comm_times:
                if not expected_comm[0] < locked_time < expected_comm[1]:
                    value_out_of_comm.append(True)
                else:
                    value_out_of_comm.append(False)

            if all(i for i in value_out_of_comm):
                spurious_cmd_locks.setdefault(f"{receiver}",[]).append(locked_time)
                print(f"   - Spurious Command Lock on Receiver-{receiver} "
                      f"""found at "{locked_time.strftime("%Y:%j:%H:%M:%S.%f")}z".""")

    return spurious_cmd_locks


def write_spurious_cmd_locks(spurious_cmd_locks):
    """
    Description: Add all the spurious cmd locks the perf_health_section string
    Input: spurious_cmd_locks <dict>
    Ouput: Modified perf_health_section <str>
    """
    print("   - Writing Spurious CMD Locks...")
    return_string = ""
    for receiver, date_list in spurious_cmd_locks.items():
        for date in date_list:
            date_time = date.strftime("%Y:%j:%H:%M:%S.%f")
            if receiver:
                return_string += (
                    f"<li>Spurious Command Lock found on Receiver-{receiver} "
                    f"""at {date_time}z</li>\n""")
    return_string += "</ul>"
    return return_string
