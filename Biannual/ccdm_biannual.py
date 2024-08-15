"Biannual data generate tool"

import copy
import time
import os
from os import system, path
from pathlib import Path
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from Ska import tdb
from Ska.engarchive import fetch_eng as fetch
from Ska.engarchive.utils import logical_intervals
from Ska.tdb import tables
from plotly.subplots import make_subplots
from Chandra.Time import DateTime
from tqdm import tqdm
from cxotime import CxoTime
from components.average_sbe_submod104_plot import build_sbe_mod104_avg_plot
from components.sbe_vs_dbe_solar_per_date_plot import build_sbe_vs_dbe_solar_date_plot
from components.dbe_seu_by_submod_plot import build_sbe_vs_dbe_submod_plot
from components.query_data_file import build_query_data_file


class Data:
    "Empty class to store data generated"


class UserVariables:
    "User inputs object. Used to store input values."
    def __init__(self):
        while True:
            system("clear")
            self.get_start_year()
            self.get_start_doy()
            self.get_end_year()
            self.get_end_doy()
            self.get_prime_ssr()
            self.set_dir = "/share/FOT/engineering/ccdm/Current_CCDM_Files/Quarterly Report/"
            self.ts = CxoTime(f"{self.start_year}:{self.start_doy}:00:00:00")
            self.tp = CxoTime(f"{self.end_year}:{self.end_doy}:23:59:59.999")
            self.input_status = input("Are these inputs correct? Y/N: ")
            if self.input_status in ("Y","y","Yes","yes"):
                break
            print("\nRestarting Inputs...\n\n")
            time.sleep(1.5)

    def get_start_year(self):
        "Takes user input for start year and checks validity, then returns"
        while True:
            start_year = input("Enter the Biannual START year: ")
            if (len(str(start_year)) == 4) and (1998 <= int(start_year) <= 2040):
                break
            print(f"{start_year} was an invalid input, please try again")
        self.start_year = start_year

    def get_start_doy(self):
        "Takes user input for start DOY and checks validity, then returns"
        while True:
            start_doy = input("Enter the Biannual START day: ")
            if (len(str(start_doy)) == 3) and (1 <= int(start_doy) <= 366):
                break
            print(f"{start_doy} was an invalid input, please try again")
        self.start_doy = start_doy

    def get_end_year(self):
        "Takes user input for end year and checks validity, then returns"
        while True:
            end_year = input("Enter the Biannual END year: ")
            if (
                (len(str(end_year)) == 4) and
                (1998 <= int(end_year) <= 2030) and
                (end_year >= self.start_year)
            ):
                break
            if end_year < self.start_year:
                print(f"({end_year}) was less than the START year input ({self.start_year}). "
                    "Please try again.")
            else:
                print("Input must be between 1998 and 2030. Please try again")
        self.end_year = end_year

    def get_end_doy(self):
        "Takes user input for end DOY and checks validity, then returns"
        while True:
            end_doy = input("Enter the Biannual END day: ")
            if (len(str(end_doy)) == 3) and (1 <= int(end_doy) <= 366):
                break
            print(f"{end_doy} was an invalid input, please try again\n")
        self.end_doy = end_doy

    def get_prime_ssr(self):
        "Takes user input to set what SSR was prime for the period"
        while True:
            prime_ssr = input("Enter which SSR was PRIME for the Biannual period (Enter A or B): ")
            if prime_ssr in ("a","A","b","B"):
                break
            print(f"{prime_ssr} was an invalid input, please try again\n")
        self.prime_ssr = prime_ssr.upper()


def display_user_instructions(user_vars):
    "Displays instructions on how to run this script properly."
    print("\n--User instructions--")

    while True:
        new_dir = input(
            "1) Enter new directory to be created with the following name format:\n"
            "   - XX_YYMMM_YYMMM\n\n   Input: "
        )
        try:
            os.mkdir(user_vars.set_dir + new_dir)
        except FileExistsError:
            if input(
                "   - Looks like that directory already exists! Please choose a different "
                """name. Or input "OKAY" to continue.: """
                ) == "OKAY":
                break
        else:
            break

    # Reset set_dir to the newly generated directory.
    user_vars.set_dir = user_vars.set_dir + new_dir

    # Make /Output Dir
    try:
        os.mkdir(f"{user_vars.set_dir}/Output/")
    except FileExistsError:
        pass

    # Make /Files/ Dir
    try:
        os.mkdir(f"{user_vars.set_dir}/Files/")
    except FileExistsError:
        pass

    # Make /Files/SSR/ Dir
    try:
        os.mkdir(f"{user_vars.set_dir}/Files/SSR/")
    except FileExistsError:
        pass

    # Make //DSN/ Dir
    try:
        os.mkdir(f"{user_vars.set_dir}/Files/DSN/")
    except FileExistsError:
        pass

    print(f"""\nConfigured Directory: "{user_vars.set_dir}"\n""")

    while True:
        input(
            f"""2) Copy previous biannual files into "{user_vars.set_dir}" directory.\n"""
            "   Rename files as follows:\n"
            """    - "full_mission_maxes.csv" --> "mission_maxes.csv"\n"""
            """    - "full_mission_mins.csv" --> "mission_mins.csv"\n"""
            """    - "full_mission_means.csv" --> "mission_means.csv"\n"""
            "\n    Input DONE once completed: "
        )
        if check_if_files_exist(user_vars):
            print("    - Files exist!\n")
            break
        print("    - Please check files again, they couldn't be found. \U0001F62D\n")


