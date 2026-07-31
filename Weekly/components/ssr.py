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
from components.data_requests import ska_data_request as ska_data


@dataclass
class SSRData:
    "Empty Data Class for data"
    ssra_good: int = 0
    ssra_bad:  int = 0
    ssrb_good: int = 0
    ssrb_bad:  int = 0


@dataclass
class SSRRolloverData:
    "dataclass for an SSR Rollover event"
    rollover_type: Optional[str]
    time: Optional[str]


@dataclass(frozen=True)
class BEATData:
    "Dataclass for BEAT Data"
    ssr: str
    submodule: int
    dbe_count: int
    ts: CxoTime
    tp: CxoTime


def get_ssr_data(user_vars):
    "returns SSRStats Object"
    print("\nFetching SSR Data...")

    url = ("https://occweb.cfa.harvard.edu/occweb/web/webapps/ifot/ifot.php?r=home&t="
           "qserver&format=list&columns=linenum&e=PLAYBACK_BCW.ssr.playback_status."
           f"ts_ssr_start_pb.status_comment&tstart={user_vars.ts}&tstop={user_vars.tp}&ul=12")

    with urllib.request.urlopen(url) as response:
        raw_data = pd.read_html(response.read())

    df = raw_data[0]

    ssr_col = df.iloc[1:, 1]
    status_col = df.iloc[1:, 2]

    return SSRData(
        ssra_good = ((ssr_col == "A") & (status_col == "OK")).sum(),
        ssra_bad  = ((ssr_col == "A") & (status_col == "FAILED")).sum(),
        ssrb_good = ((ssr_col == "B") & (status_col == "OK")).sum(),
        ssrb_bad  = ((ssr_col == "B") & (status_col == "FAILED")).sum()
    )


def parse_beat_report(beat_dir, user_vars):
    """
    Description: Parse a BEAT file
    Input: BEAT file directory path
    Output: List of BEATData objects
    """
    data_list = []

    with open(beat_dir, 'r', encoding="utf-8") as file:
        current_ssr = None

        for line in file:
            if line.startswith("SSR ="):
                current_ssr = line[6]

            elif line and line[0].isdigit():
                split_line = line.split()
                ts = CxoTime(split_line[4])

                if ts <= user_vars.tp:
                    data_point = BEATData(
                        ssr=current_ssr,
                        submodule=int(split_line[0]),
                        dbe_count=int(split_line[3]),
                        ts=ts,
                        tp=CxoTime(split_line[5])
                    )
                    data_list.append(data_point)

    return data_list


def get_beat_report_dirs(user_vars):
    "Return a list of <str> of BEAT files to parse."
    base_path = "/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/SSR_Short_Reports/"
    return_list = []

    # Get all files in Start Year
    dir_path = Path(f"{base_path}/{user_vars.ts.datetime.year}")
    all_beat_dirs = list(x for x in dir_path.rglob('BEAT*.*'))

    # Get all files in End year if Start/End are different.
    if user_vars.ts.datetime.year != user_vars.tp.datetime.year:
        dir_path = Path(f"{base_path}/{user_vars.tp.datetime.year}")
        all_beat_dirs += list(x for x in dir_path.rglob('BEAT*.*'))

    # Convert all entries to strings
    all_beat_dirs = list(str(x) for x in all_beat_dirs)

    # Return date range if start/stop years don't match.
    if user_vars.ts.datetime.year != user_vars.tp.datetime.year:
        for day in range((user_vars.tp.datetime - user_vars.ts.datetime).days + 1):
            cur_day = user_vars.ts + timedelta(days=day)
            return_list += (
                [s for s in all_beat_dirs if f"BEAT-{cur_day.yday[0:4]}{cur_day.yday[5:8]}" in s])
    # Return from DoY 1 thru end date.
    else:
        for day in range(0, int(user_vars.tp.datetime.strftime("%j")) + 1):
            cur_day = (
                CxoTime(f"{user_vars.ts.datetime.year}:001:00:00:00") + timedelta(days=day))
            return_list += (
                [s for s in all_beat_dirs if f"BEAT-{cur_day.yday[0:4]}{cur_day.yday[5:8]}" in s])

    return return_list


