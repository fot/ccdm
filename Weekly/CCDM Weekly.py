"""
v1.6 Change Notes:
 - Improves SSR rollover detection
"""

from datetime import timedelta
import urllib.request
import json
from pathlib import Path
from os import system
import warnings
import time
import pandas as pd
from cxotime import CxoTime
from Chandra.Time import DateTime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from components.html_parts import HTML_HEADER, HTML_SCRIPT
from components.data_requests import maude_data_request as maude_data
from components.spurious_cmd_lock_detection import (
    spurious_cmd_lock_detection, write_spurious_cmd_locks)
from components.obc_error_detection import (
    get_obc_report_dirs, get_obc_error_reports, write_obc_errors)
from components.vcdu_rollover_detection import vcdu_rollover_detection
from components.limit_violation_detection import (
    get_limit_report_dirs, get_limit_reports, write_limit_violations)
from components.eia_sequencer_selftest_detection import sequencer_selftest_detection
from components.ssr_rollover_detection import ssr_rollover_detection
from components.scs107_detection import scs107_detection
from components.misc import create_dir
warnings.filterwarnings('ignore')


class DataObject:
    "Empty data object to save data to"


class UserVariables:
    "User defined variables"
    def __init__(self):
        system('clear')
        self.get_start_year()
        self.get_end_year()
        self.get_dir_path()
        self.get_ssr_prime()
        self.get_start_doy()
        self.get_end_doy()
        self.get_times()
        self.get_major_events()
        self.get_cdme_performance_events()
        self.get_rf_performance_events()
        self.get_limit_violation_events()
        self.get_tlm_corruption_events()
        self.get_cdme_misc_comments()

    def get_start_year(self):
        "Constant value for each year, don't want user to have to input this every week"
        self.start_year = 2024
        print(f"START year is set at: {self.start_year}")

    def get_end_year(self):
        "Constant value for each year, don't want user to have to input this every week"
        self.end_year = 2024
        print(f"END year is set at: {self.end_year}")

    def get_dir_path(self):
        "User input for set directory"
        self.set_dir = "/home/rhoover/python/Code/Chandra_CCDM/Weekly"
        print(f"Set directory is: {self.set_dir}")

    def get_ssr_prime(self):
        "User input for SSR prime"
        self.ssr_prime = ["B","2024:213:05:26:34"]
        print(f"Prime SSR is set at: {self.ssr_prime}")

    def get_start_doy(self):
        "User input for start doy"
        while True:
            doy_input = input('Enter the START day: XXX ')
            if (len(str(doy_input)) == 3) and (1 <= int(doy_input) <= 366):
                break
            print(f"{doy_input} was an invalid input, please try again")
        self.doy_start = doy_input

    def get_end_doy(self):
        "User input for end doy"
        while True:
            doy_input = input('Enter the END day: XXX ')
            if (int(doy_input) - 6) != int(self.doy_start):
                print(f"{doy_input} was not 7 days from {self.doy_start}")
            elif (len(str(doy_input)) == 3 and (1 <= int(doy_input) <= 366)):
                break
            else:
                print(f"{doy_input} was an invalid input, please try again\n")
        self.doy_end = doy_input

    def get_times(self):
        "Generates CxoTime objects from user inputs"
        self.ts = CxoTime(f"{self.start_year}:{self.doy_start}:00:00:00")
        self.tp = CxoTime(f"{self.end_year}:{self.doy_end}:23:59:59.999")

    def get_major_events(self):
        "User input for Major events this week"
        while True:
            major_events_list = []
            print(
                "\n----Major Events Input----\n"
                "   Enter unexpected events that occured for the reporting week, "
                "(ie, CTU TLM processor resets, ect...)"
                """\n   Enter nothing when completed with Major Event Inputs."""
            )

            while True:
                input_item = input("   - Input: ")
                if input_item in (""):
                    break
                major_events_list.append(input_item)
            self.major_events_list = major_events_list
            valid_input = input("   Major Events Input(s) Accurate? Y/N: ")

            if valid_input in ("y","Y","yes","YES"):
                break

            print("    - Clearing Major Events list...")
            time.sleep(0.5)

    def get_cdme_performance_events(self):
        "User input for CDME Performance Notes for this week."
        while True:
            cdme_performance_list = []
            print(
                "\n----CDME Performance Events Input----\n"
                "   Enter any info about any off-nominal behavior that occured for the "
                "reporting week, (ie, IU resets, CTU CMD processor resets, ect...)"
                """\n   Enter nothing when completed with CDME Performance Note Inputs."""
            )
            while True:
                input_item = input("   - Input: ")
                if input_item in (""):
                    break
                cdme_performance_list.append(input_item)

            self.cdme_performance_list = cdme_performance_list
            valid_input = input("   CDME Perf Input(s) Accurate? Y/N: ")

            if valid_input in ("y","Y","yes","YES"):
                break

            print("    - Clearing CDME Perf list...")
            time.sleep(0.5)

    def get_rf_performance_events(self):
        "User input for RF Performance Notes for this week."
        while True:
            rf_performance_list = []
            print(
                "\n----RF Performance Events Input----\n"
                "   Enter any info about any off-nominal behavior that occured for the reporting "
                "week, (ie, unexpected command lock drops, ect...)"
                """\n   Enter nothing when completed with CDME Performance Note Inputs."""
            )
            while True:
                input_item = input("   - Input: ")
                if input_item in (""):
                    break
                rf_performance_list.append(input_item)

            self.rf_performance_list = rf_performance_list
            valid_input = input("   RF Perf Input(s) Accurate? Y/N: ")

            if valid_input in ("y","Y","yes","YES"):
                break

            print("    - Clearing RF Perf list...")
            time.sleep(0.5)

    def get_limit_violation_events(self):
        "User input for non-automated limit violations"
        while True:
            limit_violations_list = []
            print(
                "\n----Limit Violation (Non-Autogen) Input----\n"
                "   Enter any additional limit violations that aren't handled automatically "
                "(ie, non-CCDM limit violations, ect...)"
                """\n   Enter nothing when completed with CDME Performance Note Inputs."""
            )
            while True:
                input_item = input("   - Input: ")
                if input_item in (""):
                    break
                limit_violations_list.append(input_item)

            self.limit_violations_list = limit_violations_list
            valid_input = input("   Limit Violation Input(s) Accurate? Y/N: ")

            if valid_input in ("y","Y","yes","YES"):
                break

            print("    - Clearing Limit Violations list...")
            time.sleep(0.5)

    def get_tlm_corruption_events(self):
        "User input for Telemetry Corrcution Events for this week."
        while True:
            tlm_corruption_list = []
            print(
                "\n----Telemetry Corruption Input(s)----\n"
                "   Enter info about any telemetry corruption that occured for the reporting week, "
                """\n   Enter nothing when completed with Telemetry Corruption Note Inputs."""
            )
            while True:
                input_item = input("   - Input: ")
                if (input_item in ("")) and (len(tlm_corruption_list) == 0):
                    tlm_corruption_list.append("Nominal.")
                    break
                if input_item in (""):
                    break
                tlm_corruption_list.append(input_item)

            self.tlm_corruption_list = tlm_corruption_list
            valid_input = input("   Telemetry Corruption Input(s) Accurate? Y/N: ")

            if valid_input in ("y","Y","yes","YES"):
                break

            print("    - Clearing Telemetry Corruption list...")
            time.sleep(0.5)

    def get_cdme_misc_comments(self):
        "User input for CDME misc comments for this week."

        while True:
            cdme_misc_comments_list = []
            print(
                "\n----CDME Misc Comment Input(s)----\n"
                "   Enter any additional comments that occured for the reporting week, "
                """\n   Enter nothing when completed with CDME Misc Note Inputs."""
            )
            while True:
                input_item = input("   - Input: ")
                if input_item in (""):
                    break
                cdme_misc_comments_list.append(input_item)
            valid_input = input("   CDME Misc Comment Input(s) Accurate? Y/N: ")

            if valid_input in ("y","Y","yes","YES"):
                break

            print("    - Clearing CDME Misc Comment list...")
            time.sleep(0.5)
        self.cdme_misc_comments_list = cdme_misc_comments_list