def check_if_files_exist(user_vars):
    "Checks if files were created. Returns True/False."
    file_names = ["/mission_maxes.csv","/mission_mins.csv","/mission_means.csv"]
    status = []
    for file_name in file_names:
        status.append(path.exists(user_vars.set_dir + file_name))
    return all(status)


def get_beat_reports(user_vars, data):
    """
    Description: Generates list of BEAT reports
    Input: User Variables
    Output: List of file directories
    """
    print(" - Generating BEAT report list..." )

    file_list = []
    start_day_time = DateTime(f"{user_vars.start_year}:{user_vars.start_doy}")
    end_day_time = DateTime(f"{user_vars.end_year}:{user_vars.end_doy}")
    root_folder = "/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/SSR_Short_Reports/"
    dir_path = Path(root_folder + "/" + user_vars.start_year)

    file_path_list = list(x for x in dir_path.rglob("BEAT*.*"))

    if user_vars.start_year != user_vars.end_year:
        dir_path = Path(root_folder + "/" + str(user_vars.end_year))
        # Generate second list of file paths for 2nd year
        file_path_list_end_year = list(x for x in dir_path.rglob("BEAT*.*"))

        # Combine lists into one
        for end_year_item in file_path_list_end_year:
            file_path_list.append(end_year_item)

    # Now grab relevant days
    for day in range(int(end_day_time - start_day_time)+1):
        current_day = start_day_time + day
        current_year_str = current_day.year_doy[0:4]
        current_day_str = current_day.year_doy[-3:]

        for file_path in file_path_list:
            if f"BEAT-{current_year_str}{current_day_str}" in str(file_path):
                file_list.append(file_path)

    data.file_list = file_list


def parse_beat_report(beat_report):
    "given BEAT report fname, return tuple of day-of-year and dict with SSR designator/submodules"

    ret_dict = {}
    ret_dict["A"] = []
    ret_dict["B"] = []
    cur_state = "FIND_SSR"
    # Codes for not found
    doy = 0
    submod = -1

    with open(beat_report, encoding="utf-8") as file:
        # Little state machine
        for line in file:
            if line[0:10] ==  "Dump start": # Get DOY
                parsed = line.split() # should check that
                fulldate = parsed[3].split(".")
                doy = int(fulldate[0][-3:])
            if cur_state == "FIND_SSR":
                if line[0:5] == "SSR =":
                    cur_ssr = line[6] #Character "A" or "B"
                    cur_state = "FIND_SUBMOD"
            elif cur_state == "FIND_SUBMOD":
                if line[0:7] =="SubMod ":
                    cur_state = "REC_SUBMOD"
            elif cur_state == "REC_SUBMOD":
                if line[0].isdigit():
                    parsed = line.split()
                    submod = int(parsed[0])
                    ret_dict[cur_ssr].append(submod)
                else:
                    cur_state = "FIND_SSR"
    return doy,ret_dict


def write_png_file(user_vars,figure,file_name):
    "Writes a figure to a png file"
    figure.write_image(user_vars.set_dir + "/Output/" + file_name)


def write_csv_file(user_vars,data,file_name):
    "Writes data to csv file"
    print(f"""  - Writing data to "{file_name}" in {user_vars.set_dir}...""")
    data.to_csv(user_vars.set_dir + "/Output/" + file_name)


def write_html_file(user_vars,figure,file_name):
    "Writes a figure into an HTML file"
    print(f"""  - Writing data to "{file_name}" in {user_vars.set_dir}...""")
    figure.write_html(user_vars.set_dir + "/Output/" + file_name)


def parse_csv_file(csv_file,as_dict=False):
    "Read given .csv file and return data"
    print(f"""  - Parsing file "{csv_file}"...""")
    data = pd.read_csv(csv_file)
    if as_dict:
        data.to_dict()
    return data