def get_ssr_beat_report_data(user_vars):
    "Parse SSR beat reports into data"
    print("Generating SSR beat report data...")

    beat_report_dirs = get_beat_report_dirs(user_vars)
    all_beat_report_data = set()

    for beat_dir in beat_report_dirs:
        data_points = parse_beat_report(beat_dir, user_vars)
        all_beat_report_data.update(data_points)

    return list(all_beat_report_data)


def get_wk_list(user_vars, all_beat_report_data):
    "Generate the number of submodules that had DBEs in date range."
    wk_list = []
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

    ssr_swap_check = user_vars.ts <= CxoTime(user_vars.ssr_prime[1]) <= user_vars.tp
    ssr_rollovers = []

    if not ssr_swap_check: # Skip if SSR swap occurred inside of date range
        ssr_data = ska_data(user_vars.ts, user_vars.tp, f"COS{user_vars.ssr_prime[0]}RCEN")
        previous_value = None

        # Shorten data list to only when SSR Prime was not recording
        for time, value in zip(ssr_data.times, ssr_data.vals):

            # Detect rollover from prime to backup
            if (previous_value == "TRUE" and value == "FALS"):
                ssr_rollovers.append(SSRRolloverData("Rollover", CxoTime(time).yday))

            # Detect rollover from backup to prime
            elif (previous_value == "FALS" and value == "TRUE"):
                ssr_rollovers.append(SSRRolloverData("Recovery", CxoTime(time).yday))

            previous_value = value

    else:
        ssr_rollovers.append(SSRRolloverData("Unavailable", None))

    return ssr_rollovers