def get_tx_on(ts,tp,tx):
    "returns 'ON' if specified transmitter was on during this interval."
    ctx = maude_data(ts,tp,f"STAT_5MIN_MIN_CTX{tx}X")
    ctx_val = map(int,ctx['data-fmt-1']['values'])
    if min(ctx_val) == 0:
        return 'ON'
    return 'OFF'


def get_support_stats(ts,tp):
    """
    Description: returns two lists, one of BOT times, and EOT times in the 
                 interval as well as the number of supports
    Input: Times
    Output: list of strings [<str>], [<str>]
    """
    t_off = timedelta(seconds=3600)
    ts_off = ts - t_off
    tp_off = tp - t_off
    base_url = (
        "https://occweb.cfa.harvard.edu/occweb/web/webapps/ifot/ifot.php?r=home&t=qserver&format="
        "list&e=PASSPLAN.sched_support_time.ts_bot.eot&columns=type_desc,sheetlink,tstart&tstart="
    )
    url  = base_url+str(ts_off)+"&tstop="+str(tp_off) +"&ul=12"
    response = urllib.request.urlopen(url)
    html = response.read()
    tmp_data = pd.read_html(html)
    bot_list = tmp_data[0][4][1:]
    eot_list = tmp_data[0][5][1:]
    bot_times =[]
    eot_times =[]
    for ii,jj in zip(bot_list,eot_list):
        try: # should do a better job of handling poorly formatted
            cur_bot = CxoTime(ii)
        except Exception:
            cur_bot = "FAIL"
        if isinstance(cur_bot,CxoTime):
            bot_times.append(cur_bot)
            eot_times.append(jj)
    num_supports = len(bot_times)
    eot_out_list = []
    bot_out_list = []
    for ii,jj in zip(bot_times,eot_times):
        bot_hod = int(ii.date[9:11])
        eot_hod = int(jj[0:2])
        if bot_hod > eot_hod:  # we've wrapped around to the next day
            eot_offset = timedelta(seconds=86400)
        else:
            eot_offset = timedelta(seconds=0)
        eot_str = list(ii.date)
        eot_str[9:11] = jj[0:2]
        eot_str[12:14] = jj[2:4]
        eot_str[15:17] = '00'
        eot_time = CxoTime("".join(eot_str)) + eot_offset
        eot_out_list.append(eot_time)
        bot_out_list.append(CxoTime(ii))
    return bot_out_list,eot_out_list, num_supports


