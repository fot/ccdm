import numpy as np
import pandas as pd
from pathlib import Path
from astropy.time import Time
from astropy import units as u

# Local Imports
from misc import (
    get_constants, load_calib_database, log_callback, is_consecutive_check
)
from math_functions import (get_ground_station_position, ephemeris_interpolator,
                            two_pass_coefficient_solver, legacy_coefficient_solver)

# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------
constants = get_constants()
C_KM_S = constants['C_KM_S']
EPOCH_OFFSET_1958_TO_1985 = constants['EPOCH_OFFSET_1958_TO_1985']


# ---------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------
def calculate_clock_drift(erp_df, nrt_df, legacy_mode=True):
    """
    Main driver for applying delays and executing daily/weekly 
    trending routines against fully parsed DataFrames.
    """
    if legacy_mode:
        log_callback(f"--- Starting Clock Correlation (Legacy Mode: {legacy_mode}) ---")
    else:
        log_callback(f"--- Starting Clock Correlation ---")

    # Extract Ephemeris Arrays
    erp_times = erp_df['abs_time'].values
    erp_positions = erp_df[['pos-x', 'pos-y', 'pos-z']].values
    erp_velocities = erp_df[['vel-x', 'vel-y', 'vel-z']].values

    # Load Hardware Delay Calibration Matrix
    calib_db = load_calib_database(Path(__file__).parent.resolve() / "calibration_data.json")
    calib_df = pd.DataFrame.from_dict(calib_db, orient='index')
    calib_df.index.name = 'bit_rate_code'
    calib_df = calib_df.reset_index()

    # Dynamically Apply Format-Dependent Hardware Delays across the entire dataframe
    if 'bit_rate_code' in nrt_df.columns:
        nrt_df['bit_rate_code'] = nrt_df['bit_rate_code'].astype(str)
        nrt_df = nrt_df.merge(calib_df, on='bit_rate_code', how='left')
        nrt_df['internal_delay'] = nrt_df['internal_delay'].fillna(0.0)
        nrt_df['sync_delay'] = nrt_df['sync_delay'].fillna(0.0)
    else:
        # Fallback if processing generalized STO data lacking standard rate codes
        nrt_df['internal_delay'] = nrt_df.get('internal_delay', 0.0)
        nrt_df['sync_delay'] = nrt_df.get('sync_delay', 0.0)

    # Sort by datetime before processing rollovers.
    nrt_df = nrt_df.sort_values(by='datetime').reset_index(drop=True)
    log_callback(f"Telemetry data concatenated and sorted by datetime. Total records: {len(nrt_df)}")

    # Unwrap VCDU rollovers into new column
    nrt_df['corrected_vcdu'] = nrt_df['vcdu'].astype(np.float64)
    rollover_indices = np.where(np.diff(nrt_df['corrected_vcdu']) < -1000000)[0]

    for idx in rollover_indices:
        nrt_df.loc[idx + 1:, 'corrected_vcdu'] += 2**24

    nrt_df = nrt_df.sort_values(by='corrected_vcdu').reset_index(drop=True)

    # Calculate absolute continuous time
    raw_counter_sec = ((nrt_df['num_days'] * 86400.0) + (nrt_df['num_ms'] / 1000.0) + (nrt_df['num_us_frac'] / 1000000.0)).values

    epoch_1958 = Time('1958-01-01 00:00:00', scale='tai')
    astropy_times = epoch_1958 + raw_counter_sec * u.s

    epoch_1985 = Time('1985-01-01 00:00:00', scale='tai')
    abs_times = (astropy_times - epoch_1985).sec

    nrt_df['astropy_time'] = astropy_times
    nrt_df['abs_time'] = abs_times

    ert_times = nrt_df['abs_time'].values
    dss_codes = nrt_df['dss_id'].values if 'dss_id' in nrt_df.columns else np.full(len(nrt_df), 34)

    # Calculate dynamic header offsets for legacy mode alignment
    epoch_1985_dt = pd.to_datetime("1985-01-01 00:00:00")
    header_abs_time = (nrt_df['datetime'] - epoch_1985_dt).dt.total_seconds().values
    time_offsets = header_abs_time - ert_times if legacy_mode else np.zeros(len(nrt_df))

    sc_pos_func, sc_vel_func = ephemeris_interpolator(ert_times, erp_times, erp_positions, erp_velocities, legacy_mode)
    nrt_df['sc_pos_x'] = sc_pos_func[:, 0]
    nrt_df['sc_pos_y'] = sc_pos_func[:, 1]
    nrt_df['sc_pos_z'] = sc_pos_func[:, 2]
    nrt_df['sc_vel_x'] = sc_vel_func[:, 0]
    nrt_df['sc_vel_y'] = sc_vel_func[:, 1]
    nrt_df['sc_vel_z'] = sc_vel_func[:, 2]

    gs_positions, dsn_delay = get_ground_station_position(ert_times, dss_codes, time_offsets, legacy_mode)
    nrt_df['gs_pos_x'] = gs_positions[:, 0]
    nrt_df['gs_pos_y'] = gs_positions[:, 1]
    nrt_df['gs_pos_z'] = gs_positions[:, 2]
    nrt_df['dsn_delay'] = dsn_delay

    # Section 4.4.3.1.2 Compute Adjustment to Ground Receive Time for Propagation Delays
    light_time = np.sqrt((nrt_df['sc_pos_x'] - nrt_df['gs_pos_x']) ** 2 +
                         (nrt_df['sc_pos_y'] - nrt_df['gs_pos_y']) ** 2 +
                         (nrt_df['sc_pos_z'] - nrt_df['gs_pos_z']) ** 2
                         ) / C_KM_S
    nrt_df['light_time'] = light_time

    # Smart Pass Batching
    time_gaps = np.diff(ert_times, prepend=ert_times[0])
    nrt_df['pass_id'] = (time_gaps > 3600).cumsum()

    is_consecutive_check(nrt_df)

    # 5. Execute Trending Pipelines
    daily_trending(nrt_df, legacy_mode)
    weekly_trending(nrt_df, legacy_mode)

    return nrt_df


