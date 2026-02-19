"SSR Data request methods for CCDM Weekly"

import pandas as pd
import urllib
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
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

@dataclass
class SSRRolloverData:
    "dataclass for an SSR Rollover event"
    rollover_type: Optional[str]
    time: Optional[datetime]

@dataclass
class BEATData:
    "Dataclass for BEAT Data"
    ssr:       None
    submodule: None
    dbe_count: None
    ts:        None
    tp:        None


def check_attributes(obj):
    "Check if all attributes of an object are not None"
    for attr_name in obj.__dict__:
        if obj.__dict__[attr_name] is None:
            return False
    return True


def get_ssr_data(user_vars):
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

    return ssr_data


def parse_beat_report(beat_dir,user_vars):
    """
    Description: Parse a BEAT file
    Input: BEAT file directory path
    Output: Two dicts
    """
    data_point= BEATData(None,None,None,None,None)

    with open(beat_dir, 'r', encoding= "utf-8") as file:
        cur_state, data_list= "FIND_SSR", []
        for line in file:
            if cur_state == "FIND_SSR":
                if line[0:5] == "SSR =":
                    data_point.ssr= line[6]
                    cur_state= "FIND_SUBMOD"
            elif cur_state == "FIND_SUBMOD":
                if line[0:7] == "SubMod ":
                    cur_state= "REC_SUBMOD"
            elif cur_state == "REC_SUBMOD":
                if line[0].isdigit():
                    split_line= line.split()
                    data_point.submodule= int(split_line[0])
                    data_point.dbe_count= int(split_line[3])
                    data_point.ts=        CxoTime(split_line[4])
                    data_point.tp=        CxoTime(split_line[5])
                else:
                    cur_state = 'FIND_SSR'

            # Append data_list if data_point fills up.
            if ((check_attributes(data_point)) and (data_point.ts <= user_vars.tp)):
                data_list.append(data_point)
                data_point= BEATData(data_point.ssr,None,None,None,None)
        file.close()

    return data_list


def get_beat_report_dirs(user_vars):
    "Return a list of <str> of BEAT files to parse."
    base_path= "/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/SSR_Short_Reports/"
    return_list= []

    # Get all files in Start Year
    dir_path= Path(f"{base_path}/{user_vars.ts.datetime.year}")
    all_beat_dirs= list(x for x in dir_path.rglob('BEAT*.*'))

    # Get all files in End year if Start/End are different.
    if user_vars.ts.datetime.year != user_vars.tp.datetime.year:
        dir_path= Path(f"{base_path}/{user_vars.tp.datetime.year}")
        all_beat_dirs += list(x for x in dir_path.rglob('BEAT*.*'))

    # Convert all entries to strings
    all_beat_dirs= list(str(x) for x in all_beat_dirs)

    # Return date range if start/stop years don't match.
    if user_vars.ts.datetime.year != user_vars.tp.datetime.year:
        for day in range((user_vars.tp.datetime - user_vars.ts.datetime).days + 1):
            cur_day= user_vars.ts + timedelta(days= day)
            return_list += (
                [s for s in all_beat_dirs if f"BEAT-{cur_day.yday[0:4]}{cur_day.yday[5:8]}" in s])
    # Return from DoY 1 thru end date.
    else:
        for day in range(0, int(user_vars.tp.datetime.strftime("%j")) + 1):
            cur_day= (
                CxoTime(f"{user_vars.ts.datetime.year}:001:00:00:00") + timedelta(days= day))
            return_list += (
                [s for s in all_beat_dirs if f"BEAT-{cur_day.yday[0:4]}{cur_day.yday[5:8]}" in s])

    return return_list


def get_ssr_beat_report_data(user_vars):
    "Parse SSR beat reports into data"
    print("Generating SSR beat report data...")
    all_beat_report_data= []

    beat_report_dirs= get_beat_report_dirs(user_vars)

    # Parse all beat reports and collect data objects
    for beat_dir in beat_report_dirs:
        data_points= parse_beat_report(beat_dir,user_vars)
        for data_point in data_points:
            if data_point not in all_beat_report_data:
                all_beat_report_data.append(data_point)

    return all_beat_report_data


def get_wk_list(user_vars,all_beat_report_data):
    "Generate the number of submodules that had DBEs in date range."
    wk_list= []
    for beat_data in all_beat_report_data:
        if user_vars.ts <= beat_data.ts <= user_vars.tp:
            wk_list.append(beat_data.submodule)
    return len(wk_list)