def get_dsn_drs(ts,tp):
    "return a table of DR reports from iFOT"
    base_url = (
        "https://occweb.cfa.harvard.edu/occweb/web/webapps/ifot/ifot.php?r=home&t=qserver&a=show&"
        "format=list&columns=id,type_desc,tstart,properties&size="
        "auto&e=DSN_DR.problem&op=properties&tstart="
    )
    url = base_url+ str(ts)+"&tstop="+str(tp)+"&ul=12"
    response = urllib.request.urlopen(url)
    html = response.read()
    df_tmp = pd.read_html(html)
    return df_tmp


def get_ssr_stats(ts,tp):
    "returns pandas dataframe of SSR indicators along with a dict of stats"
    base_url = (
        "https://occweb.cfa.harvard.edu/occweb/web/webapps/ifot/ifot.php?r=home&t="
        "qserver&format=list&columns=linenum&e=PLAYBACK_BCW.ssr.playback_status."
        "ts_ssr_start_pb.status_comment&tstart="
    )
    url  = base_url+str(ts)+"&tstop="+str(tp) +"&ul=12"
    response = urllib.request.urlopen(url)
    html = response.read()
    df_tmp = pd.read_html(html)
    # determine which SSRs were active during  the period
    ssrs = list(df_tmp[0][1][1:])
    ssrs_status = list(df_tmp[0][2][1:])
    # remove status not 'OK' or 'FAILED' from consideration
    ssr_a_good = 0
    ssr_a_bad = 0
    ssr_b_good = 0
    ssr_b_bad = 0
    ssr_active = ''
    for status,ssr in zip(ssrs_status,ssrs):
        if status == 'OK' :
            if ssr == 'A':
                ssr_a_good +=1
                if 'A' not in ssr_active:
                    ssr_active += 'A'
            else:
                ssr_b_good +=1
                if 'B' not in ssr_active:
                    ssr_active += 'B'
        elif status == 'FAILED' :
            if ssr == 'A':
                ssr_a_bad +=1
                if 'A' not in ssr_active:
                    ssr_active += 'A'
            else:
                ssr_b_bad +=1
                if 'B' not in ssr_active:
                    ssr_active += 'B'

    ret_dict = {}
    ret_dict['SSR-A Good'] = ssr_a_good
    ret_dict['SSR-A Bad'] = ssr_a_bad
    ret_dict['SSR-B Good'] = ssr_b_good
    ret_dict['SSR-B Bad'] = ssr_b_bad
    ret_dict['SSR Active'] = ssr_active

    return df_tmp, ret_dict


def get_nearest_mod(t):
    """ Returns surrounding M1050 monitor state"""
    #sanitize timeformats
    t.format = "yday"
    base_url = "https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m=M1050"
    url = base_url + "&ts=" +str(t) + "&nearest=t"
    response = urllib.request.urlopen(url)
    html = response.read()
    data_after= json.loads(html)
    mod_after = int(data_after['data-fmt-1']['values'][0]) # maybe shoudl check timestamp to gate missing data
    mod_time = jsontime2cxo(str(data_after['data-fmt-1']['times'][0]))
    after_dt = (mod_time - t)*86400  # CxoTime timedelta is in fractional days for yday format
    if abs(after_dt) > 60: # Ignore monitor data that is signficantly far away.  Just assume modulation is on during a pass
        mod_after = 2
    url = base_url + "&tp=" +str(t) + "&nearest=t"
    response = urllib.request.urlopen(url)
    html = response.read()
    data_before= json.loads(html)
    mod_before = int(data_before['data-fmt-1']['values'][0])
    mod_time = jsontime2cxo(str(data_after['data-fmt-1']['times'][0]))
    before_dt = (t - mod_time)*86400 # CxoTime timedelta is in fractional days for yday format
    if abs(before_dt) > 60:
        mod_before = 2
    if (mod_before == 1) or (mod_after ==1):
        return 'OFF'
    return 'ON'


def jsontime2cxo(time_in):
    "sanitize input"
    time_str = str(time_in)
    return (
        CxoTime(time_str[0:4]+ ':' +time_str[4:7]+':' +time_str[7:9]+':'
                +time_str[9:11]+':' +time_str[11:13]+'.' +time_str[13:])
    )


def parse_beat_report(fname):
    """
    Description: Parse a BEAT file
    Input: BEAT file directory path
    Output: Two dicts
    """
    ret_dict = {}
    ret_dict['A'] = []
    ret_dict['B'] = []
    cur_state = 'FIND_SSR'
    # Codes for not found
    doy = 0
    submod = -1
    with open(fname, 'r', encoding="utf-8") as f:
        # Little state machine
        for line in f:
            if line[0:10] ==  'Dump start': # Get DOY
                parsed = line.split() # should check that
                fulldate = parsed[3].split('.')
                doy = int(fulldate[0][-3:])
            if cur_state == 'FIND_SSR':
                if line[0:5] == 'SSR =':
                    cur_ssr = line[6] #Character 'A' or 'B'
                    cur_state = 'FIND_SUBMOD'
            elif cur_state == 'FIND_SUBMOD':
                if line[0:7] =='SubMod ':
                    cur_state = 'REC_SUBMOD'
            elif cur_state == 'REC_SUBMOD':
                if line[0].isdigit():
                    parsed = line.split()
                    submod = int(parsed[0])
                    ret_dict[cur_ssr].append(submod)
                else:
                    cur_state = 'FIND_SSR'
    return doy,ret_dict