# ---------------------------------------------------------
# PIPELINE 1: DAILY TRENDING
# ---------------------------------------------------------
def daily_trending(nrt_df, legacy_mode=False):
    """
    Daily Trending using a local 2nd-degree fit plus a
    3rd degree fit for higher-order drift analysis.
    Implements a 1-to-1 matching 2-pass 3-sigma outlier rejection.
    """

    for pass_id, group in nrt_df.groupby('pass_id'):
        scale = 1e-6
        idx = group.index  # Index range for this pass
        pass_ert_times =      nrt_df.loc[idx, 'abs_time'].values
        pass_vcdus =          nrt_df.loc[idx, 'corrected_vcdu'].values
        pass_dsn_delay =      nrt_df.loc[idx, 'dsn_delay'].values
        pass_light_time =     nrt_df.loc[idx, 'light_time']
        pass_internal_delay = nrt_df.loc[idx, 'internal_delay'].values
        pass_sync_delay =     nrt_df.loc[idx, 'sync_delay'].values

        # Adjusted Propagation Time and Ground Time
        nrt_df.loc[idx, 'adjusted_propogation_time'] = (pass_light_time + pass_dsn_delay + pass_internal_delay - pass_sync_delay)
        nrt_df.loc[idx, 'adjusted_ground_time'] = (pass_ert_times - nrt_df.loc[idx, 'adjusted_propogation_time'])

        # Local ground time (Absolute Spacecraft Time, Y)
        pass_tsc = nrt_df.loc[idx, 'adjusted_ground_time'].values

        # --- ZERO-BASING & SCALING ---
        pass_delta_vcdu = pass_vcdus - pass_vcdus[0]
        pass_delta_tcs = pass_tsc - pass_tsc[0]

        # if legacy_mode:
        #     results = legacy_coefficient_solver(pass_delta_vcdu, pass_delta_tcs, scale=scale)
        # else:
        #     results = two_pass_coefficient_solver(pass_delta_vcdu, pass_delta_tcs, scale=scale)
        results = legacy_coefficient_solver(pass_delta_vcdu, pass_delta_tcs, scale=scale)

        c1 = results["coeffs"]["T0"] + pass_tsc[0]
        c2 = results["coeffs"]["R0"]
        c3 = results["coeffs"]["D0"]
        s2 = results["s2"]
        std_devs = results["std_devs"]

        predicted_time = (c1 + (c2 * pass_delta_vcdu) + (c3 * pass_delta_vcdu**2))
        residuals_sec = pass_tsc - predicted_time

        nrt_df.loc[idx, "init_time"] =      c1
        nrt_df.loc[idx, 'rate'] =           c2
        nrt_df.loc[idx, 'drift'] =          c3
        nrt_df.loc[idx, 'resid_usec'] =     residuals_sec / (1e-6 * 1e2) # in usec
        nrt_df.loc[idx, 'resid_variance'] = s2

        # 2nd order standard deviations for this pass
        nrt_df.loc[idx, 'std_dev_utc0'] =  std_devs[0]
        nrt_df.loc[idx, 'std_dev_rate'] =  std_devs[1]
        nrt_df.loc[idx, 'std_dev_drift'] = std_devs[2]