def get_quartely_sum_stats(data):
    "Generates all dbe data, saves to data object."

    print(" - Generating SSR data...")

    doy_full = []
    dbe_full = []
    doy_dict_a = {}
    doy_dict_b = {}
    doy_dict_a_all = {}
    doy_dict_b_all = {}
    submod_dict_a = {}
    submod_dict_b = {}
    for module in range(128):  # slice all days by submods
        submod_dict_a[module] = [] # Insert list of days when processing
        submod_dict_b[module] = [] # Insert list of days when processing

    for beat_report in data.file_list:
        doy, dbe = parse_beat_report(beat_report)
        if doy != 0:   # very occaisonal midnight spanning results in a BEAT parse error
            cur_dbe = {}
            cur_dbe["A"] = dbe["A"].copy()
            cur_dbe["B"] = dbe["B"].copy()
            doy_full.append(doy)
            dbe_full.append(cur_dbe)
            if doy in doy_dict_a_all:
                doy_dict_a_all[doy].append(dbe["A"])
            else:
                doy_dict_a_all[doy]= dbe["A"]
            if doy in doy_dict_b_all:
                doy_dict_b_all[doy].append(dbe["B"])
            else:
                doy_dict_b_all[doy]= dbe["B"]
            if doy in doy_dict_a:
                doy_dict_a[doy] += len(dbe["A"])
            else:
                doy_dict_a[doy] = len(dbe["A"])
            if doy in doy_dict_b:
                doy_dict_b[doy] += len(dbe["B"])
            else:
                doy_dict_b[doy] = len(dbe["B"])
            for sm in dbe["A"]:
                submod_dict_a[sm].append(doy)
            for sm in dbe["B"]:
                submod_dict_b[sm].append(doy)

    # Record all data
    data.doy_full = doy_full
    data.dbe_full = dbe_full
    data.doy_dict_a_all = doy_dict_a_all
    data.doy_dict_b_all = doy_dict_b_all
    data.doy_dict_a = doy_dict_a
    data.doy_dict_b = doy_dict_b
    data.submod_dict_a = submod_dict_a
    data.submod_dict_b = submod_dict_b


def make_ssr_by_submod(ssr, user_vars, data_dict, fname):
    "Generate SSR-A/B plots per submodule"

    print(
        f" - Generating SSR-{ssr} DBE Activity by Submodule for "
        f"{user_vars.start_year}:{user_vars.start_doy}-{user_vars.end_year}:{user_vars.end_doy}"
    )

    fig = make_subplots(rows=4,cols=1,y_title="# DBEs")
    x = list(map(str,data_dict.keys()))
    y = [0]*128
    sm_idx = 0
    for doys in data_dict.values():
        for doy in doys:
            y[sm_idx] +=1
        sm_idx +=1

    fig.add_trace(go.Bar(x=x[0:32], y=y[0:32],width=.9 ),row=1,col=1)
    fig.add_trace(go.Bar(x=x[32:64], y=y[32:64],width=.9  ),row=2,col=1)
    fig.add_trace(go.Bar(x=x[64:96], y=y[64:96],width=.9  ),row=3,col=1)
    fig.add_trace(go.Bar(x=x[96:128], y=y[96:128],width=.9),row=4,col=1)
    fig.update_traces( marker_line_color="black",
                    marker_line_width=1, opacity=0.6)

    fig.update_layout(
        title=(
            f"SSR-{ssr} DBE Activity, By Submodule, for {user_vars.start_year}:"
            f"{user_vars.start_doy}-{user_vars.end_year}:{user_vars.end_doy}"
        ),
        autosize=False,
        width=1250,
        height=1000,
        showlegend=False,
        font=dict(
            family="Courier New, monospace",
            size=18,
            color="RebeccaPurple"
        )
    )
    fig.update_layout(barmode="group", xaxis_tickangle=-90)
    fig.update_yaxes(range=[0, max(y[0:128])+1])
    file_name = user_vars.set_dir + "/Output/" + fname + ".html"
    fig.write_html(file_name, include_plotlyjs = "directory", auto_open=False)


def make_ssr_by_doy(ssr,user_vars, data_dict, fname):
    "Generate SSR-A/B plots per DOY"

    print(
        f" - Generating SSR-{ssr} Daily DBE Activity Plot for "
        f"{user_vars.start_year}:{user_vars.start_doy}-{user_vars.end_year}:{user_vars.end_doy}"
    )

    x = list(map(str,data_dict.keys()))
    y = list(data_dict.values()) # # of DBE"s
    fig = go.Figure([go.Bar(x=x, y=y)])

    fig.update_layout(
        title=(
            f"SSR-{ssr} Daily DBE Activity, All Submodules, for {user_vars.start_year}:"
            f"{user_vars.start_doy}-{user_vars.end_year}:{user_vars.end_doy}"
        ),
        autosize=False,
        width=1250,
        height=750,
        showlegend=False,
        font={
            "family": "Courier New, monospace",
            "size": 18,
            "color": "RebeccaPurple"
        }
    )
    fig.update_yaxes(range=[0, max(y)+1])
    file_name = user_vars.set_dir + "/Output/" + fname + ".html"
    fig.write_html(file_name, include_plotlyjs = "directory", auto_open=False)