def get_ssr_rollover_data(user_vars):
    """
    Description: Find datetimes and data points when SSRs rolled over
    Input: User variable dates
    Output: <dict>
    """
    print("SSR Rollover Detection...")

    ssr_swap_check= user_vars.ts <= CxoTime(user_vars.ssr_prime[1]) <= user_vars.tp
    ssr_rollovers= []

    if not ssr_swap_check: # Skip if SSR swap occurred inside of date range
        ssr_data = ska_data(user_vars.ts, user_vars.tp, f"COS{user_vars.ssr_prime[0]}RCEN")
        previous_value= None

        # Shorten data list to only when SSR Prime was not recording
        for time, value in zip(ssr_data.times, ssr_data.vals):

            # Detect rollover from prime to backup
            if (previous_value == "TRUE" and value == "FALS"):
                ssr_rollovers.append(SSRRolloverData("Rollover", CxoTime(time).datetime))

            # Detect rollover from backup to prime
            elif (previous_value == "FALS" and value == "TRUE"):
                ssr_rollovers.append(SSRRolloverData("Recovery", CxoTime(time).datetime))

            previous_value= value

    else:
        ssr_rollovers.append(SSRRolloverData("Unavailable", None))

    return ssr_rollovers


def ssr_rollover_detection(user_vars):
    "ssr rollover detection"
    return_string = str()
    ssr_rollover_data = get_ssr_rollover_data(user_vars)

    # Build the return string with rollover info.
    prime= "A" if user_vars.ssr_prime[0] == "A" else "B"
    backup= "B" if prime == "A" else "A"

    if ssr_rollover_data:
        for data_point in ssr_rollover_data:

            # Assemble the final string
            if data_point.rollover_type == "Unavailable":
                return_string= (
                    f"<li>SSR Rollover data is unavailable due to an SSR prime swap "
                    f"on {user_vars.ssr_prime[1]}z</li>")
                print(f"   - SSR Rollover data is unavailable due to an SSR prime swap "
                      f"on {user_vars.ssr_prime[1]}z")
                break

            if data_point.rollover_type == "Rollover":
                return_string += (
                    f"<li>SSR {data_point.rollover_type} from SSR-{prime} "
                    f"to SSR-{backup} on {data_point.time}z</li>")
                print(f"   - SSR Rollover from SSR-{prime} to SSR-{backup} on {data_point.time}")

            if data_point.rollover_type == "Recovery":
                return_string += (
                    f"<li>SSR {data_point.rollover_type} from SSR-{backup} "
                    f"to SSR-{prime} on {data_point.time}z</li>")
                print(f"   - SSR Recovery from SSR-{backup} to SSR-{prime} on {data_point.time}")

    else:
        print("   - No SSR rollover detected.")

    return f"{return_string}</li></ul></div></div>"


def make_ssr_by_submod(ssr,user_vars,all_beat_report_data,ftitle):
    """
    Description: Build SSR By Submodule plot
    Input: SSR <str>, year <str>, doy_ts <str>, doy_tp <str>, submod_dict {dict}, ....
    Output: None
    """
    root= ("/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/"
           f"SSR_Weekly_Charts/{user_vars.ts.datetime.year}/")
    fname= (f"{root}SSR_{ssr}_{user_vars.ts.datetime.year}_"
            f"{user_vars.ts.datetime.strftime('%j').zfill(3)}_{ftitle}")
    fig = make_subplots(rows=4,cols=1,  x_title='SubModule #', y_title='# DBEs')

    x, y= list(range(0,128)), [0]*128
    for beat_data in all_beat_report_data:
        if beat_data.ssr == ssr:
            y[beat_data.submodule] += (1 if beat_data.dbe_count else 0)

    fig.add_trace(go.Bar(x= x[0:32],y= y[0:32],width= 0.9),row= 1,col= 1)
    fig.add_trace(go.Bar(x= x[32:64],y= y[32:64],width= 0.9),row= 2,col= 1)
    fig.add_trace(go.Bar(x= x[64:96],y= y[64:96],width= 0.9),row= 3,col= 1)
    fig.add_trace(go.Bar(x= x[96:128],y= y[96:128],width= 0.9),row= 4,col= 1)
    fig.update_traces(marker_line_color= "black",marker_line_width= 1,opacity= 0.6)

    fig.update_layout(
        title= (f"{user_vars.ts.datetime.year} SSR-{ssr} Year-to-DOY "
                f"{user_vars.tp.datetime.strftime("%j")} DBE by Submodule"),
        autosize= False,width= 1040,height= 700,showlegend= False,
        font={"family":"Courier New, monospace","size":14,"color":"RebeccaPurple"})
    fig.update_layout(barmode= "group",xaxis_tickangle= -90)
    fig.update_yaxes(range=[0, max(y[0:127])+1])
    fig.write_html(f"{fname}.html",include_plotlyjs= "directory",auto_open= False)