# ---------------------------------------------------------
# PIPELINE 2: WEEKLY TRENDING
# ---------------------------------------------------------
def weekly_trending(nrt_df, legacy_mode=False):
    """
    Weekly Trending using a Global Fit on the Entire Dataset.
    Implements a 1-to-1 matching 2-pass 3-sigma outlier rejection on global scope.
    """
    scale = 1e-6
    corrected_vcdus = nrt_df['corrected_vcdu'].values

    # Delta Clock Counts (X)
    global_delta_vcdu = corrected_vcdus - corrected_vcdus[0]

    # Absolute Spacecraft Time (Y)
    global_tsc = nrt_df['adjusted_ground_time'].values
    global_delta_tsc = global_tsc - global_tsc[0]

    # --- QUADRATIC FIT (2nd Order) ---
    # if legacy_mode:
    #     results = legacy_coefficient_solver(global_delta_vcdu, global_delta_tsc, scale=scale)
    # else:
    #     results = two_pass_coefficient_solver(global_delta_vcdu, global_delta_tsc, scale=scale)
    results = legacy_coefficient_solver(global_delta_vcdu, global_delta_tsc, scale=scale)

    global_c1 = results["coeffs"]["T0"]
    global_c2 = results["coeffs"]["R0"]
    global_c3 = results["coeffs"]["D0"]
    global_s2 = results["s2"]
    global_std_devs = results["std_devs"]

    # Reconstruct predicted time using the transformation equation (OFLS 4.4.3.2)
    global_predicted_time = (global_c1 + global_tsc[0] + (global_c2 * global_delta_vcdu) + ((global_c3 / 2.0) * global_delta_vcdu**2))
    nrt_df['global_predicted_time'] = global_predicted_time
    global_residuals_sec = global_tsc - global_predicted_time

    nrt_df['global_init_time'] =   global_c1 + global_tsc[0]
    nrt_df['global_rate'] =        global_c2
    nrt_df['global_drift'] =       global_c3
    nrt_df['global_resid_musec'] = global_residuals_sec / (1e-6 * 1e2) # in usec
    nrt_df['global_variance'] =    global_s2

    # 2nd order standard deviations
    nrt_df['global_std_dev_utc0'] =  global_std_devs[0]
    nrt_df['global_std_dev_rate'] =  global_std_devs[1]
    nrt_df['global_std_dev_drift'] = global_std_devs[2]

    # --- OUTPUT LOGGING ---
    ref_time = nrt_df['astropy_time'].iloc[0].strftime('%Y:%j:%H:%M:%S.%f')
    ref_count = nrt_df['corrected_vcdu'].iloc[0]
    span_days = (nrt_df['astropy_time'].iloc[-1] - nrt_df['astropy_time'].iloc[0]).sec / 86400.0

    rate_str = f"{global_c2:.12f}"
    drift_str = f"{global_c3:.3e}"

    print(
        f"\n{'RefTime (UTC)':<24} | {'RefCounts':<10} | {'Rate (Quadratic)':<32} | "
        f"{'Drift (Quadratic)':<25} | {'Span (Days)':<12}\n"
        f"{ref_time:<24} | {ref_count:<10.0f} | {rate_str:<32} | "
        f"{drift_str:<25} | {f'{span_days:.2f} Days':<12}"
    )