def make_ssr_full(ssr, user_vars, data, fname):
    "Generate SSR-A/B SSR Full Plots"

    print(
        f" - Generating SSR-{ssr} DBEs Plot for {user_vars.start_year}:{user_vars.start_doy}"
        f"-{user_vars.end_year}:{user_vars.end_doy}"
    )

    full_dict = {}

    for ii in range(1,367):
        full_dict[ii] = []
    for cur_doy,dbe in zip(data.doy_full,data.dbe_full):
        full_dict[cur_doy] += dbe[ssr]
    doy_in_order = []
    im = []
    for ii in data.doy_full:
        if ii not in doy_in_order:
            doy_in_order.append(ii)
    for jj in doy_in_order:
        cur_doy = [0]*128
        for dbe in full_dict[jj]:
            cur_doy[dbe] += 1
        im.append(cur_doy)
    fig = go.Figure(data=go.Heatmap(
                   z=im,
                   x=[str(i) for i in doy_in_order],#oy_in_order,
                   y=[i for i in range(128)],
                   transpose=True,
                   colorscale="Gray"
                   ))
    fig.update_xaxes(title_text="Day-of-Year")
    fig.update_yaxes(title_text="Submodule #")
    fig.update_layout(
        title=(
            f"SSR-{ssr} DBEs from {user_vars.start_year}:{user_vars.start_doy}"
            f"-{user_vars.end_year}:{user_vars.end_doy}"
        ),
        autosize=False,
        width=1200,
        height=800,
        showlegend=False,
        font={
            "family": "Courier New, monospace",
            "size": 14,
            "color": "RebeccaPurple"
        }
    )
    file_name = user_vars.set_dir + "/Output/" + fname + ".html"
    fig.write_html(file_name, include_plotlyjs = "directory", auto_open=False)


def TimeAdjust(msid,ts,tp):
    """
    Inputs:
        msid =  MSID for which to calculate the time adjustments statistics for.  
                instance of  from ska.engarchive.fetch.MSID or Msid  Needs to have a .times field and a .msid field
        ts   =  string containing start time in a Chandra.time compatible format, e.g. "2020:100:12:12:12"
        tp   =  string containing stop time in a Chandra.time compatible format, e.g. "2020:100:12:12:12"        
    Notes/Improvements: 
        TBD: Should accept MSIDSet in addition to MSID
        NOTE: Could use times from the msid.times span, but may create problems at the beginning and end since these are subject to adjustment.  Should use time query that generated the MSID
    """
    samp_rate = tables["tsmpl"][msid.msid]["SAMPLE_RATE"]
    str_num = tables["tsmpl"][msid.msid]["STREAM_NUMBER"]
    start_minor_frame = tables["tloc"][msid.msid]["START_MINOR_FRAME"]
    fmt_dict = {1: "FMT1",2: "FMT2",3: "FMT3",4: "FMT4",5: "FMT5",72:"FMT6",6:"FMT6"}
    t_off = {}
    t_samp = {}
    str_num_2_idx = {}
    for index, stream in enumerate(str_num):
        str_num_2_idx[stream] = index
    for stream in str_num:
        fmt = fmt_dict[stream]
        off_phase = 0.25625 * start_minor_frame[str_num_2_idx[stream]]
        t_off[fmt] = off_phase
        t_samp[fmt] = (128 /  samp_rate[str_num_2_idx[stream]] ) * 0.25625
    tmf = fetch.Msid("CCSDSTMF",ts,tp)
    # generate list of intervals for each format using logical intervals
    fmts = ("FMT1","FMT2","FMT3","FMT4","FMT5","FMT6")
    tmf_intervals = {}
    for fmt in fmts:
        tmf_intervals[fmt] = logical_intervals(tmf.times,tmf.vals==fmt,complete_intervals=False)
    times = msid.times # make scratchpad copy to avoid in-place effects (I think need to check by ref or by val convention)    
    ts_labels = np.zeros(len(times))
    for fmt in fmts:
        for interval in tmf_intervals[fmt]:
            # select data from that interval
            times[(msid.times>=interval["tstart"]) & (msid.times < interval["tstop"])] += t_off[fmt]
            ts_labels[(msid.times>=interval["tstart"]) & (msid.times < interval["tstop"])] = t_samp[fmt]
    msid.times = times
    ts_msid = copy.copy(msid)
    ts_msid.vals = ts_labels # stuff it into MSID class so that we can later remove intervals...
    return msid,ts_msid


