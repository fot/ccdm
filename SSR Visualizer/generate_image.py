"Tool to display SSR Pointers"
from datetime import datetime, timedelta, timezone
import traceback
import json
import urllib.request
import warnings
import numpy as np
import plotly.graph_objects as go
import tkinter as tk
warnings.filterwarnings("ignore")


def get_screen_scaling():
    root = tk.Tk()
    pixels_per_inch = root.winfo_fpixels('1i')  # '1i' = 1 inch
    root.destroy()
    scaling_factor = pixels_per_inch / 96  # 96 is the baseline DPI
    return scaling_factor


def data_request(ts, tp, msid, skip= False):
    """
    Description: Data request for a general timeframe and MSID, returns json or data dict
    Input: User Variables, MSID
    Output: Data dict or JSON
    """
    if not skip:
        print(f"    - Requesting data for MSID: {msid}...")
    url= (f"https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m="
          f"{msid}&ts={ts.strftime('%Y%j.%H%M%S')}&tp={tp.strftime('%Y%j.%H%M%S')}")
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())


def get_pointers(self):
    """
    Retrieves the playback and record pointers for a specified SSR (Solid State Recorder)
    within a given date range.
    Args:
        start_date (str): The start date for the data query.
        end_date (str): The end date for the data query.
        ssr (str): The identifier for the SSR.
    Returns:
        tuple: A tuple containing:
            - pb_pointers (list of int): List of playback pointer values (current and previous).
            - rc_pointer (int): The current record pointer value.
    Raises:
        KeyError: If expected keys are missing in the data response.
        IndexError: If pointer values are not found in the response.
        ValueError: If pointer values cannot be converted to integers.
    Note:
        Assumes the existence of a `data_request` function that fetches pointer data in a
        specific format. Get the record pointers for the selected SSR."""
    print("  - Getting Playback/Record Pointers...")
    pb_pointers= []

    # Find Current and Previous Playback Pointers
    pb_data= data_request(self.start_date, self.end_date, f"COS{self.selectedssr.upper()}PBPT")
    pb_data['data-fmt-1']['values'].reverse()
    pb_pointers.append(int(pb_data['data-fmt-1']['values'][0]))

    for i, (val) in enumerate(pb_data['data-fmt-1']['values']):
        try:
            next_val= pb_data['data-fmt-1']['values'][i+1]
            if next_val != val:
                pb_pointers.append(int(next_val))
                break
        except IndexError:
            pb_pointers.append(None)

    # Record the current Record Pointer Value
    rc_data= data_request(self.start_date, self.end_date, f"COS{self.selectedssr.upper()}RCPT")
    rc_pointer= int(rc_data['data-fmt-1']['values'][-1])

    self.pb_pointers= pb_pointers
    self.rc_pointer= rc_pointer