def ssr_rollover_detection(user_vars):
    "ssr rollover detection"
    return_string = str()
    ssr_rollover_data = get_ssr_rollover_data(user_vars)

    # Build the return string with rollover info.
    prime = "A" if user_vars.ssr_prime[0] == "A" else "B"
    backup = "B" if prime == "A" else "A"

    if ssr_rollover_data:
        for data_point in ssr_rollover_data:

            # Assemble the final string
            if data_point.rollover_type == "Unavailable":
                return_string = (
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


# ==========================================
# PLOTTING FUNCTIONS & DATA PREP
# ==========================================

def prep_beat_dataframe(all_beat_report_data):
    """Converts the dataclass list into a DataFrame for optimized plotting."""
    df = pd.DataFrame(all_beat_report_data)
    df['doy'] = df['ts'].apply(lambda x: int(x.datetime.strftime('%j')))
    df['has_dbe'] = df['dbe_count'].apply(lambda x: 1 if x else 0)
    return df


def make_ssr_by_submod(ssr, user_vars, df, ftitle):
    """
    Description: Build SSR By Submodule plot using Pandas for aggregation
    """
    root = ("/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/"
            f"SSR_Weekly_Charts/{user_vars.ts.datetime.year}/")

    doy_tp_str = user_vars.tp.datetime.strftime('%j')
    fname = f"{root}SSR_{ssr}_{user_vars.ts.datetime.year}_{user_vars.ts.datetime.strftime('%j').zfill(3)}_{ftitle}"

    ssr_df = df[df['ssr'] == ssr]
    counts = ssr_df.groupby('submodule')['has_dbe'].sum()
    counts = counts.reindex(range(128), fill_value=0)

    y = counts.tolist()
    x = list(range(128))

    fig = make_subplots(rows=4, cols=1, x_title='SubModule #', y_title='# DBEs')

    fig.add_trace(go.Bar(x=x[0:32], y=y[0:32], width=0.9), row=1, col=1)
    fig.add_trace(go.Bar(x=x[32:64], y=y[32:64], width=0.9), row=2, col=1)
    fig.add_trace(go.Bar(x=x[64:96], y=y[64:96], width=0.9), row=3, col=1)
    fig.add_trace(go.Bar(x=x[96:128], y=y[96:128], width=0.9), row=4, col=1)

    fig.update_traces(marker_line_color="black", marker_line_width=1, opacity=0.6)

    fig.update_layout(
        title=f"{user_vars.ts.datetime.year} SSR-{ssr} Year-to-DOY {doy_tp_str} DBE by Submodule",
        autosize=False, width=1040, height=700, showlegend=False,
        font={"family": "Courier New, monospace", "size": 14, "color": "RebeccaPurple"},
        barmode="group", xaxis_tickangle=-90
    )
    fig.update_yaxes(range=[0, max(y) + 1])
    fig.write_html(f"{fname}.html", include_plotlyjs="directory", auto_open=False)


def make_ssr_by_doy(ssr, user_vars, df, ftitle):
    "Generate Plot SSR by DoY using Pandas aggregation"
    root = ("/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/"
            f"SSR_Weekly_Charts/{user_vars.ts.datetime.year}/")
    fname = f"{root}SSR_{ssr}_{user_vars.ts.datetime.year}_{user_vars.ts.datetime.strftime('%j').zfill(3)}_{ftitle}"

    doy_tp = int(user_vars.tp.datetime.strftime("%j"))

    ssr_df = df[df['ssr'] == ssr]
    counts = ssr_df.groupby('doy')['has_dbe'].sum()
    counts = counts.reindex(range(1, doy_tp + 1), fill_value=0)

    y = counts.tolist()
    x = list(range(1, doy_tp + 1))

    fig = make_subplots(rows=1, cols=1, x_title='DOY #', y_title='# DBEs')
    fig.add_trace(go.Bar(x=x, y=y, width=.9), row=1, col=1)

    fig.update_traces(marker_line_color="black", marker_line_width=1, opacity=0.6)
    fig.update_layout(
        title=f"{user_vars.tp.datetime.year} SSR-{ssr} DBEs from Day-of-Year 1 - {doy_tp}",
        autosize=False, width=1040, height=700, showlegend=False,
        font={"family": "Courier New, monospace", "size": 14, "color": "RebeccaPurple"},
        barmode="group", xaxis_tickangle=-90
    )
    fig.update_yaxes(range=[0, max(y) + 1])
    fig.write_html(f"{fname}.html", include_plotlyjs="directory", auto_open=False)


def make_ssr_full(ssr, user_vars, df, ftitle, full=False):
    "Generate SSR Heatmap using Pandas Crosstab"
    root = ("/share/FOT/engineering/ccdm/Current_CCDM_Files/Weekly_Reports/"
            f"SSR_Weekly_Charts/{user_vars.ts.datetime.year}/")
    fname = f"{root}SSR_{ssr}_{user_vars.ts.datetime.year}_{user_vars.ts.datetime.strftime('%j').zfill(3)}_{ftitle}"

    doy_ts = int(user_vars.ts.datetime.strftime('%j'))
    doy_tp = int(user_vars.tp.datetime.strftime("%j"))
    doy_start = 1 if full else doy_ts

    ssr_df = df[df['ssr'] == ssr]

    if not full:
        ssr_df = ssr_df[(ssr_df['ts'] >= user_vars.ts) & (ssr_df['ts'] <= user_vars.tp)]

    matrix = pd.crosstab(ssr_df['doy'], ssr_df['submodule'])
    matrix = matrix.reindex(index=range(doy_start, doy_tp + 1), columns=range(128), fill_value=0)

    im = matrix.values.tolist()

    fig = go.Figure(data=go.Heatmap(
        z=im,
        x=list(range(doy_start, doy_tp + 1)),
        y=list(range(128)),
        transpose=True,
        colorscale='Gray'
    ))

    fig.update_xaxes(title_text='Day-of-Year')
    fig.update_yaxes(title_text='Submodule #')
    fig.update_layout(
        title=f"{user_vars.ts.datetime.year} SSR-{ssr} DBEs from Day-of-Year {doy_start} - {doy_tp}",
        autosize=False, width=1040, height=700, showlegend=False,
        font={"family": "Courier New, monospace", "size": 14, "color": "RebeccaPurple"}
    )
    fig.write_html(f"{fname}.html", include_plotlyjs='directory', auto_open=False)
