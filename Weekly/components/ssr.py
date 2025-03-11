"SSR Data request methods for CCDM Weekly"

import pandas as pd
import urllib
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from pathlib import Path
from dataclasses import dataclass
from cxotime import CxoTime
from components.data_requests import maude_data_request as maude_data
from components.data_requests import ska_data_request as ska_data


@dataclass
class SSRData:
    "Empty Data Class for data"
    ssra_good: None
    ssra_bad:  None
    ssrb_good: None
    ssrb_bad:  None


def get_ssr_data(user_vars,data):
    "returns SSRStats Object"
    print("\nFetching SSR Data...")

    url= ("https://occweb.cfa.harvard.edu/occweb/web/webapps/ifot/ifot.php?r=home&t="
        "qserver&format=list&columns=linenum&e=PLAYBACK_BCW.ssr.playback_status."
        f"ts_ssr_start_pb.status_comment&tstart={user_vars.ts}&tstop={user_vars.tp}&ul=12")
    ssr_data= SSRData(0,0,0,0)

    with urllib.request.urlopen(url) as response:
        raw_data= pd.read_html(response.read())

    for status,ssr in zip(list(raw_data[0][2][1:]),list(raw_data[0][1][1:])):
        if status == "OK" and ssr == "A":
            ssr_data.ssra_good += 1
        elif status == "FAILED" and ssr == "A":
            ssr_data.ssra_bad += 1
        elif status == "OK" and ssr == "B":
            ssr_data.ssrb_good += 1
        elif status == "FAILED" and ssr == "B":
            ssr_data.ssrb_bad += 1

    # Record ssr_data to data object
    data.ssr_data= ssr_data


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


def get_ssr_beat_reports(user_vars,data):
    "Parse SSR beat reports into data"
    print("\nGenerating SSR beat report data...")

    start= user_vars.ts
    end= user_vars.tp
    diff= end.datetime - start.datetime

    root_folder = "/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/SSR_Short_Reports/"
    dir_path = Path(f"{root_folder}/{user_vars.ts.datetime.year}")
    full_file_list_path = list(x for x in dir_path.rglob('BEAT*.*'))
    if user_vars.ts.datetime.year != user_vars.tp.datetime.year:
        dir_path = Path(f"{root_folder}/{user_vars.tp.datetime.year}")
        full_file_list_path += list(x for x in dir_path.rglob('BEAT*.*'))
    full_file_list =list(str(x) for x in full_file_list_path)

    file_list = []
    for day in range(diff.days + 1): #
        cur_day = start + day
        cur_year_str = cur_day.yday[0:4]
        cur_day_str = cur_day.yday[5:8]
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
    for idx in range(int(user_vars.ts.datetime.strftime('%j')),int(user_vars.tp.datetime.strftime('%j'))+1):
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


def ssr_rollover_detection(user_vars):
    "ssr rollover detection"
    ssr_rollover_data = get_ssr_rollover_data(user_vars)
    return add_ssr_rollovers(user_vars,ssr_rollover_data)


def get_ssr_rollover_data(user_vars):
    """
    Description: Find datetimes and data points when SSRs rolled over
    Input: User variable dates
    Output: <dict>
    """
    print("SSR Rollover Detection...")
    ssr_data = ska_data(user_vars.ts, user_vars.tp, f"COS{user_vars.ssr_prime[0]}RCEN")
    ssr_times, ssr_values = ssr_data.times, ssr_data.vals
    ssr_rollover_datetimes = {}

    # Shorten data list to only when SSR Prime was not recording
    for index, (time, value) in enumerate(zip(ssr_times, ssr_values)):

        # Detect rollover from prime to backup
        if (ssr_values[index - 1] == "TRUE"
            and value == "FALS"
            and CxoTime(time).strftime("%j") != user_vars.ts.datetime.strftime('%j')
            and CxoTime(time).strftime("%j") != user_vars.tp.datetime.strftime('%j')
        ):
            ssr_rollover_datetimes.setdefault("Prime to Backup",[]).append(
                CxoTime(time).datetime)

        # Detect rollover from backup to prime (exclude last data point)
        try:
            if (value == "FALS"
                and ssr_values[index + 1] == "TRUE"
                and CxoTime(time).strftime("%j") != user_vars.ts.datetime.strftime('%j')
                and CxoTime(time).strftime("%j") != user_vars.tp.datetime.strftime('%j')
            ):
                ssr_rollover_datetimes.setdefault("Backup to Prime",[]).append(
                    CxoTime(time).datetime)
        except IndexError: # drop the last data point, can't look at index+1 on last value
            pass

    return ssr_rollover_datetimes


def add_ssr_rollovers(user_vars, rollover_data):
    "Add SSR rollover data to config_section string"
    return_string = ""

    if user_vars.ssr_prime[0] == "A":
        backup = "B"
    else:
        backup = "A"

    if rollover_data:
        zip_data = zip(rollover_data["Prime to Backup"],
                       rollover_data["Backup to Prime"])

        for prime_to_backup, backup_to_prime in zip_data:
            rollover_date = prime_to_backup.strftime("%Y:%j:%H:%M:%S.%f")
            recovery_date = backup_to_prime.strftime("%Y:%j:%H:%M:%S.%f")

            # Assemble the final string
            return_string += (
                    f"<li>SSR Rollover from SSR-{user_vars.ssr_prime[0]} "
                    f"to SSR-{backup} on {rollover_date}z</li>")
            print(f"   - SSR Rollover from SSR-{user_vars.ssr_prime[0]} "
                  f"to SSR-{backup} on {rollover_date}")

            return_string += (
                    f"<li>SSR Recovery from SSR-{backup} "
                    f"to SSR-{user_vars.ssr_prime[0]} on {recovery_date}z</li>")
            print(f"   - SSR Recovery from SSR-{backup} "
                  f"to SSR-{user_vars.ssr_prime[0]} on {recovery_date}")

    else:
        print(" - No SSR rollover detected.")

    return_string += "</li></ul></div></div>"
    return return_string


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
        font={"family":"Courier New, monospace","size":14,"color":"RebeccaPurple"}
    )
    fig.update_layout(barmode='group', xaxis_tickangle=-90)
    fig.update_yaxes(range=[0, max(y[0:127])+1])
    if show:
        fig.show()
    if w:
        fig.write_html(fname+'.html',include_plotlyjs='directory', auto_open=False)


def make_ssr_by_doy(ssr,year,doy_ts,doy_tp,doy_dict,fname,show,w):
    "Generate Plot SSR by DoY"
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
        font={"family":"Courier New, monospace","size":14,"color":"RebeccaPurple"}
    )
    fig.update_layout(barmode='group', xaxis_tickangle=-90)
    fig.update_yaxes(range=[0, max(y[doy_ts:doy_tp])+1])
    if show:
        fig.show()
    if w:
        fig.write_html(fname+'.html',include_plotlyjs='directory', auto_open=False)


def make_ssr_full(ssr,year,doy_ts,doy_tp,doy_full,dbe_full,fname,show,w):
    "Generate SSR Plot"
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
        font={"family":"Courier New, monospace","size":14,"color":"RebeccaPurple"}
    )
    if show:
        fig.show()
    if w:
        fig.write_html(fname+'.html',include_plotlyjs='directory', auto_open=False)