def get_daily_stats(msid,sw_msid,bad_val,yyyy,ddd,filter_rng):
    """
    Inputs:
        msid = MSID to calculate statistics for, e.g. CTXAV
        sw_msid = MSID used to remove times we don't want to include in statistic calculation.  E.g. CTXAX
        bad_val =  value of switch MSID to exclude, e.g. "OFF"
        data_toff = time to add to each data sample 
        sw_toff = time to add to each data sample 
        filter_rng = range of valid values.  values < filter_rng[0] and > filter_rng[1] will be excluded        
    Outputs:
        dictionary with keys = ["min", "max", "mean"].  
        values are numbers.  If no data is available, np.nan is returned as the value for each
    Notes/Improvements: 
        TBD: Shoud make "bad_val" a list which is applied using a logical OR sense
        TBD: may want to invert the sense of and have the user supply "good_val".  or allow either (but at least one) to be specified 
        TBD: If we want to get fancy, allow the user to supply their own boolean function and multiple MSIDs. This would effectively reproduce much of pseudo-msid GRETA"s capability 
    """
    ret_dict = {}
    ts = DateTime(yyyy + ':' + ddd + ':00:00:00') # ensure > 1 MjF buffer before collection interval
    ts_buf = ts - 33/86400
    tp = ts + 1
    data = fetch.Msid(msid,ts_buf.greta,tp.greta)
    data,data_t_samp= TimeAdjust(data,ts_buf.greta,tp.greta)
    time_oor = (data.times >= tp.secs) | (data.times < ts.secs)
    data.filter_bad(time_oor)
    data_t_samp.filter_bad(time_oor)
    data_t0 = data.times[0] # store start of data time for greta

    if (sw_msid is not None) and (len(data)>1):
        sw = fetch.MSID(sw_msid,ts_buf.greta,tp.greta)
        sw,sw_t_samp= TimeAdjust(sw,ts_buf.greta,tp.greta)
        bad_sw = sw.vals == bad_val
        bad_sw_2 = bad_sw
        bad_times = logical_intervals(sw.times,bad_sw_2,complete_intervals=False)        
        sw.remove_intervals(bad_times)
        sw_t_samp.remove_intervals(bad_times)
        time_oor = (data.times >= tp.secs) | (data.times<DateTime(data_t0).secs)
        data.filter_bad(time_oor)
        data_t_samp.filter_bad(time_oor)
        data.remove_intervals(bad_times)
        data_t_samp.remove_intervals(bad_times)
    if filter_rng is not None:
        data_out_of_range = (data.vals < filter_rng[0]) | (data.vals > filter_rng[1])
        data.filter_bad(data_out_of_range)
        data_t_samp.filter_bad(data_out_of_range)
    if len(data) > 0:
        ret_dict["min"] = np.min(data.vals)
        ret_dict["max"] = np.max(data.vals)
        data_w = np.sum(data.vals*data_t_samp.vals / np.sum(data_t_samp.vals))
        ret_dict["mean"]= data_w  # time-weighted mean
    else:                   # No data available this day
        ret_dict["min"] = np.nan
        ret_dict["max"] = np.nan
        ret_dict["mean"] = np.nan
    return ret_dict


def get_quarterly_stats(data, msid, sw_msid, bad_val, start, end):
    "Doc String"
    days = []
    data_pres = {}
    mins =  {}
    means =  {}
    maxes =  {}

    if msid in ("CTXAPWR","CTXBPWR"):
        filter_rng = [20,40]
    elif msid in ("CPA1PWR","CPA2PWR"):
        filter_rng = [20,42]
    else:
        filter_rng = None

    for day in range(int(end-start) + 1):
        cur_day = start+day
        cur_year_str = cur_day.year_doy[0:4]
        cur_day_str = cur_day.year_doy[-3:]
        cur_stats = get_daily_stats(msid,sw_msid,bad_val,cur_year_str,cur_day_str,filter_rng)
        data_pres[cur_day.year_doy] = 1
        mins[cur_day.year_doy] = cur_stats["min"]
        maxes[cur_day.year_doy] = cur_stats["max"]
        means[cur_day.year_doy] = cur_stats["mean"]
        days.append(cur_day.year_doy)

    data.days = days
    data.data_pres = data_pres
    data.mins = mins
    data.means = means
    data.maxes = maxes