def generate_polar_plot(self):
    """
    Generates a custom polar plot visualizing record and playback pointers on a circular scale.
    The plot displays:
        - SSR pointer segments with value labels.
        - Record pointer as a blue line.
        - Current playback pointer as a solid red line.
        - Previous playback pointer as a dashed red line.
        - Highlighted area between record and current playback pointers.
        - Timestamp annotation.
    Args:
        ssr (int): Identifier for the SSR (Solid State Recorder).
        pb_pointers (list[int]): List of playback pointer values. The first element is the
                                 current pointer, the last is the previous pointer.
        rc_pointer (int): Record pointer value.
    Returns:
        plotly.graph_objs.Figure: A Plotly figure object representing the polar plot.
         - Generates a custom polar plot visualizing record and
           playback pointers on a circular scale.
    """
    def build_and_add_labels(plot):
        "Define labels, based off SSR min/max"
        labels, label_sum= [], ssr_min
        for i in range(0, 8):
            labels.append(f"{int(label_sum):,}")
            label_sum += ((ssr_max-ssr_min) / 8)
        labels[0]= f"{int(label_sum):,}<br>{labels[0]}"

        for i, label in enumerate(labels):
            plot.add_trace(go.Scatterpolar(
                r= [1.2], theta= [angles_deg[i]],
                mode= "text", text= [label],
                textfont= {"size":18, "color":"black"},
                hoverinfo= "skip", showlegend= False))
            plot.add_trace(go.Scatterpolar(
                r= [0, 1.3], theta= [angles_deg[i], angles_deg[i]],
                mode= "lines", line= {"color":"rgba(0,0,0,0.1)", "width":3, "dash":"dash"},
                hoverinfo= "skip", showlegend= False))

    def add_record_pointer(plot):
        "Add the record pointer"
        rc_angle= (self.rc_pointer / (ssr_max-ssr_min)) * 360
        plot.add_trace(go.Scatterpolar(
            r= [0, 1.2], theta= [rc_angle, rc_angle],
            name= f"Record Pointer: {self.rc_pointer:,}",
            mode= "lines", line= {"color": "blue", "width": 4},
            hoverinfo= "skip", showlegend= True))

    def add_current_playback_pointer(plot):
        "Add the current playback pointer"
        pb_angle= (self.pb_pointers[0] / (ssr_max-ssr_min)) * 360
        plot.add_trace(go.Scatterpolar(
            r= [0, 1.2], theta= [pb_angle, pb_angle],
            name= f"Current Playback Pointer: {self.pb_pointers[0]:,}",
            mode= "lines", line= {"color": "red", "width": 4},
            hoverinfo= "skip", showlegend= True))

    def add_previous_playback_pointer(plot):
        "Add the previous playback pointer"
        if self.pb_pointers[-1] is not None:
            prev_pb_angle= (self.pb_pointers[-1] / (ssr_max-ssr_min)) * 360
            plot.add_trace(go.Scatterpolar(
                r= [0, 1.2], theta= [prev_pb_angle, prev_pb_angle],
                name= f"Previous Playback Pointer: {self.pb_pointers[-1]:,}",
                mode= "lines", line= {"color":"red", "width":4, "dash":"dash"},
                hoverinfo= "skip", showlegend= True))

    def add_highlighted_region(plot):
        "Add the highlighted region between record/playback (current) pointer values"
        if not self.pb_pointers[0] == self.rc_pointer:

            theta0= (self.pb_pointers[0] / (ssr_max-ssr_min)) * 360 % 360
            theta1= (self.rc_pointer / (ssr_max-ssr_min)) * 360 % 360

            if theta1 <= theta0:
                theta1 += 360

            theta_fill= np.linspace(theta0, theta1, 200)
            r_fill= np.ones_like(theta_fill) * 1.2
            plot.add_trace(go.Scatterpolar(
                r= np.concatenate([[0], r_fill, [0]]),
                theta= np.concatenate([[theta_fill[0]], theta_fill, [theta_fill[-1]]]),
                mode= "lines", fill= "toself", fillcolor= "rgba(255,0,0,0.2)",
                line= {"color": "rgba(255,0,0,0)"},
                hoverinfo= "skip", showlegend= False))

    def add_datetime_annotations(plot):
        "Add query datetime annotation"
        plot.add_annotation(
            text= f"{datetime.now(timezone.utc).strftime('%m/%d/%Y %H:%M:%S')} UTC",
            xref= "paper", yref= "paper",
            x= 1.00, y= -0.10, showarrow= False,
            font= {"size":12, "color":"black"}, align= "right",
            borderpad= 4, bgcolor= "rgba(0,0,0,0)")

    def add_playback_active_annotation(plot):
        "Add annotation if an SSR playback is currently occuring"
        print(f"  - Checking if SSR-{self.selectedssr} has an active playback...")
        playback_active= data_request(self.start_date, self.end_date, f"COS{self.selectedssr}PBEN")

        if playback_active['data-fmt-1']['values'][-1] == "1":
            plot.add_annotation(
                text= "PLAYBACK ACTIVE", xref= "paper", yref= "paper",
                x= 1.00, y= 1.00, showarrow= False,
                font= {"size":14, "color":"black"}, align= "right",
                borderpad= 4, bordercolor= "black", bgcolor= "red")

    def format_plot(plot):
        "Finalize plot formatting"
        plot.update_layout(
            polar= {"angularaxis": {"rotation":90, "direction":"clockwise", "visible":False},
                    "radialaxis": {"visible":False, "range":[0, 1.3]}},
            showlegend= True, margin= {"l":40, "r":40, "t":25, "b":100},
            width= 750, height= 750, font= {"size":14, "color":"black"},
            paper_bgcolor= "white",
            legend= {"yanchor":"bottom", "y":-0.15, "xanchor":"left", "x":0.00,
                    "borderwidth":2, "bordercolor":"black"})

    ssr_max, ssr_min= 134217728, 0
    angles_deg= np.linspace(0, 360, 8, endpoint=False)
    plot= go.Figure()

    # Assemble the figure
    build_and_add_labels(plot)
    add_record_pointer(plot)
    add_current_playback_pointer(plot)
    add_previous_playback_pointer(plot)
    add_highlighted_region(plot)
    add_datetime_annotations(plot)
    add_playback_active_annotation(plot)
    format_plot(plot)
    print(f"  - Plot generated for SSR-{self.selectedssr}...\n")

    self.plot= plot


def generate_image(self):
    """
    Executes the main logic to generate a polar plot image for the selected
    SSR (Solid State Relay) if it is ON.
    - Determines the time window for data retrieval (from 1 day ago to 10 seconds ago).
    - Checks the power status of the selected SSR using `data_request`.
    - If the SSR is ON, retrieves pointer data and generates a polar plot.
    - Handles errors if SSR power data is unavailable.
    Returns:
        plot: The generated polar plot if SSR is ON, otherwise None.
    """
    self.start_date= datetime.now(timezone.utc) - timedelta(hours= 18.5)
    self.end_date=   datetime.now(timezone.utc) - timedelta(seconds=5)
    print(f"Checking if SSR-{self.selectedssr} is ON...")
    ssr_power= data_request(self.start_date, self.end_date, f"COSSR{self.selectedssr}X")

    # Only generate plot if SSR is ON
    try:
        if int(ssr_power['data-fmt-1']['values'][-1]) == 1:
            print(f"  - SSR-{self.selectedssr} is ON...")
            get_pointers(self)
            generate_polar_plot(self)
        else:
            self.plot= None

    except IndexError as error:
        print(f""" - (Error) "{error}": Unable to retrieve SSR-{self.selectedssr} power data.""")
        traceback.print_exc()