def make_ssr_by_submod(ssr,year,doy_ts,doy_tp,submod_dict,fname,show,w):
    """
    Description: Build SSR By Submodule plot
    Input: SSR <str>, year <str>, doy_ts <str>, doy_tp <str>, submod_dict {dict}, ....
    Output: None
    """
    fig = make_subplots(rows=4,cols=1,  x_title='SubModule #', y_title='# DBEs')
    x = list(map(str,submod_dict.keys()))
    y = [0]*128
    sm_idx = 0
    for doys in submod_dict.values():
        for doy in doys:
            if doy <= doy_tp:
                y[sm_idx] +=1
        sm_idx +=1

    #y = list(map(len,submod_dict.values())) # # of DBE's
    # Ignoring Submod 127 for now, need to remember why
    fig.add_trace(go.Bar(x=x[0:32], y=y[0:32],width=.9 ),row=1,col=1)
    fig.add_trace(go.Bar(x=x[32:64], y=y[32:64],width=.9  ),row=2,col=1)
    fig.add_trace(go.Bar(x=x[64:96], y=y[64:96],width=.9  ),row=3,col=1)
    fig.add_trace(go.Bar(x=x[96:127], y=y[96:127],width=.9),row=4,col=1)
    fig.update_traces( marker_line_color='black',
                    marker_line_width=1, opacity=0.6)

    fig.update_layout(
        title=f"{year} SSR-{ssr} Year-to-DOY {doy_tp } DBE by Submodule",
        autosize=False,
        width=1040,
        height=700,
        showlegend=False,
        font=dict(
            family="Courier New, monospace",
            size=14,
            color="RebeccaPurple"
        )
    )
    fig.update_layout(barmode='group', xaxis_tickangle=-90)
    fig.update_yaxes(range=[0, max(y[0:127])+1])
    if show:
        fig.show()
    if w:
        fig.write_html(fname+'.html',include_plotlyjs='directory', auto_open=False)


def make_ssr_by_doy(ssr,year,doy_ts,doy_tp,doy_dict,fname,show,w):
    fig = make_subplots(rows=1,cols=1,  x_title='DOY #',y_title = '# DBEs')
    x = list(map(str,doy_dict.keys()))
    y = list(doy_dict.values()) # # of DBE's
    fig.add_trace(go.Bar(x=x[doy_ts-1:doy_tp], y=y[doy_ts-1:doy_tp],width=.9 ),row=1,col=1)
    fig.update_traces( marker_line_color='black',
                    marker_line_width=1, opacity=0.6)

    fig.update_layout(
        title=f"{year} SSR-{ssr} DBEs from Day-of-Year {doy_ts} - {doy_tp}",
        autosize=False,
        width=1040,
        height=700,
        showlegend=False,
        font=dict(
            family="Courier New, monospace",
            size=14,
            color="RebeccaPurple"
        )
    )
    fig.update_layout(barmode='group', xaxis_tickangle=-90)
    fig.update_yaxes(range=[0, max(y[doy_ts:doy_tp])+1])
    if show:
        fig.show()
    if w:
        fig.write_html(fname+'.html',include_plotlyjs='directory', auto_open=False)


def make_ssr_full(ssr,year,doy_ts,doy_tp,doy_full,dbe_full,fname,show,w):
#    fig = make_subplots(rows=4,cols=1,  x_title='SubModule #',
#                       y_title='# DBEs')
    # reformulate data to be X = DOY, Y = Submodule err or no err.
# TBD: Update for year-spanning periods
    doy_list = [i for i in range(doy_ts,doy_tp)]
    full_dict = {}
    for ii in range(1,367):
        full_dict[ii] = []
    for cur_doy,dbe in zip(doy_full,dbe_full):
        full_dict[cur_doy] += dbe[ssr]
    im = [] # Build up #doy x 128 image of DBEs
    for doy in doy_list:
        cur_doy = [0]*128
        for dbe in full_dict[doy]:
            cur_doy[dbe] += 1
        im.append(cur_doy)
    fig = go.Figure(data=go.Heatmap(
                   z=im,
                   x=doy_list,
                   y=[i for i in range(128)],
                   transpose=True,
                   colorscale='Gray'
                   ))
    fig.update_xaxes(title_text='Day-of-Year')
    fig.update_yaxes(title_text='Submodule #')
    fig.update_layout(
        title=f"{year} SSR-{ssr} DBEs from Day-of-Year {doy_ts} - {doy_tp}",
        autosize=False,
        width=1040,
        height=700,
        showlegend=False,
        font=dict(
            family="Courier New, monospace",
            size=14,
            color="RebeccaPurple"
        )
    )
    if show:
        fig.show()
    if w:
        fig.write_html(fname+'.html',include_plotlyjs='directory', auto_open=False)


