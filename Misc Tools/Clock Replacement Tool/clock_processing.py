import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
from misc import (get_constants, load_calib_database, load_dsn_database, parse_erp_file,
                  parse_nrt_file, log_callback, get_cumulative_leap_seconds)
from math_functions import (get_ground_station_position, polyfit_quadratic,
                            polyfit_cubic, ephemeris_interpolator)


# Constants
constants=   get_constants()
C_KM_S=      constants['C_KM_S']
INIT_CLOCK = constants['INIT_CLOCK']
JD_1958=     constants['JD_1958']


def calculate_clock_drift(erp_path, nrt_paths):
    log_callback("--- Starting Pure Cubic Clock Correlation ---")

    # 1. Parse Ephemeris
    erp_df = parse_erp_file(erp_path)
    erp_times = erp_df['abs_time'].values
    erp_positions = erp_df[['pos-x', 'pos-y', 'pos-z']].values
    erp_velocities = erp_df[['vel-x', 'vel-y', 'vel-z']].values

    # 2. Parse Telemetry & Dynamically Apply Format-Dependent Hardware Delays
    calib_db = load_calib_database(Path(__file__).parent.resolve() / "calibration_data.json")
    dsn_db = load_dsn_database(Path(__file__).parent.resolve() / "dsn_data.json")
    nrt_dataframes = []

    for path in nrt_paths:
        df = parse_nrt_file(path)

        # Extract the telemetry rate/format ID from the filename (e.g., 'rclk_26_138_10_6' -> '6')
        file_rate_id = Path(path).stem.split('_')[-1]

        # Safely lookup the delays matching OFLS Spec nomenclatures
        df['internal_delay']= calib_db.get(file_rate_id, {}).get("internal_delay", 0.0)
        df['sync_delay']= calib_db.get(file_rate_id, {}).get("sync_delay", 0.0)

        # Assign the total calibration delay directly to this file's chunk of data
        nrt_dataframes.append(df)

    # 3. Concatenate and Sort Telemetry
    nrt_df = pd.concat(nrt_dataframes, ignore_index=True)
    nrt_df['abs_time'] = (nrt_df['num_days'] * 86400.0) + (nrt_df['num_ms'] / 1000.0) + (nrt_df['num_us_frac'] / 1000000.0)
    nrt_df = nrt_df.sort_values(by='abs_time').reset_index(drop=True)

    ert_times = nrt_df['abs_time'].values
    ert_datetimes = pd.to_datetime(nrt_df['datetime']).dt.to_pydatetime().tolist()
    dss_codes = nrt_df['dss_id'].values if 'dss_id' in nrt_df.columns else np.full(len(nrt_df), 34)

    # Int64 Overflow s/ VCDU Rollover Protection
    vcdus= nrt_df['vcdu'].values.astype(np.float64).copy() 

    for idx in np.where(np.diff(vcdus) < -1000000)[0]:
        vcdus[idx+1:] += 2**24
    
    # 4. Legacy Orbital Kinematics (Positions & Distances)
    # Vectorized Light-Time Calculation and Smart Pass Batching for Localized FDF Fits
    leap_offsets = np.array([get_cumulative_leap_seconds(dt) for dt in ert_datetimes])
    leap_corrections= leap_offsets - leap_offsets[0]

    # Apply leap second corrections to the ephemeris times
    sc_pos_func = ephemeris_interpolator(ert_times, erp_times, erp_positions, erp_velocities)
    gs_positions, dsn_delay = get_ground_station_position(ert_times, dss_codes, dsn_db)

    # Light-Time Calculation (Vectorized)
    distances = np.linalg.norm(sc_pos_func - gs_positions, axis=1)
    light_time = distances / C_KM_S
    nrt_df['light_time']= light_time

    # Smart Pass Batching (Groups by continuous passes > 1hr gaps)
    time_gaps= np.diff(ert_times, prepend=ert_times[0])
    nrt_df['pass_id']= pd.to_datetime(nrt_df['datetime']).dt.dayofyear

    # ---------------------------------------------------------
    # PIPELINE 1: DAY-TO-DAY FDF SUPPORT (3rd-Degree Fit)
    # ---------------------------------------------------------
    for pass_id, group in nrt_df.groupby('pass_id'):
        idx= group.index # Index range for this pass

        pass_ert_times = ert_times[idx]   # ert times for this pass
        pass_vcdus = vcdus[idx]           # Corrected VCDU counts for this pass
        pass_leap = leap_corrections[idx] # Leap second corrections for this pass (only used if leap seconds occur within the pass)
        pass_dsn_delay = dsn_delay[idx]   # Delay per DSN station for this pass
        pass_light_time = light_time[idx] # Light time for this pass
        pass_internal_delay= nrt_df.loc[idx, 'internal_delay'].values # Calibration delay values for this pass
        pass_sync_delay= nrt_df.loc[idx, 'sync_delay'].values # Sync delay values for this pass

        # Adjusted Propagation Time and Ground Time
        nrt_df.loc[idx, 'adjusted_propogation_time']= pass_light_time + pass_dsn_delay + pass_internal_delay - pass_sync_delay
        nrt_df.loc[idx, 'adjusted_ground_time']= pass_ert_times - nrt_df.loc[idx, 'adjusted_propogation_time']

        # Delta Clock Counts & Scaling (X)
        pass_delta_vcdu = pass_vcdus - pass_vcdus[0]
        scaled_vcdu = pass_delta_vcdu * 1e-6

        # Absolute Spacecraft Time (Y)
        pass_tsc= nrt_df.loc[idx, 'adjusted_ground_time'].values

        # 3. Weights (w)
        pass_weights= np.ones(len(pass_tsc))

        cubic_coeffs, s2, std_devs = polyfit_cubic(scaled_vcdu, pass_tsc, pass_weights)
        # cubic_coeffs, _ = np.polyfit(scaled_vcdu, pass_tsc, 3, cov= True)

        # Un-scale the coefficients strictly aligned with c1, c2, c3, c4
        true_c1= cubic_coeffs[0]         # Absolute Initial Time
        true_c2= cubic_coeffs[1] * 1e-6  # Absolute Rate
        true_c3= cubic_coeffs[2] * 1e-12 # Absolute Drift
        true_c4= cubic_coeffs[3] * 1e-18 # Derivative of Drift (3rd derivative of time w.r.t. VCDU)

        # Apply kinematic multipliers for physics outputs
        nrt_df.loc[idx, "pass_init_time"]=       true_c1
        nrt_df.loc[idx, 'pass_cubic_rate']=      true_c2
        nrt_df.loc[idx, 'pass_cubic_drift']=     true_c3 * 2.0
        nrt_df.loc[idx, 'pass_cubic_der_drift']= true_c4 * 6.0

        # Calculate Residuals against the local curve
        pass_predicted_time= (true_c1 + (true_c2 * pass_delta_vcdu) +
                             ((true_c3 / 2) * pass_delta_vcdu**2) +
                             ((true_c4 / 6) * pass_delta_vcdu**3))
        pass_residuals_sec = pass_tsc - pass_predicted_time
        nrt_df.loc[idx, 'resid_musec'] = pass_residuals_sec * 1e6

        # ODB Statistical Confidence Tags
        nrt_df.loc[idx, 'pass_resid_variance']= s2
        nrt_df.loc[idx, 'pass_std_dev_rate']=   std_devs[2]

    # ---------------------------------------------------------
    # PIPELINE 2: WEEKLY TRENDING (Global 2nd-Degree Fit)
    # ---------------------------------------------------------
    # 1. Delta Clock Counts (X)
    global_delta_vcdu = vcdus - vcdus[0]
    global_scaled_vcdu = global_delta_vcdu * 1e-6

    # 2. Absolute Spacecraft Time (Y)
    global_tsc = nrt_df['adjusted_ground_time'].values

    # 3. Weights (W)
    global_weights = np.ones(len(global_tsc))

    # Run the absolute QUADRATIC matrix on the ENTIRE dataset
    global_quad_coeffs, global_s2, global_std_devs = polyfit_quadratic(global_scaled_vcdu, global_tsc, global_weights)

    # Un-scale the Global Coefficients strictly aligned with c1, c2, c3
    global_c1 = global_quad_coeffs[0]               # Absolute Initial Time
    global_c2 = global_quad_coeffs[1] * 1e-6        # Absolute Rate (No INIT_CLOCK needed)
    global_c3 = global_quad_coeffs[2] * 1e-12       # Absolute Drift

    # Apply the Kinematic Multipliers (Factor of 2 for quadratic drift)
    nrt_df['global_init_time']=  global_c1
    nrt_df['global_rate_quad']=  global_c2
    nrt_df['global_drift_quad']= global_c3 * 2.0

    # Save the global uncertainty tags
    nrt_df['global_variance']=     global_s2
    nrt_df['global_std_dev_rate']= global_std_devs[1]

    # Outputs for Terminal Logging
    ref_time= nrt_df['datetime'].iloc[0].strftime('%Y:%j:%H:%M:%S.%f') # first time stamp
    ref_count= nrt_df['vcdu'].iloc[0] # First VCDU count
    current_clock_rate= global_c2
    current_clock_drift= global_c3 * 2.0
    span_days= (nrt_df['datetime'].iloc[-1] - nrt_df['datetime'].iloc[0]).total_seconds() / 86400.0

    # Log the successfully scaled Global ODB output to the terminal
    print(
        f"{'RefTime (UTC)':<24} | {'RefCounts':<10} | {'Rate (Sec/Cnt)':<16} | "
        f"{'Drift (Sec/Cnt^2)':<17} | {'Span (Days)':<12}\n"
        f"{ref_time:<24} | {ref_count:<10.0f} | {current_clock_rate:<16.12f} | "
        f"{current_clock_drift:<17.3e} | {f'{span_days:.2f} Days':<12}")

    return nrt_df