def fetch_ska_data(user_vars,data,mission=False):
    "Generate entire ska data .csv files for MSID list"

    print(" - Fetching CCDM SKA Data (This will take awhile ~45 min)...")

    msid_list = [
        ("CRXAV",None,None),("CRXBV",None,None),("CRXASIG","CCMDLKA","NLCK"),
        ("CRXBSIG","CCMDLKB","NLCK"),("CRXALS","CCMDLKA","NLCK"),
        ("CRXBLS","CCMDLKB","NLCK"),("CTXAV","CTXAX","OFF"),("CTXBV","CTXBX","OFF"),
        ("CTXAPWR","CTXAX","OFF"),("CTXBPWR","CTXBX","OFF"),("CXPNAIT","CTXAX","OFF"),
        ("CXPNBIT","CTXBX","OFF"),("CPA1V","CPA1","OFF"),("CPA2V","CPA2","OFF"),
        ("CPA1PWR","CPA1","OFF"),("CPA2PWR","CPA2","OFF"),("CPA1BPT","CPA1","OFF"),
        ("CPA2BPT","CPA2","OFF"),("CTUA5V",None,None),("CTUB5V",None,None),
        ("CTUA15V","CTUTMPPR","OFF"),("CTUB15V","CTUTMPRD","OFF"),("EEPA5V","CTUEPA","OFF"),
        ("EPA15V","CTUEPA","OFF"),("EEPB5V","CTUEPB","OFF"),("EPB15V","CTUEPB","OFF"),
        ("CPCA5V","CTUPCA","OFF"),("CPCA15V","CTUPCA","OFF"),("CPCB5V","CTUPCB","OFF"),
        ("CPCB15V","CTUPCB","OFF"),("CSITA5V","CTUSIA","OFF"),("CSITA15V","CTUSIA","OFF"),
        ("CSITB5V","CTUSIB","OFF"),("CSITB15V","CTUSIB","OFF"),("CTSA5V","CTUTSA","OFF"),
        ("CTSA15V","CTUTSA","OFF"),("CTSB5V","CTUTSB","OFF"),("CTSB15V","CTUTSB","OFF"),
        ("CIUA5V",None,None),("CIUA15V",None,None),("CIUB5V",None,None),("CIUB15V",None,None),
        ("CUSOA28V",None,None),("CUSOAOVN",None,None),("CUSOAIT",None,None),("CUSOB28V",None,None),
        ("CUSOBOVN",None,None),("CUSOBIT",None,None),("CXO5VOBA",None,None),("CXO5VOBB",None,None),
        ("EIACVAV",None,None),("EIACVBV",None,None),("CSSR1CAV",None,None),("CSSR2CBV",None,None)
    ]

    df_mins= pd.DataFrame()
    df_means= pd.DataFrame()
    df_maxes= pd.DataFrame()

    if mission:
        start = DateTime("2000:002")
    else:
        start = DateTime(f"{user_vars.start_year}:{user_vars.start_doy}")
    end= DateTime(f"{user_vars.end_year}:{user_vars.end_doy}")

    for msid in tqdm(msid_list):
        get_quarterly_stats(data,msid[0],msid[1],msid[2],start,end)
        df_min = pd.DataFrame({msid[0]:data.mins})
        df_mean = pd.DataFrame({msid[0]:data.means})
        df_max = pd.DataFrame({msid[0]:data.maxes})
        df_mins= pd.concat([df_mins,df_min],axis=1)
        df_means= pd.concat([df_means,df_mean],axis=1)
        df_maxes= pd.concat([df_maxes,df_max],axis=1)

    write_csv_file(
        user_vars,df_mins,("biannual_mins_LS.csv" if not mission else "mission_mins.csv")
        )
    write_csv_file(
        user_vars,df_means,("biannual_means_LS.csv" if not mission else "mission_means.csv")
        )
    write_csv_file(
        user_vars,df_maxes,("biannual_maxes_LS.csv" if not mission else "mission_maxes.csv")
        )


def generate_report_tables(user_vars):
    """
    Description: Uses user data to generate SKA data Plots for Biannual Period.
    Input: User Varaibles, data object
    Output: PNG files of plots.
    """
    print(" - Generating SKA Data Tables...")

    rf_msids = [
        "CTXAV","CTXBV","CTXAPWR","CTXBPWR","CRXAV","CRXBV","CRXASIG",
        "CRXBSIG","CRXALS","CRXBLS","CPA1V","CPA2V","CPA1PWR","CPA2PWR"
        ]
    cdme_msids = [
        "CTUA5V","CTUB5V","CTUA15V","EEPA5V","EPA15V","CPCA5V","CPCA15V",
        "CSITA5V","CSITA15V","CTSA5V","CTSA15V","CIUA5V","CIUA15V","EIACVAV",
        "EIACVBV","CSSR1CAV","CSSR2CBV"
        ]

    df_mins = parse_csv_file(user_vars.set_dir + "/Output/" + "biannual_mins_LS.csv")
    tmp = list(df_mins.columns)
    tmp[0] = 'Mission Day'
    df_mins.columns = tmp

    df_means = parse_csv_file(user_vars.set_dir + "/Output/" + "biannual_means_LS.csv")
    tmp = list(df_means.columns)
    tmp[0] = 'Mission Day'
    df_means.columns = tmp

    df_maxes = parse_csv_file(user_vars.set_dir + "/Output/" + "biannual_maxes_LS.csv")
    tmp = list(df_maxes.columns)
    tmp[0] = 'Mission Day'
    df_maxes.columns = tmp

    df_rf = pd.concat([
        df_means.loc[:,rf_msids].mean(),df_mins.loc[:,rf_msids].min(),
        df_maxes.loc[:,rf_msids].max()],axis=1
        )
    df_cdme = pd.concat([
        df_means.loc[:,cdme_msids].mean(),df_mins.loc[:,cdme_msids].min(),
        df_maxes.loc[:,cdme_msids].max()],axis=1
        )
    df_all_means = df_means.loc[:,:]
    df_all_mins = df_mins.loc[:,:]
    df_all_maxes = df_maxes.loc[:,:]

    write_csv_file(user_vars,df_rf,"rf_stats.csv")
    write_csv_file(user_vars,df_cdme,"cdme_stats.csv")
    write_csv_file(user_vars,df_all_means,"period_means.csv")
    write_csv_file(user_vars,df_all_mins,"period_mins.csv")
    write_csv_file(user_vars,df_all_maxes,"period_maxes.csv")