def get_ssr_data(user_vars,data):
    "Working on it"

    print("\nFetching SSR Data...")

    support_t_off = timedelta(seconds=300)
    ssr_data,ssr_stats = get_ssr_stats(user_vars.ts,user_vars.tp)
    ssr_tot_pb = ssr_stats['SSR-A Good'] + ssr_stats['SSR-B Good']
    bot,eot,num_supports = get_support_stats(user_vars.ts,user_vars.tp)

    for idx in range(len(bot)):
        bot[idx] += support_t_off
        eot[idx] -= support_t_off

    # Now iterate through each BOT-EOT interval and look for transitions...
    a_bad = {}
    b_bad = {}
    tx_a_on = 0
    tx_b_on = 0

    for idx, item in enumerate(bot):
        try:
            # Transmitter on/off statistics
            if get_tx_on(item,eot[idx],'A') == 'ON':
                tx_a_on +=1
            if get_tx_on(item,eot[idx],'B') == 'ON':
                tx_b_on +=1
            # Bad Visibility Processing
            ccmdlka = maude_data(item,eot[idx],'TR_CCMDLKA') #  Look for unlocked intervals
            ccmdlka_val, ccmdlka_time = ([] for i in range(2))
            for ii in ccmdlka['data-fmt-1']['values']:
                ccmdlka_val.append(int(ii))
            for ii in ccmdlka['data-fmt-1']['times']:
                ccmdlka_time.append(jsontime2cxo(str(ii)))
            # Traverse list of CCMDLK vals and times
            for t,val in zip(ccmdlka_time,ccmdlka_val):
                tmp_str = str(t)
                doy = tmp_str[5:8]
                if val == 1: # this is a transition to NLK
                    if (t > item) and (t < eot[idx]): #it's in the appropriate time window
                        if get_nearest_mod(t) == 'ON':    # only tag id modulation is on
                            a_bad[doy] = 1
            ccmdlkb = maude_data(item,eot[idx],'TR_CCMDLKB') # just look for unlocked intervals
            ccmdlkb_val =[]
            ccmdlkb_time =[]
            for ii in ccmdlkb['data-fmt-1']['values']:
                ccmdlkb_val.append(int(ii))
            for ii in ccmdlkb['data-fmt-1']['times']:
                ccmdlkb_time.append(jsontime2cxo(str(ii)))
            for t,val in zip(ccmdlkb_time,ccmdlkb_val):
                tmp_str = str(t)
                doy = tmp_str[5:8]
                if val == 1: # this is a transition to NLK.
                    if (t > item) and (t < eot[idx]): #it's in the appropriate time window
                        if get_nearest_mod(t) == 'ON':    # only tag id modulation is on
                            b_bad[doy] = 1
        except ReferenceError:
            print(f"IFOT ERR Pass {item.greta} - {eot[idx].greta}. "
                  "Stats not processed for this pass.")

    data.ssr_tot_pb = ssr_tot_pb
    data.ssr_data = ssr_data
    data.ssr_stats = ssr_stats
    data.a_bad = a_bad
    data.b_bad = b_bad
    data.tx_a_on = tx_a_on
    data.tx_b_on = tx_b_on
    data.bot = bot
    data.eot = eot
    data.num_supports = num_supports


def get_ssr_beat_reports(user_vars,data):
    "Parse SSR beat reports into data"

    print("Generating SSR beat report data...")

    start = DateTime(f"{user_vars.start_year}:001")
    end = DateTime(f"{user_vars.start_year}:{user_vars.doy_end}")
    root_folder = "/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/SSR_Short_Reports/"
    dir_path = Path(root_folder + "/" + str(user_vars.start_year))
    full_file_list_path = list(x for x in dir_path.rglob('BEAT*.*'))
    if user_vars.start_year != user_vars.end_year:
        dir_path = Path(root_folder + "/" +  user_vars.end_year)
        full_file_list_path += list(x for x in dir_path.rglob('BEAT*.*'))
    full_file_list =list(str(x) for x in full_file_list_path)

    file_list = []
    for day in range(int(end-start)+1): #
        cur_day = start + day
        cur_year_str = cur_day.year_doy[0:4]
        cur_day_str = cur_day.year_doy[-3:]   
        matching = [s for s in full_file_list if f"BEAT-{cur_year_str}{cur_day_str}" in s]
        file_list += matching

    doy_dict_a = {}
    doy_dict_b = {}
    doy_dict_a_all = {}
    doy_dict_b_all = {}
    submod_dict_a = {}
    submod_dict_b = {}
    for ii in range(366):  # slice all submods by doy (time on x-axis)
        doy_dict_a[ii+1] = 0
        doy_dict_b[ii+1] = 0
        doy_dict_a_all[ii+1] = []
        doy_dict_b_all[ii+1] = []
    submod_dict_a = {}
    submod_dict_b = {}
    for ii in range(128):  # slice all days by submods
        submod_dict_a[ii] = [] # Insert list of days when processing
        submod_dict_b[ii] = [] # Insert list of days when processing

    doy_full = []
    dbe_full = []
    for fnum in range(len(file_list)):
        doy,dbe =   parse_beat_report(file_list[fnum])
        if doy != 0:   # very occaisonal midnight spanning results in a BEAT parse error
            doy_full.append(doy)
            dbe_full.append(dbe)
            doy_dict_a_all[doy] += dbe['A']
            doy_dict_b_all[doy] += dbe['B']
            doy_dict_a[doy] += len(dbe['A'])
            doy_dict_b[doy] += len(dbe['B'])
            for sm in dbe['A']:
                submod_dict_a[sm].append(doy)
            for sm in dbe['B']:
                submod_dict_b[sm].append(doy)
    # Weekly stats
    wk_list = []
    for idx in range(int(user_vars.doy_start),int(user_vars.doy_end)+1):
        cur_day = doy_dict_b_all[idx]
        for el in cur_day:
            wk_list.append(el)
        cur_day = doy_dict_a_all[idx]
        for el in cur_day:
            wk_list.append(el)

    data.doy_full = doy_full
    data.dbe_full = dbe_full
    data.doy_dict_a = doy_dict_a
    data.doy_dict_b = doy_dict_b
    data.doy_dict_a_all = doy_dict_a_all
    data.doy_dict_b_all = doy_dict_b_all
    data.submod_dict_a = submod_dict_a
    data.submod_dict_b = submod_dict_b
    data.wk_list = wk_list


