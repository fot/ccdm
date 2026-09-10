import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from openpyxl import load_workbook
from copy import copy
from astropy.time import Time, TimeDelta
import astropy.units as u

#Local Imports
from misc import log_callback, get_constants

# CONSTANTS
constants = get_constants()
JD_1985 = constants['JD_1985']
INIT_CLOCK = constants['INIT_CLOCK']
NOMINAL_RATE = constants['NOMINAL_RATE']


def get_correlation_report_title(df):
    "Get the name of the correlation report file based on the output path."
    first_utc = df['datetime'].iloc[0]
    last_utc =  df['datetime'].iloc[-1]
    filetitle = f"rclkout_{first_utc.strftime('%y')}_{first_utc.strftime('%j')}_{last_utc.strftime('%j')}"
    return filetitle


def generate_correlation_report(nrt_df, nrt_paths=None, erp_path=Path(), output_path=Path()):
    """
    Generates a legacy-formatted .txt report mirroring the 1990s Pascal OFLS tool.
    Uses the standardized quadratic column names from the updated Pipeline dataframe.
    Agnostic exit path: returns the text string, optionally writes to file.
    """

    if nrt_paths is None:
        nrt_paths = []

    # Pull the global coefficients directly from the DataFrame
    global_c1 = nrt_df['global_init_time'].iloc[0]
    global_c2 = nrt_df['global_rate'].iloc[0]
    global_c3 = nrt_df['global_drift'].iloc[0]
    global_rate = global_c2
    global_drift = global_c3

    # Pull the global standard deviations and variance from the DataFrame
    global_variance = nrt_df['global_variance'].iloc[0]
    global_std_rate = nrt_df['global_std_dev_utc0'].iloc[0]

    # 1. Extract Global Anchor Data
    first_vcdu = nrt_df['vcdu'].iloc[0]
    first_abs_time = nrt_df['adjusted_ground_time'].iloc[0]
    first_utc = nrt_df['datetime'].iloc[0]
    last_utc =  nrt_df['datetime'].iloc[-1]

    global_resid_sec = nrt_df['global_resid_musec'] * 1e6

    # Safely define span_days for both the summary printout and the uncertainty projection loop
    span_days = (last_utc - first_utc).total_seconds() / 86400.0

    # Safely extract the drift standard deviation (or default to 0.0 if missing)
    if 'global_std_dev_drift' in nrt_df.columns:
        global_std_drift = nrt_df['global_std_dev_drift'].iloc[0] 
    else:
        global_std_drift = 0.0

    total_packets = len(nrt_df)
    total_passes = nrt_df['pass_id'].nunique()

    # Extract first pass detail values for header
    first_delay = nrt_df['adjusted_propogation_time'].iloc[0]

    # 2. Begin In-Memory String Building
    report_text = ""
    def write(text):
        nonlocal report_text
        report_text += text

    # =========================================================
    # --- SECTION 1: HEADER & FILE MANIFEST
    # =========================================================
    filetitle = get_correlation_report_title(nrt_df)
    write(f"****** begin rclk corr ****** Run: ..\\{output_path.name}\\{filetitle}.txt\n")
    write(f"Run Time = {datetime.now().strftime('%m/%d/%Y (%Y:%j) %H:%M:%S')}\n")

    # We use Path(__file__) if running as a script, or just string fallback if in a notebook
    try:
        base_dir = Path(__file__).parent.resolve()
    except NameError:
        base_dir = Path.cwd()

    write(f"DSN Calibration File: {base_dir / 'dsn_data.json'}\n")
    write(f"DelayFileName: {base_dir / 'calibration_data.json'}\n")
    write(f"ERPFileName: {str(erp_path).replace("/", "\\")}\n")
    write(f"first adjusted dsn time (sec) = {first_abs_time:.9f}\n")
    write(f"first delay (sec) = {first_delay:.8f},  first count = {first_vcdu:.0f}\n")

    # Write out the .nrt file list with extended pass details
    pass_groups = list(nrt_df.groupby('pass_id'))

    # If no nrt paths provided (e.g. from GUI MAUDE pull), generate placeholders
    if not nrt_paths and total_passes > 0:
        nrt_paths = [f"Database_Extract_{i}" for i in range(total_passes)]

    for idx, path in enumerate(nrt_paths, start=1):
        filename = os.path.basename(path)

        # Extract the corresponding pass data
        if idx - 1 < len(pass_groups):
            _, group = pass_groups[idx - 1]

            # Format start and end times (dropping microseconds with %Y:%j:%H:%M:%S)
            start_utc = group['datetime'].iloc[0].strftime('%Y:%j:%H:%M:%S')
            end_utc = group['datetime'].iloc[-1].strftime('%Y:%j:%H:%M:%S')

            start_vcdu = group['vcdu'].iloc[0]
            end_vcdu = group['vcdu'].iloc[-1]

            # Format the Ground Station ID (Defaulting to 24 if dss_id isn't explicitly in the DF)
            dss_val = group['dss_id'].iloc[0] if 'dss_id' in group.columns else 24
            dss_str = f"DSS-{int(dss_val)}"

            # Safely extract the Bit Rate Code from the updated dataframe column
            if 'bit_rate_code' in group.columns:
                rate_id = str(int(group['bit_rate_code'].iloc[0]))
            else:
                rate_id = "N/A"

            # Print the fully padded line to match the legacy spacing
            write(f" {idx:>2}: {filename:<20}  {start_utc}  {start_vcdu:<8.0f}  "
                    f"{end_utc}  {end_vcdu:<8.0f}  {dss_str:<6}  {rate_id}\n")
        else:
            # Safety fallback just in case the file loop outruns the dataframe passes
            write(f" {idx:>2}: {filename}\n")

    # =========================================================
    # --- SECTION 2: COMBINED CORRELATION RESULTS
    # =========================================================
    write(f"Init Rate: {INIT_CLOCK:.12f},  poly_degree= 2\n")
    # cvec prints the unscaled raw coefficients of the quadratic fit
    write(f"cvec:  {global_c1:1.15E}  {global_c2:1.15E}  {global_c3:1.15E}\n")
    write(f"num data = {total_packets},  skip num = 0\n")

    write("-" * 10 + "\n")

    write(f"refcnt   = {first_vcdu:.0f}\n")
    write(f"reftim   = {first_abs_time:.9f} sec,    stdtim   = {global_variance:.3e} micsec\n")
    write(f"clkrate  = {global_rate:.15f} sec/cnt,   stdrate  = {global_std_rate:.3e} sec/cnt\n")
    write(f"clkdrift = {global_drift:.7e} sec/cnt^2,    stddrift = {global_std_drift:.3e} sec/cnt^2\n")

    write("-" * 10 + "\n")

    # Global Summary Line
    abs_init_time = Time('1985-01-01 00:00:00', scale='tai') + TimeDelta(first_abs_time, format='sec')

    # Calculate timezero (When VCDU would theoretically be 0)
    delta_vcdu_zero = 0.0 - first_vcdu
    delta_sec_zero = (global_rate * delta_vcdu_zero) + (0.5 * global_drift * (delta_vcdu_zero ** 2))
    vcdu_zero_time = abs_init_time + TimeDelta(delta_sec_zero, format="sec")

    # Calculate timeroll (When VCDU reaches 2**24)
    delta_vcdu_roll = (2**24) - first_vcdu
    delta_sec_roll = (global_rate * delta_vcdu_roll) + (0.5 * global_drift * (delta_vcdu_roll ** 2))
    vcdu_roll_time = abs_init_time + TimeDelta(delta_sec_roll, format="sec")

    abs_init_time.precision =  6
    vcdu_zero_time.precision = 6 # Enforce 6 decimal places for microseconds in astropy output
    vcdu_roll_time.precision = 6

    # Legacy header printout spacing
    write(f"{abs_init_time.yday} {first_vcdu:.0f} {global_rate:.12f} {global_drift:.3E} {span_days:.2f}\n")
    write(f"timezero = {vcdu_zero_time.yday}, timeroll = {vcdu_roll_time.yday}\n")

    # Construct the summary line
    rms_resid_musec = np.sqrt(global_c2) * 1e6
    max_resid_musec = np.max(np.abs(global_resid_sec))

    write(f"  {first_vcdu:.0f}{first_abs_time:.9f} "
          f"{global_rate:.14f} {global_drift:.3E} "
          f"{rms_resid_musec:.2f} {max_resid_musec:.2f}\n"
          )

    write("-" * 10 + "\n")

    # Write RMS stats
    max_embt_err_sec = 0.99  # Replace with actual calculation, e.g., np.max(np.abs(nrt_df['embt_err']))
    num_write = len(nrt_df)

    write(f"rmsresid = {rms_resid_musec:>9.3f} micsec, "
          f"maxresid = {max_resid_musec:>9.3f} micsec, "
          f"maxembterr = {max_embt_err_sec:>7.2f} sec\n")

    write(f"numwrite = {num_write} to {filetitle}.csv\n")

    write("****** end rclk corr ******\n\n")

    # =========================================================
    # --- SECTION 3: PRIMARY CORRELATION RESULTS (TABLE FORMAT)
    # =========================================================
    # Explanatory Paragraph
    write("The above results are obtained by simultaneously fitting data from all \n")
    write("contacts.  The OFLS SCLK application does a separate, \"primary\", fit for \n")
    write("each contact and saves the results as intermediate data.  These data are \n")
    write("then processed to produce the \"combined\" correlation.  The OFLS algorithm, \n")
    write("inherited from HST, has the alleged advantage of processing data for each \n")
    write("contact just once.  The disadvantage is increased complexity.  The \n")
    write("following results are obtained with the \"primary/combined\" method plus \n")
    write("experimental enhancements to be considered for improvement to SCLK.   \n\n")

    write("-" * 42 + "\n")
    write("Primary Correlation Results\n")

    # Legacy Table Header
    write(f"{'ref time':<24} {'ref vcdu':>9} {'clock rate':>17} {'drift':>12} {'num':>6} "
          f"{'rmsres':>10} {'maxres':>11} {'minres':>11} {'TimeAdj':>9}\n")
    # Loop through the dataframe pass by pass to extract the 2nd-degree pipeline results
    previous_raw_vcdu = 0
    rollover_offset = 0

    for pass_num, (pass_id, group) in enumerate(nrt_df.groupby('pass_id'), start=1):

        p_reftime_str = group['datetime'].iloc[0].strftime('%Y:%j:%H:%M:%S.%f')

        # Determine if VCDU rolled over (Compare RAW to RAW)
        raw_vcdu = group['vcdu'].iloc[0]
        rollover_offset += 2**24 if previous_raw_vcdu > raw_vcdu else 0
        previous_raw_vcdu = raw_vcdu
        p_refcnt = raw_vcdu + rollover_offset

        # Updated variables here to pull the quadratic variables
        p_clkrate = group['rate'].iloc[0]
        p_clkdrift = group['drift'].iloc[0]
        p_numpts = len(group)

        # Variance to Microseconds
        p_rms_resid = np.sqrt(group['resid_variance'].iloc[0]) * 1e6

        # Extract Max and Min residuals dynamically from the new quadratic residual array
        if 'resid_musec' in group.columns:
            p_maxres = group['resid_musec'].max()
            p_minres = group['resid_musec'].min()
        else:
            p_maxres = 0.0
            p_minres = 0.0

        # TimeAdj placeholder (Usually 0.0 unless there was an explicit ground command shift)
        p_timeadj = 0.0

        # Formatted with precise string padding to match the legacy column alignment
        write(f"{p_reftime_str:<24} {int(p_refcnt):>9d} {p_clkrate:>17.13f} {p_clkdrift:>12.3E} "
              f"{int(p_numpts):>6d} {p_rms_resid:>10.3f} {p_maxres:>11.3f} {p_minres:>11.3f} {p_timeadj:>9.3f}\n")
    write("-" * 42 + "\n")

    # =========================================================
    # --- SECTION 3.5: COMBINED CORRELATION RESULTS
    # =========================================================
    # Note: The legacy report displays TWO values for stdtim, stdrate, and stddrift
    # (often formal error vs. actual/empirical error from the pipeline). 
    # You will need to map these to the correct columns in your nrt_df. 
    # Placeholders (e.g., _val1, _val2) are used here for formatting.
    
    stdtim_val1, stdtim_val2 = 0.0, 0.0 # Replace with actual DF variables
    stdrate_val1, stdrate_val2 = 0.0, 0.0 # Replace with actual DF variables
    stddrift_val1, stddrift_val2 = 0.0, 0.0 # Replace with actual DF variables
    sqrt_var = np.sqrt(global_variance)

    write(f"Combined Correlation Results, NumData = {total_packets}, NumPrimCorr = {total_passes}\n")
    write(f"refcnt   = {first_vcdu:.1f}\n")
    write(f"reftim   = {first_abs_time:.9f} sec,  stdtim = {stdtim_val1:.3E}, {stdtim_val2:.3E} sec\n")
    write(f"clkrate  = {global_rate:.15f} sec/cnt, stdrate = {stdrate_val1:.3E}, {stdrate_val2:.3E} sec/cnt\n")
    write(f"clkdrift = {global_drift:.7E} sec/cnt^2,  stddrift = {stddrift_val1:.3E}, {stddrift_val2:.3E} sec/cnt^2\n")
    write(f"reftime  = {abs_init_time.yday},  sqrt(var) = {sqrt_var:.3E} sec\n")
    write("-" * 42 + "\n")

    # =========================================================
    # --- SECTION 3.6: PRIMARY CORRELATION RESIDUALS TABLE
    # =========================================================
    # Adjusted header spacing to strictly match the legacy printout
    write(f"Primary Correlation Residuals,          NumPrimCorr = {total_passes:>3}\n")
    
    # Use exact column widths to align headers seamlessly over the data
    write(f"{'num':>3}{'deltacnt':>14}{'deltasec':>14}{'maxresid':>14}{'minresid':>14}\n")

    previous_raw_vcdu = 0
    rollover_offset = 0

    for pass_num, (pass_id, group) in enumerate(nrt_df.groupby('pass_id'), start=1):
        # Handle the VCDU rollover to calculate the continuous delta count
        raw_vcdu = group['vcdu'].iloc[0]
        rollover_offset += 2**24 if previous_raw_vcdu > raw_vcdu else 0
        previous_raw_vcdu = raw_vcdu
        
        p_refcnt = raw_vcdu + rollover_offset
        deltacnt = p_refcnt - first_vcdu

        # NOTE: "deltasec" in the legacy text often refers to the scaled time delta or  
        # the difference between the primary fit and combined fit. Update to your specific column.
        p_deltasec = group['primary_delta_sec'].iloc[0] if 'primary_delta_sec' in group.columns else 0.0
        
        if 'quadratic_resid_musec' in group.columns:
            p_maxres = group['quadratic_resid_musec'].max()
            p_minres = group['quadratic_resid_musec'].min()
        else:
            p_maxres, p_minres = 0.0, 0.0

        # Right-aligned fixed widths (14 characters per column) with precise decimal places
        write(f"{pass_num:>3}{deltacnt:>14.2f}{p_deltasec:>14.3f}{p_maxres:>14.3f}{p_minres:>14.3f}\n")

    # =========================================================
    # --- SECTION 3.7: OVERALL RESIDUALS FOOTER
    # =========================================================
    # Calculate overall RMS and Max Absolute Residual across the entire dataset
    if 'quadratic_resid_musec' in nrt_df.columns:
        overall_rms = np.sqrt((nrt_df['quadratic_resid_musec']**2).mean())
        max_abs_resid = nrt_df['quadratic_resid_musec'].abs().max()
    else:
        overall_rms = 0.0
        max_abs_resid = 0.0

    # Added severe right-padding to match the gap in the legacy image footer
    write(f"RMS residual = {overall_rms:>11.3f}, Maximum abs(residual) = {max_abs_resid:>11.3f} microsec\n")
    write("-" * 42 + "\n")

    # =========================================================
    # --- SECTION 4: QUADRATIC FIT SUMMARY
    # =========================================================
    write(f"Quadratic fit of reference times from {total_passes} primary correlations\n")
    write(f"refcnt   = {first_vcdu:.1f}\n")

    # stdtim in microseconds
    stdtim_micsec = np.sqrt(global_variance) * 1e6

    # Padding applied to values (>20) and units (<11) to force strict columnar alignment
    write(f"reftim   = {first_abs_time:>20.9f} {'sec,':<11} stdtim   = {stdtim_micsec:>10.2f} micsec\n")
    write(f"clkrate  = {global_rate:>20.15f} {'sec/cnt,':<11} stdrate  = {global_std_rate:>10.3E} sec/cnt\n")
    write(f"clkdrift = {global_drift:>20.7E} {'sec/cnt^2,':<11} stddrift = {global_std_drift:>10.3E} sec/cnt^2\n")
    write("-" * 42 + "\n")

    # =========================================================
    # --- SECTION 5: UNCERTAINTY PROPAGATION
    # =========================================================
    write("Uncertainty of computed times at regular intervals\n")
    write("Time (UTC)                  count delta-cnt uncertainty (microsec)\n")

    # Calculate the nominal VCDU counts that tick by in exactly 24 hours
    counts_per_day = 86400.0 / global_rate

    # Propagate exactly 30 days as requested
    total_days_to_project = 30 

    # Extract the 3x3 covariance matrix from the dataframe.
    if 'global_covariance_matrix' in nrt_df.columns:
        cov_matrix = nrt_df['global_covariance_matrix'].iloc[0]
    else:
        # Fallback to a diagonal matrix if the full covariance matrix isn't mapped.
        # Note: A diagonal matrix lacks the off-diagonal cross-correlation terms 
        # required to produce the initial "dip" in the bow-tie error curve.
        cov_matrix = np.diag([global_variance, global_std_rate**2, global_std_drift**2])

    current_date = first_utc
    current_vcdu = first_vcdu

    for day in range(total_days_to_project + 1):
        # Truncate to 6 microsecond decimal places to match legacy string format
        date_str = current_date.strftime('%Y:%j:%H:%M:%S.%f')
        delta_cnt = day * counts_per_day

        # The evaluation vector H for the quadratic fit: [1, x, 0.5 * x^2]
        H = np.array([1.0, delta_cnt, 0.5 * (delta_cnt ** 2)])

        # Predicted Variance = H * P * H^T
        pred_variance = H @ cov_matrix @ H.T

        # Convert predicted variance (sec^2) to standard deviation (microseconds)
        uncert_micsec = np.sqrt(pred_variance) * 1e6

        # Formatted with right-alignment padding for the numeric columns
        write(f"{date_str:<24} {int(current_vcdu):>8d} {int(delta_cnt):>9d}   {uncert_micsec:>5.2f}\n")

        # Step forward exactly 24 hours and add 1 day's worth of VCDU counts
        current_date += timedelta(days=1)
        current_vcdu += counts_per_day

    # 3. Handle Exit Paths
    if output_path:
        filetitle = Path(output_path / filetitle).with_suffix(".txt")
        with open(filetitle, 'w') as f:
            f.write(report_text)
        log_callback(f"Report successfully initialized and written. Saved to {filetitle.name}")