def make_ssr_by_doy(ssr,user_vars,all_beat_report_data,ftitle):
    "Generate Plot SSR by DoY"
    root= ("/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/"
           f"SSR_Weekly_Charts/{user_vars.ts.datetime.year}/")
    fname= (f"{root}SSR_{ssr}_{user_vars.ts.datetime.year}_"
            f"{user_vars.ts.datetime.strftime('%j').zfill(3)}_{ftitle}")
    fig = make_subplots(rows=1,cols=1,  x_title='DOY #',y_title = '# DBEs')
    doy_tp= int(user_vars.tp.datetime.strftime("%j"))
    x, y= list(range(1,doy_tp + 1)), [0]*len(list(range(1,doy_tp + 1)))

    for beat_data in all_beat_report_data:
        doy= int(beat_data.ts.datetime.strftime("%j"))
        if beat_data.ssr == ssr:
            y[doy - 1] += (1 if beat_data.dbe_count else 0)

    fig.add_trace(go.Bar(x= x,y= y,width=.9 ),row=1,col=1)
    fig.update_traces(marker_line_color= "black",marker_line_width= 1,opacity= 0.6)
    fig.update_layout(title= (f"{user_vars.tp.datetime.year} SSR-{ssr} "
                              f"DBEs from Day-of-Year 1 - {doy_tp}"),
                      autosize= False,width= 1040,height= 700,showlegend= False,
                      font={"family":"Courier New, monospace","size":14,"color":"RebeccaPurple"})
    fig.update_layout(barmode= "group",xaxis_tickangle= -90)
    fig.update_yaxes(range= [0, max(y) + 1])
    fig.write_html(f"{fname}.html",include_plotlyjs= "directory",auto_open= False)


def make_ssr_full(ssr,user_vars,all_beat_report_data,ftitle,full= False):
    "Generate SSR Plot"
    root= ("/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/"
           f"SSR_Weekly_Charts/{user_vars.ts.datetime.year}/")
    fname= (f"{root}SSR_{ssr}_{user_vars.ts.datetime.year}_"
            f"{user_vars.ts.datetime.strftime('%j').zfill(3)}_{ftitle}")
    doy_ts= int(user_vars.ts.datetime.strftime('%j'))
    doy_tp= int(user_vars.tp.datetime.strftime("%j"))

    im = [] # Build up #doy x 128 image 7x list() x 128 list()
    for doy in range((1 if full else doy_ts), doy_tp + 1):
        im.append([0]*128)

    for beat_data in all_beat_report_data:
        doy= int(beat_data.ts.datetime.strftime('%j'))

        if beat_data.ssr == ssr:
            if full:
                im[doy - 1][beat_data.submodule] += 1
            elif user_vars.ts <= beat_data.ts <= user_vars.tp:
                im[doy - doy_ts][beat_data.submodule] += 1

    fig = go.Figure(data= go.Heatmap(
                z= im,
                x= list(range(1 if full else doy_ts, doy_tp + 1)),
                y= list(range(128)),
                transpose=True,
                colorscale='Gray'
                ))
    fig.update_xaxes(title_text='Day-of-Year')
    fig.update_yaxes(title_text='Submodule #')
    fig.update_layout(
        title= (f"{user_vars.ts.datetime.year} SSR-{ssr} "
                f"DBEs from Day-of-Year {1 if full else doy_ts} - {doy_tp}"),
        autosize=False,
        width=1040, height=700, showlegend=False,
        font={"family":"Courier New, monospace","size":14,"color":"RebeccaPurple"}
    )
    fig.write_html(f"{fname}.html",include_plotlyjs='directory', auto_open=False)