def build_config_section(user_vars, data):
    "build the CONFIGURATION section of the report"

    config_section = (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        """<p><strong>CONFIGURATION:</strong></p></div></div>"""
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
    )

    # CDME Section
    config_section += (
        "<div><div><ul><li><strong>CDME:</strong><ul>"
        "<li>All A-side Equipment is in use</li>"
        f"<li>SSR-{user_vars.ssr_prime[0]} selected as "
        f"Prime since {user_vars.ssr_prime[1]}</li>"
    )

    for list_item in user_vars.cdme_misc_comments_list:
        config_section += (
            f"""<li>{list_item}</li>"""
        )

    # CDME Section - SSR Rollover Detection
    config_section += ssr_rollover_detection(user_vars)

    # RF Section
    config_section += (
        "<div><div><ul><li><strong>RF:</strong><ul>"
        f"<li><strong>{data.num_supports}</strong> DSN Supports this week</li>"
        f"<li><strong>{data.tx_a_on}</strong> TX-A/PA-A</li>"
        f"<li><strong>{data.tx_b_on}</strong> TX-B/PA-B</li>"
        )
    config_section += "</li></ul></div></div>"

    # Bad Visibility Days Section
    config_section += (
        "<div><div><ul><li><strong>Bad Visibility Days:</strong><ul>"
        f"<li>Receiver-A: {str(list(data.a_bad.keys()))}</li>"
        f"<li>Receiver-B: {str(list(data.b_bad.keys()))}</li>"
    )
    config_section += "</li></ul></div></div>"

    # DSN DR(s) Section
    config_section += (
        "<div><div><ul><li><strong>DSN DRs this week:</strong><ul>"
    )
    tmp = get_dsn_drs(user_vars.ts,user_vars.tp)
    df = tmp[0]
    result = df.to_html(
        classes="table table-stripped",
        # columns=["Event ID >","< Type Description >","< TStart (GMT) >","< DSN_DR.problem"],
        )
    if len(df) > 1:
        config_section += result
    else:
        config_section += "<li>No DSN DRs this week</li>"
    config_section += "</li></ul></div></div>"

    return config_section


def build_perf_health_section(user_vars):
    "Build the Performance and Healtlh Section"
    perf_health_dict = {
        "CDME": user_vars.cdme_performance_list,
        "RF Equipment": user_vars.rf_performance_list,
        "Limit Violations": user_vars.limit_violations_list,
        "Telemtry Corruption": user_vars.tlm_corruption_list
    }
    perf_health_section = (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        """<p><strong>PERFORMANCE & HEALTH:</strong></p></div></div>"""
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
    )
    tlm_corrup_link = "https://occweb.cfa.harvard.edu/twiki/bin/view/SC_Subsystems/CcdmTlmCorrupt"

    for title, string_list in perf_health_dict.items():
        perf_health_section += (
            f"<div><div><ul><li><strong>{title}:</strong><ul>\n"
                )

        for list_item in string_list: # User Inputted Items
            perf_health_section += (
                f"""<li>{list_item}</li>\n"""
            )

        if "CDME" in title:
            obc_error_files = get_obc_report_dirs(user_vars)
            obc_error_report_data = get_obc_error_reports(obc_error_files)

            if obc_error_report_data:
                perf_health_section += write_obc_errors(obc_error_report_data)
            elif not user_vars.cdme_performance_list:
                perf_health_section += ("<li>Nominal.</li>\n")

        elif "RF Equipment" in title:
            spurious_cmd_locks = spurious_cmd_lock_detection(user_vars)

            if spurious_cmd_locks:
                perf_health_section += write_spurious_cmd_locks(spurious_cmd_locks)
            else:
                perf_health_section += ("<li>Nominal.</li>\n")

        elif "Limit Violations" in title:
            limit_dir_list = get_limit_report_dirs(user_vars)
            limit_data = get_limit_reports(limit_dir_list)

            if limit_data:
                perf_health_section += write_limit_violations(limit_data)
            elif not user_vars.limit_violations_list:
                perf_health_section += ("<li>Nominal.</li>\n")

        elif "Telemtry Corruption" in title:
            perf_health_section += (
                f"""<li><a href="{tlm_corrup_link}">List of Telemetry Corruption Events"""
                "</a></li>\n"
                )

        perf_health_section += "</li></ul></div></div>"

    return perf_health_section