def generate_trending_report(nrt_df, output_path=None):
    """
    TOOL 1 REPLICA: Absolute Quadratic Trending Math using Pandas Native Excel Appending 
    with Live Formulas & Formatting.
    Agnostic exit path: returns the new dataframe slice, optionally appends to Excel file.
    """
    NOMINAL_RATE = 0.25625
    
    # Define astropy Time epochs in TAI (continuous seconds, no leap seconds)
    epoch_1958 = Time('1958-01-01 00:00:00', scale='tai')
    epoch_1985 = Time('1985-01-01 00:00:00', scale='tai')

    # Int64 Overflow s/ VCDU Rollover Protection
    vcdus = nrt_df['vcdu'].values.astype(np.float64).copy() 
    for idx in np.where(np.diff(vcdus) < -1000000)[0]:
        vcdus[idx+1:] += 2**24

    # 1. Quickly check the Excel file just to find the last empty row
    current_max_row = 1
    file_exists = False

    if output_path:
        file_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0
        if file_exists:
            try:
                wb = load_workbook(output_path, read_only=True)
                current_max_row = wb.active.max_row
                wb.close()
            except Exception as e:
                print(f"[ERROR] Could not read Excel file to find max row: {e}. Aborting.")
                return

    # 2. Process new passes and inject Live Excel Formulas
    new_rows = []

    for i, (day_id, group) in enumerate(nrt_df.groupby('pass_id')):
        pass_vcdu = group['vcdu'].values

        # Pull the new 2nd-order degree fit data
        trend_init_time = group['init_time'].iloc[0]
        trend_rate = group['rate'].iloc[0]
        trend_drift = group['drift'].iloc[0]

        major_frames = pass_vcdu[pass_vcdu % 128 == 0]
        vcdu_ref = int(major_frames[0]) if len(major_frames) > 0 else int(pass_vcdu[0] + (128 - (pass_vcdu[0] % 128)))
        delta_to_ref = vcdu_ref - pass_vcdu[0]

        # Evaluate the absolute 2nd-degree polynomial directly at the major frame
        # (Since trend_init_time is 1985 epoch, this result is seconds since 1985)
        ref_time_sec = (trend_init_time +
                       (trend_rate * delta_to_ref) +
                       ((trend_drift / 2.0) * (delta_to_ref ** 2)))

        # --- ASTROPY TIME CONVERSION ---
        # Add those continuous seconds to the 1985 TAI epoch, then convert to UTC to apply leap seconds
        dt_final_tai = epoch_1985 + (ref_time_sec * u.second)
        dt_final_utc = dt_final_tai.utc
        
        # Extract native Python datetime from the UTC object for Excel formatting
        dt_datetime = dt_final_utc.datetime
        hosc_final = dt_datetime.strftime('%Y:%j:%H:%M:%S.%f')
        doy_decimal = dt_datetime.timetuple().tm_yday + (dt_datetime.hour / 24.0) + (dt_datetime.minute / 1440.0) + ((dt_datetime.second + dt_datetime.microsecond / 1e6) / 86400.0)

        # --- EXCEL FORMULA INJECTION ---
        # Calculate exactly which Excel row this specific loop will be written to
        excel_row = current_max_row + 1 + i

        formula_30min = f"=D{excel_row}-0.25625"

        # If this isn't the very first row under the header, we can build the 1-day formulas
        if excel_row > 2:
            formula_1day = (f"=IF((B{excel_row}-B{excel_row-1})<0, "
                            f"(C{excel_row}-C{excel_row-1})/(B{excel_row}-B{excel_row-1}+16777216)-{NOMINAL_RATE}, "
                            f"(C{excel_row}-C{excel_row-1})/(B{excel_row}-B{excel_row-1})-{NOMINAL_RATE})")
            formula_1day_sq = f"=H{excel_row}^2"
        else:
            formula_1day = np.nan
            formula_1day_sq = np.nan

        # Map directly to the headers
        new_rows.append({
            'RefTime(UTC)': hosc_final,                                  # Col A
            'VCDU': vcdu_ref,                                            # Col B
            'RefTime(sec)': ref_time_sec,                                # Col C
            'Rate(sec/cnt)': trend_rate,                                 # Col D
            'Drift(sec/^nct^2)': trend_drift,                            # Col E
            'day of yr': doy_decimal,                                    # Col F
            'date time': dt_datetime,                                         # Col G
            '1-day rate': formula_1day,                                  # Col H (Live Formula)
            '30-min rate': formula_30min,                                # Col I (Live Formula)
            'Data generated using CLKFILES.exe and input from': np.nan,  # Col J 
            'Comment 3': np.nan,                                         # Col K
            'Comment 4': np.nan,                                         # Col L
            'Comment 5': np.nan,                                         # Col M
            '1-day rate squared': formula_1day_sq                        # Col N (Live Formula)
        })

    new_df = pd.DataFrame(new_rows)
    if new_df.empty:
        return new_df

    # 3. Safely APPEND the new data directly to the existing Excel file and COPY FORMATTING
    if output_path:
        try:
            if file_exists:
                with pd.ExcelWriter(output_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                    sheet_name = list(writer.sheets.keys())[0] if writer.sheets else 'Sheet1'
                    ws = writer.sheets[sheet_name]
                    
                    # Drop the new data in
                    new_df.to_excel(writer, sheet_name=sheet_name, startrow=current_max_row, index=False, header=False)
                    
                    # --- APPLY FORMATTING ---
                    if current_max_row >= 2:
                        for col_idx in range(1, len(new_df.columns) + 1):
                            src_cell = ws.cell(row=current_max_row, column=col_idx)
                            
                            for row_offset in range(1, len(new_df) + 1):
                                tgt_cell = ws.cell(row=current_max_row + row_offset, column=col_idx)
                                tgt_cell.font = copy(src_cell.font)
                                tgt_cell.border = copy(src_cell.border)
                                tgt_cell.fill = copy(src_cell.fill)
                                tgt_cell.number_format = copy(src_cell.number_format)
                                tgt_cell.alignment = copy(src_cell.alignment)

                log_callback(f"Trending report safely appended {len(new_df)} rows. Saved to {output_path.name}")
            else:
                new_df.to_excel(output_path, index=False)
                log_callback(f"Trending report successfully created. Saved to {output_path.name}")

        except PermissionError:
            print("[ERROR] Could not write to Excel file. Is the spreadsheet currently open in Excel?")

    return new_df