def generate_full_mission_tables(user_vars):
    """
    Description: Generate full mission tables from parsed csv files
    Input: User Variables, generated csv files.
    Output: csv files.
    """

    print(" - Generating Full Mission Table csv(s)...")

    df_means_per = parse_csv_file(user_vars.set_dir + "/Output/" + "biannual_means_LS.csv")
    tmp = list(df_means_per.columns)
    tmp[0] = "Mission Day"
    df_means_per.columns = tmp

    df_mins_per = parse_csv_file(user_vars.set_dir + "/Output/" + "biannual_mins_LS.csv")
    tmp = list(df_mins_per.columns)
    tmp[0] = "Mission Day"
    df_mins_per.columns = tmp

    df_maxes_per = parse_csv_file(user_vars.set_dir + "/Output/" + "biannual_maxes_LS.csv")
    tmp = list(df_maxes_per.columns)
    tmp[0] = "Mission Day"
    df_maxes_per.columns = tmp

    df_means  = parse_csv_file(user_vars.set_dir + "/mission_means.csv")
    tmp = list(df_means.columns)
    tmp[0] = "Mission Day"
    df_means.columns = tmp

    df_mins  = parse_csv_file(user_vars.set_dir + "/mission_mins.csv")
    tmp = list(df_mins.columns)
    tmp[0] = "Mission Day"
    df_mins.columns = tmp

    df_maxes  = parse_csv_file(user_vars.set_dir + "/mission_maxes.csv")
    tmp = list(df_maxes.columns)
    tmp[0] = "Mission Day"
    df_maxes.columns = tmp

    df_means_full = pd.concat([df_means,df_means_per],ignore_index=True)
    df_mins_full = pd.concat([df_mins,df_mins_per],ignore_index=True)
    df_maxes_full = pd.concat([df_maxes,df_maxes_per],ignore_index=True)

    write_csv_file(user_vars,df_means_full,"full_mission_means.csv")
    write_csv_file(user_vars,df_mins_full,"full_mission_mins.csv")
    write_csv_file(user_vars,df_maxes_full,"full_mission_maxes.csv")


def generate_appendix_figure(user_vars,df_means,df_mins,df_maxes,mission=False):
    "Generate appendix figures based on csv file data passed"

    ranges = {
        "CRXAV": [3.8,4.2], "CRXBV": [3.8,4.2], "CRXASIG": [-140,-40], "CRXBSIG": [-140,-40],
        "CRXALS": [-200,200], "CRXBLS": [-200,200], "CTXAV": [3.4,3.7], "CTXBV": [3.4,3.7],
        "CTXAPWR": [36,37], "CTXBPWR": [36,37], "CPA1V": [3.8,4.2], "CPA2V": [3.8,4.2],
        "CPA1PWR":  [32,42], "CPA2PWR":  [32,42], "CXO5VOBA": [4.7,5.2], "CXO5VOBB": [4.7,5.2],
        "CUSOAOVN": [0,1], "CUSOA28V": [22,30], "CSSR1CAV": [0,6], "CSSR2CBV": [0,6]
        }

    for cur_msid in tqdm(ranges):
        msid = tdb.msids[cur_msid]
        if len(msid.Tlmt) > 2 :
            warn_low = msid.Tlmt[4]
            caut_low = msid.Tlmt[2]
            caut_high = msid.Tlmt[3]
            warn_high = msid.Tlmt[5]
        else:
            if msid.Tlmt[0][1] == 1:
                sel_lim = msid.Tlmt[0]
            else:
                sel_lim = msid.Tlmt[1]
            warn_low = sel_lim[4]
            caut_low = sel_lim[2]
            caut_high = sel_lim[3]
            warn_high = sel_lim[5]

        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x = df_means["Mission Day"], y = df_mins[cur_msid],
                name = "Min", line = {"color":"blue","width":1}
                )
            )
        figure.add_trace(
            go.Scatter(
                x = df_means["Mission Day"], y = df_maxes[cur_msid],
                name = "Max", line = {"color":"green","width":1}
                )
            )
        figure.add_trace(
            go.Scatter(
                x = df_means["Mission Day"], y = df_means[cur_msid],
                name = "Mean", line = {"color":"black","width":3}
                )
            )
        figure.update_yaxes(range = ranges[cur_msid])
        figure.update_layout(
            title=(
                f"{msid.technical_name} Limits:({warn_low}/{caut_low}:"
                f"{caut_high}/{warn_high}) - {cur_msid}"
                ),
            xaxis_title = "Mission Date", yaxis_title = f"{msid.eng_unit}",
            autosize = False, width = 1400, height = 800,
            legend = {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "center",
                "x": 0.1
                },
            font = {
                "family": "Courier New, monospace",
                "size": 20,
                "color": "RebeccaPurple"
                },
            )
        write_png_file(user_vars,figure,f"{cur_msid}.png" if mission else f"period_{cur_msid}.png")