def build_ssr_dropdown(user_vars,data):
    "Build the SSR stats dropdown menus"

    dropdown_string = HTML_HEADER

    plot_title_dict = {
        'A': ['SSR-A Current Week Time Strip','SSR-A Year-to-Date By Submodule',
              'SSR-A Year-To-Date By Day-of-Year','SSR-A Year-to-Date Full Time Strip'],
        'B': ['SSR-B Current Week Time Strip','SSR-B Year-to-Date By Submodule',
              'SSR-B Year-To-Date By Day-of-Year','SSR-B Year-to-Date Full Time Strip'],
    }
    root = (
        "/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/"
        "SSR_Weekly_Charts/" + str(user_vars.start_year) + "/"
    )
    plot_loc = (
        "https://occweb.cfa.harvard.edu/occweb/FOT/engineering/ccdm/"
        "Current_CCDM_Files/Weekly_Reports/SSR_Weekly_Charts/" + str(user_vars.start_year)
    )
    dropdown_string = ""
    output_width = 1074
    output_height = 710

    for plot_group, plot_titles in plot_title_dict.items():

        dropdown_string += (
            """</div>"""
            """<p></p>"""
            f"""<button type="button" class="collapsible">SSR-{plot_group} Plots</button>"""
            """<div class="content">\n"""
            )

        for plot_title in plot_titles:

            if "Current Week Time Strip" in plot_title:
                fname = (
                    root + f"SSR_{plot_group}_" + str(user_vars.start_year) + '_' +
                    str(user_vars.doy_start).zfill(3) + '_Cur_TimeStrip'
                )
                make_ssr_full(
                    plot_group, user_vars.start_year, int(user_vars.doy_start),
                    int(user_vars.doy_end), data.doy_full, data.dbe_full, fname,
                    show=False, w=True
                    )
                url =  (
                    f"{plot_loc}/SSR_{plot_group}_{user_vars.start_year}_"
                    f"{str(user_vars.doy_start).zfill(3)}_Cur_TimeStrip.html"
                )

            elif "Year-to-Date By Submodule" in plot_title:
                fname = (
                    root + f"SSR_{plot_group}_" + str(user_vars.start_year) + "_" +
                    str(user_vars.doy_start).zfill(3) + "_YTD_by_SubMod"
                )
                make_ssr_by_submod(
                    plot_group, user_vars.start_year, 1, int(user_vars.doy_end),
                    getattr(data, f"submod_dict_{plot_group.lower()}"), fname, show=False, w=True
                    )
                url =  (
                    f"{plot_loc}/SSR_{plot_group}_{user_vars.start_year}_"
                    f"{str(user_vars.doy_start).zfill(3)}_YTD_by_SubMod.html"
                )

            elif "Year-To-Date By Day-of-Year" in plot_title:
                fname = (
                    root + f"SSR_{plot_group}_" + str(user_vars.start_year) + "_" +
                    str(user_vars.doy_start).zfill(3) + "_YTD_by_DoY"
                )
                make_ssr_by_doy(
                    plot_group, user_vars.start_year, 1, int(user_vars.doy_end),
                    getattr(data, f"doy_dict_{plot_group.lower()}"), fname, show=False, w=True
                    )
                url =  (
                    f"{plot_loc}/SSR_{plot_group}_{user_vars.start_year}_"
                    f"{str(user_vars.doy_start).zfill(3)}_YTD_by_DoY.html"
                )

            elif "Year-to-Date Full Time Strip" in plot_title:
                fname = (
                    root + f"SSR_{plot_group}_" + str(user_vars.start_year) + '_' +
                    str(user_vars.doy_start).zfill(3) + '_YTD_Timestrip'
                )
                make_ssr_full(
                    plot_group, user_vars.start_year, 1, int(user_vars.doy_end),
                    data.doy_full, data.dbe_full, fname, show=False, w=True
                    )
                url =  (
                    f"{plot_loc}/SSR_{plot_group}_{user_vars.start_year}_"
                    f"{str(user_vars.doy_start).zfill(3)}_YTD_Timestrip.html"
                )

            dropdown_string += (
                f"""<button type="button" class="collapsible">{plot_title}</button>"""
                """<div class="content">"""
                f"""<p><iframe src={url} width=\"{output_width}\" height=\"{output_height}\">"""
                """</iframe></p></div>\n"""
                )

    dropdown_string += "</body></li></ul></div></div>"

    return dropdown_string


def build_ssr_playback_section(user_vars,data):
    "Build the SSR playback section of the report"

    plot_loc = (
        "https://occweb.cfa.harvard.edu/occweb/FOT/engineering/ccdm/"
        "Current_CCDM_Files/Weekly_Reports/SSR_Weekly_Charts/"
        )
    plot_explainer_pptx = (
        "https://occweb.cfa.harvard.edu/occweb/FOT/engineering/ccdm/"
        "Current_CCDM_Files/Weekly_Reports/SSR_Weekly_Charts/SSR_Timestrip_Chart_Explainer.pptx"
        )
    ssr_playback_section = (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        """<p><strong>SSR Playback Analysis:</strong></p></div></div>"""
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        f"""<li><strong>{data.ssr_stats["SSR-A Good"]}</strong> SSR-A Playbacks were successful """
        f"""(<strong>{data.ssr_stats["SSR-A Bad"]}</strong> required re-dump)</li>"""
        f"""<li><strong>{data.ssr_stats["SSR-B Good"]}</strong> SSR-B Playbacks were successful """
        f"""(<strong>{data.ssr_stats["SSR-B Bad"]}</strong> required re-dump)</li>"""
        f"""<li><strong>{len(set(data.wk_list))}</strong> submodules with DBEs were detected in """
        f"""<strong>{data.ssr_stats["SSR-A Good"]+data.ssr_stats["SSR-B Good"]}</strong> """
        "playbacks</li>"
    )

    ssr_playback_section += (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        """<p><strong>SSR DBE Plot Links:</strong></p></div></div>"""
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        f"""<li><a href="{plot_loc}">SSR DBE Plot Archive</a> | """
        f"""<a href="{plot_explainer_pptx}">SSR DBE Plot Archive</a></li>"""
    )

    ssr_playback_section += build_ssr_dropdown(user_vars,data)
    ssr_playback_section += "</body></li></ul></div></div>"

    return ssr_playback_section