def generate_trending_report(nrt_df, output_filepath):
    """TOOL 1 REPLICA: Absolute Quadratic Trending Math with Weighted Matrix Conditioning"""
    NOMINAL_RATE = 0.25625 
    EPOCH_SHIFT_1985 = 852076800.0
    epoch_1958 = datetime(1958, 1, 1)
    pass_history, trend_lines = [[] for i in range(2)]
    file_exists = os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0

    # Int64 Overflow s/ VCDU Rollover Protection
    vcdus= nrt_df['vcdu'].values.astype(np.float64).copy() 

    for idx in np.where(np.diff(vcdus) < -1000000)[0]:
        vcdus[idx+1:] += 16777216

    if file_exists:
        first_pass = False
        try:
            with open(output_filepath, 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    last_data = lines[-1].strip().split()
                    pass_history.append((int(last_data[1]), float(last_data[2])))
        except PermissionError:
            log_callback("WARNING: clock_rate.txt is locked by another program!")
    else:
        first_pass = True
        trend_lines.append(
            f"{'RefTime_Day':<28}{'VCDU_Ref':<12}{'RefTime_Sec':<21}{'Clock_Rate(sec/cnt)':<23}"
            f"{'Drift(sec/cnt^2)':<27}{'DOY_Decimal':<22}{'Datetime':<30}{'1_Day_Rate':<26}"
            f"{'30_Min_Rate':<26}{'1_Day_Rate_Sq':<26}\n"
        )

    for day_id, group in nrt_df.groupby('pass_id'):
        pass_vcdu = group['vcdu'].values

        # Pull the absolute time calculated in Pipeline 1
        pass_tsc = group['adjusted_ground_time'].values

        # Origin = First Packet
        delta_vcdu = pass_vcdu - pass_vcdu[0]
        scaled_vcdu = delta_vcdu * 1e-6
        pass_weights = np.ones(len(pass_tsc))

        # Absolute Matrix Conditoning & Fit
        quad_coeffs, _, _ = polyfit_cubic(scaled_vcdu, pass_tsc, pass_weights)

        # Un-scale the Absolute Coefficients
        trend_rate = quad_coeffs[1] * 1e-6
        trend_drift = (quad_coeffs[2] * 1e-12) * 2.0
        thirty_min_rate = trend_rate - NOMINAL_RATE

        # Major Frame Anchor
        major_frames = pass_vcdu[pass_vcdu % 128 == 0]
        vcdu_ref = int(major_frames[0]) if len(major_frames) > 0 else int(pass_vcdu[0] + (128 - (pass_vcdu[0] % 128)))

        delta_to_ref = vcdu_ref - pass_vcdu[0]
        scaled_ref = delta_to_ref * 1e-6

        # Evaluate the absolute polynomial directly at the major frame to get atomic seconds
        ref_final_1958 = quad_coeffs[0] + (quad_coeffs[1] * scaled_ref) + (quad_coeffs[2] * (scaled_ref ** 2))
        ref_time_sec = ref_final_1958 - EPOCH_SHIFT_1985

        dt_final = epoch_1958 + pd.to_timedelta(ref_final_1958, unit='s')
        hosc_final = dt_final.strftime('%Y:%j:%H:%M:%S.%f')

        # Pass History Bridge
        if pass_history:
            target_pass = pass_history[-1] 
            for hist_vcdu, hist_sec in reversed(pass_history):
                time_gap = ref_time_sec - hist_sec
                if 64800 < time_gap < 108000: 
                    target_pass = (hist_vcdu, hist_sec)
                    break

            delta_sec_1day = ref_time_sec - target_pass[1]
            delta_vcdu_1day = vcdu_ref - target_pass[0]
            if delta_vcdu_1day < -8000000: delta_vcdu_1day += 16777216

            one_day_rate = (delta_sec_1day / delta_vcdu_1day) - NOMINAL_RATE
            one_day_rate_sq = one_day_rate ** 2
        else:
            one_day_rate = 0.0
            one_day_rate_sq = 0.0

        pass_history.append((vcdu_ref, ref_time_sec))

        doy_decimal = dt_final.timetuple().tm_yday + (dt_final.hour / 24.0) + (dt_final.minute / 1440.0) + ((dt_final.second + dt_final.microsecond / 1e6) / 86400.0)
        dt_str = dt_final.strftime('%Y-%m-%d %H:%M:%S.%f')
        one_day_str = "NaN" if first_pass else f"{one_day_rate:.16e}"
        one_day_sq_str = "NaN" if first_pass else f"{one_day_rate_sq:.16e}"
        first_pass = False

        trend_lines.append(
            f"{hosc_final:<28}{vcdu_ref:<12}{ref_time_sec:<21.5f}{trend_rate:<23.14f}"
            f"{trend_drift:<27.6e}{doy_decimal:<22.6f}{dt_str:<30}{one_day_str:<26}"
            f"{thirty_min_rate:<26.16e}{one_day_sq_str:<26}\n"
        )

    try:
        with open(output_filepath, 'a') as f:
            f.writelines(trend_lines)
    except PermissionError:
        log_callback("ERROR: Could not write to clock_rate.txt. Is it open in another program?")


def generate_residual_plot(results_df, output_filepath):

    """
    Generates an interactive Plotly graph matching the classic MATLAB figure aesthetic.
    """
    resid_musec= results_df['resid_musec'].values
    vcdu= results_df['vcdu'].values

    # MATLAB Statistics
    rms_val= np.sqrt(np.mean(resid_musec**2))
    max_val, min_val= np.max(resid_musec), np.min(resid_musec)
    max_abs_resid= max(abs(max_val), abs(min_val))

    dif= np.diff(vcdu)
    dif= dif[dif < 3000]
    avg_skip= round(np.mean(dif)) - 1 if len(dif) > 0 else 0

    # Dynamic Titles
    start_dt, end_dt= results_df['datetime'].iloc[0], results_df['datetime'].iloc[-1]
    year, day1, day2= start_dt.strftime('%Y'), start_dt.strftime('%j'), end_dt.strftime('%j')

    title_line1= f"Chandra Clock Correlation Residuals for {year}:{day1} to {year}:{day2}"
    title_line2= f"RMS = {rms_val:.2f} μsec, max = {max_abs_resid:.2f} μsec"

    plot_min_y, plot_max_y= min(-10, np.floor(min_val)), max(10, np.ceil(max_val))
    frames= np.arange(1, len(resid_musec) + 1)

    fig= go.Figure()

    fig.add_trace(go.Scatter(
        x= frames,
        y= resid_musec,
        mode= 'markers',
        name= 'Raw Residuals',
        marker= dict(color='#0000FF', size=4)
    ))

    fig.update_layout(
        title= {
            'text': f"<b>{title_line1}</b><br><span style='font-size: 14px;'>{title_line2}</span>",
            'x': 0.5, 
            'xanchor': 'center', 
            'font': dict(family="Arial, sans-serif", color="black")
        },
        xaxis_title= 'Telemetry Frame Number (VCDU)',
        yaxis_title= 'Timing Error (μsec)',
        plot_bgcolor= 'white',
        paper_bgcolor= '#f0f0f0',
        showlegend= False,
        margin= dict(l= 60, r= 40, t= 80, b= 60)
    )

    fig.update_xaxes(
        range=[0, len(frames)], showgrid=False, zeroline=False,
        showline=True, linewidth=1.5, linecolor='black', mirror=True,
        ticks='inside', tickwidth=1.5, tickcolor='black', ticklen=6
    )

    fig.update_yaxes(
        range=[plot_min_y, plot_max_y], showgrid=False, zeroline=False,
        showline=True, linewidth=1.5, linecolor='black', mirror=True,
        ticks='inside', tickwidth=1.5, tickcolor='black', ticklen=6
    )

    fig.write_html(output_filepath)