def generate_mission_appendix_plots(user_vars):
    "Generate mission appendix plots from csv file data."

    print(" - Generating Mission Appendix Plots...")
    df_means = parse_csv_file(user_vars.set_dir + "/Output/" + "full_mission_means.csv")
    df_mins  = parse_csv_file(user_vars.set_dir + "/Output/" + "full_mission_mins.csv")
    df_maxes = parse_csv_file(user_vars.set_dir + "/Output/" + "full_mission_maxes.csv")
    generate_appendix_figure(user_vars,df_means,df_mins,df_maxes,True)


def generate_period_appendix_plots(user_vars):
    "Generate period appendix plots from csv file data."

    print(" - Generating Period Appendix Plots...")
    df_means = parse_csv_file(user_vars.set_dir + "/Output/" + "period_means.csv")
    df_mins  = parse_csv_file(user_vars.set_dir + "/Output/" + "period_mins.csv")
    df_maxes = parse_csv_file(user_vars.set_dir + "/Output/" + "period_maxes.csv")
    generate_appendix_figure(user_vars,df_means,df_mins,df_maxes)


def generate_ssr_plots(user_vars, data):
    """
    Description: Uses user data to generate SSR plots for Biannual period.
    Input: User varaibles, empty data object
    Output: HTML Plot files.
    """
    print("Generating SSR Plots...")
    get_beat_reports(user_vars, data)
    get_quartely_sum_stats(data)
    make_ssr_by_submod("A", user_vars, data.submod_dict_a,"Quarterly_SSR_A_by_SubMod")
    make_ssr_by_submod("B", user_vars, data.submod_dict_b,"Quarterly_SSR_B_by_SubMod")
    make_ssr_by_doy("A", user_vars, data.doy_dict_a,"Quarterly_SSR_A_by_DoY")
    make_ssr_by_doy("B", user_vars, data.doy_dict_b,"Quarterly_SSR_B_by_DoY")
    make_ssr_full("A", user_vars, data, "Quarterly_SSR_A_Timestrip")
    make_ssr_full("B", user_vars, data, "Quarterly_SSR_B_Timestrip")


def generate_ska_plots(user_vars, data):
    """
    Description: Generates ska data based plots and csv files.
    Input: User Variables, empty data class
    Output: png and csv files.
    """
    print("Generating SKA Data Plots...")
    fetch_ska_data(user_vars, data)
    generate_report_tables(user_vars)
    generate_full_mission_tables(user_vars)
    generate_mission_appendix_plots(user_vars)
    generate_period_appendix_plots(user_vars)


def generate_pa_bpt_plots(user_vars):
    "Generate Power Amp versus Baseplate temp plot."

    print("Generating PA vs. BPT Plot...")

    # df_mins = parse_csv_file(user_vars.set_dir + "///Output/" + "period_mins.csv")
    df_means = parse_csv_file(user_vars.set_dir + "/Output/" + "period_means.csv")
    # df_maxes = parse_csv_file(user_vars.set_dir + "///Output/" + "period_maxes.csv")
    # days = df_means['Mission Day']

    txapwr = df_means.loc[:,'CTXAPWR']
    txbpwr = df_means.loc[:,'CTXBPWR']

    cpa1bpt = df_means.loc[:,'CPA1BPT']
    cpa2bpt = df_means.loc[:,'CPA2BPT']

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=cpa1bpt, y=txapwr, name="TX-A Power vs. PA Baseplate Temp",
            mode="markers",marker={"size":12},line={"color":"blue", "width":3}
            )
        )
    figure.add_trace(
        go.Scatter(
            x=cpa2bpt, y=txbpwr, name="TX-B Power vs. PA Baseplate Temp",
            mode="markers",marker={"size":12},line={"color":"orange", "width":3}
            )
        )

    figure.update_layout(
            title="Daily Mean Tx Output Power vs. Daily Mean Base Plate Temperature",
            xaxis_title="Baseplate Temperature (degF)",
            yaxis_title="Tx Output Power (dBm)",
            autosize=True,
            legend={
                "yanchor":"top",
                "y":0.99,
                "xanchor":"left",
                "x":0.01
                },
            font={
                "family":"Courier New, monospace",
                "size":18,
                "color":"RebeccaPurple"
                }
            )
    write_html_file(user_vars,figure,f"{user_vars.end_year}b_TX_BPT.html")


def main():
    "Main execution"
    user_vars = UserVariables()
    ssr_data = Data()
    ska_data = Data()
    display_user_instructions(user_vars)
    generate_ska_plots(user_vars, ska_data)
    generate_ssr_plots(user_vars, ssr_data)
    generate_pa_bpt_plots(user_vars)
    if user_vars.prime_ssr == "A":
        build_sbe_mod104_avg_plot(user_vars)
    build_sbe_vs_dbe_solar_date_plot(user_vars)
    build_sbe_vs_dbe_submod_plot(user_vars)
    build_query_data_file(user_vars)


main()