def build_clock_correlation_section(user_vars):
    "Build the Clock Correlation Data section of the report"

    clock_corr_section = (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        """<p><strong>Clock Correlation Data:</strong></p></div></div>"""
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">""")
    clock_correlation_link = (
        "https://occweb.cfa.harvard.edu/occweb/web/fot_web/eng/subsystems/ccdm/"
        f"Clock_Rate/Clock_Correlation{user_vars.start_year}.htm")
    daily_clock_rate_link = (
        "https://occweb.cfa.harvard.edu/occweb/web/fot_web/eng/subsystems/ccdm/"
        f"Clock_Rate/images/{user_vars.start_year}_Daily_Clock_Rate.png")
    uso_stability_link = (
        "https://occweb.cfa.harvard.edu/occweb/web/fot_web/eng/subsystems/ccdm/"
        "Clock_Rate/Clock_Rateindex.htm")
    clock_link_dict = {
        f"Clock Correlation Table {user_vars.start_year}":
            f"""<iframe src={clock_correlation_link} width=\"800\" height=\"700\"></iframe>""",
        f"Daily Clock Rate {user_vars.start_year}":
            f"""<img src={daily_clock_rate_link} width=\'1000\' height=\"700\"></img>""",}

    clock_corr_section += HTML_HEADER

    for plot_title, plot_link in clock_link_dict.items():
        clock_corr_section += (f"""
            <button type="button" class="collapsible">{plot_title}</button>
            <div class="content"><p>{plot_link}</p></div><p></p>\n""")

    clock_corr_section += HTML_SCRIPT

    clock_corr_section += (
        f"""<ul><li><a href="{uso_stability_link}">Link to USO Stability"""
        " - Clock Correlation Data</a></li></ul>\n")

    clock_corr_section += "</body></li></ul></div></div>"

    return clock_corr_section


def build_major_events_section(user_vars):
    "Build the Major Events section of the report."

    uso_link = "https://occweb.cfa.harvard.edu/twiki/bin/view/SC_Subsystems/EiaSelfTests"

    major_event_section = (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        """<p><strong>Major Events:</strong></p></div></div>"""
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">""")

    for list_item in user_vars.major_events_list:
        major_event_section += f"<li>{list_item}</li>"

    # VCDU rollover detection
    vcdu_rollover_string = vcdu_rollover_detection(user_vars)
    if vcdu_rollover_string:
        major_event_section += vcdu_rollover_string

    # EIA Sequencer Self-Test Detection
    eia_sequencer_selftest_string = sequencer_selftest_detection(user_vars)
    if eia_sequencer_selftest_string:
        major_event_section += eia_sequencer_selftest_string

    # SCS107 Detection
    scs107_string = scs107_detection(user_vars)
    if scs107_string:
        major_event_section += scs107_string

    major_event_section += (
        f"""<li><a href="{uso_link}">List of EIA Sequencer Self Tests</a></li>"""
    )
    major_event_section += "</li></ul></div></div>"

    return major_event_section


def build_report(user_vars,data):
    "doc string"

    print("Assembling the report...")

    file_title = (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        f"""<p><strong>CCDM Weekly Report from {user_vars.start_year}:"""
        f"""{user_vars.doy_start} through {user_vars.end_year}:{user_vars.doy_end}"""
        """</strong></p></div></div>"""
        )
    horizontal_line = (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea">"""
        """<hr></div></div>"""
        )

    config_section = build_config_section(user_vars,data)
    perf_health_section = build_perf_health_section(user_vars)
    ssr_playback_section = build_ssr_playback_section(user_vars,data)
    clock_correlation_section = build_clock_correlation_section(user_vars)
    major_event_section = build_major_events_section(user_vars)

    html_output = (
        file_title + horizontal_line + config_section + horizontal_line + perf_health_section +
        horizontal_line + ssr_playback_section + horizontal_line + clock_correlation_section +
        horizontal_line + major_event_section + horizontal_line
    )

    file_name = (
        f"CCDM_Weekly_{user_vars.start_year}{user_vars.doy_start}_"
        f"{user_vars.end_year}{user_vars.doy_end}.html"
    )

    create_dir(f"{user_vars.set_dir}/{user_vars.start_year}")

    with open(f"{user_vars.set_dir}/{user_vars.start_year}/{file_name}",
              "w",encoding="utf-8") as file:
        file.write(html_output)
        file.close()


def main():
    "Main execution"
    data = DataObject()
    user_vars = UserVariables()
    get_ssr_data(user_vars,data)
    get_ssr_beat_reports(user_vars,data)
    build_report(user_vars,data)


main()
