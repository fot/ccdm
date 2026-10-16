import os
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
from pathlib import Path


def generate_correlation_report(nrt_df, nrt_paths, erp_path, output_filepath):
    """
    Generates a legacy-formatted .txt report mirroring the 1990s Pascal OFLS tool.
    Uses the standardized column names from the updated Pipeline dataframe.
    """
    INIT_CLOCK = 0.256250 # Used only for the legacy printout string
    
    # Ensure datetime column is properly cast to datetime objects if it was read from a CSV
    if not pd.api.types.is_datetime64_any_dtype(nrt_df['datetime']):
        nrt_df['datetime'] = pd.to_datetime(nrt_df['datetime'])

    # Pull the global coefficients directly from the DataFrame
    global_c1 = nrt_df['global_init_time'].iloc[0]
    global_c2 = nrt_df['global_rate_quad'].iloc[0]
    global_c3 = nrt_df['global_drift_quad'].iloc[0]

    # Pull the global standard deviations and variance from the DataFrame
    global_variance = nrt_df['global_variance'].iloc[0]
    global_std_rate = nrt_df['global_std_dev_rate'].iloc[0]
    
    # 1. Extract Global Anchor Data
    first_vcdu = nrt_df['vcdu'].iloc[0]
    first_abs_time = nrt_df['adjusted_ground_time'].iloc[0]
    first_utc = nrt_df['datetime'].iloc[0]
    last_utc =  nrt_df['datetime'].iloc[-1]

    global_rate = global_c2
    global_drift = global_c3
    
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

    # 2. Begin File Writing
    with open(output_filepath, 'w') as f:
        
        # =========================================================
        # --- SECTION 1: HEADER & FILE MANIFEST
        # =========================================================
        f.write("*** begin rclk corr ******\n")
        f.write(f" Run Time {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}\n")
        
        # We use Path(__file__) if running as a script, or just string fallback if in a notebook
        try:
            base_dir = Path(__file__).parent.resolve()
        except NameError:
            base_dir = Path.cwd()
            
        f.write(" DSN Calibration File: "
                f"{base_dir / 'dsn_data.json'}\n")
        f.write(" DelayFileName: "
                f"{base_dir / 'calibration_data.json'}\n")
        f.write(f" ERPFileName: {erp_path}\n\n")
        
        f.write(f"first adjusted dsn time (sec) = {first_abs_time:.9f}\n")
        f.write(f"first delay (sec) = {first_delay:.8f},  first count = {first_vcdu:.0f}\n\n")

        # Write out the .nrt file list with extended pass details
        pass_groups = list(nrt_df.groupby('pass_id'))

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
                f.write(f" {idx:>2}: {filename:<20}  {start_utc}  {start_vcdu:<8.0f}  "
                        f"{end_utc}  {end_vcdu:<8.0f}  {dss_str:<6}  {rate_id}\n")
            else:
                # Safety fallback just in case the file loop outruns the dataframe passes
                f.write(f" {idx:>2}: {filename}\n")

        # =========================================================
        # --- SECTION 2: COMBINED CORRELATION RESULTS
        # =========================================================
        f.write(f"\nInit Rate: {INIT_CLOCK:.7f},  poly_degree= 2\n")
        # cvec prints the unscaled raw coefficients of the quadratic fit
        f.write(f"cvec:  {global_c1:1.15E}  {global_c2:1.15E}  {global_c3:1.15E}\n")
        f.write(f"num data = {total_packets},  skip num = 0\n")

        f.write("-" * 10 + "\n") 

        f.write(f"refcnt   = {first_vcdu:.1f}\n")
        f.write(f"reftim   = {first_abs_time:.9f} sec,      stdtim = {np.sqrt(global_variance) * 1e6:.3e} micsec\n") 
        f.write(f"clkrate  = {global_rate:.15f} sec/cnt,    stdrate = {global_std_rate:.3e} sec/cnt\n") 
        f.write(f"clkdrift = {global_drift:.7e} sec/cnt^2,  stddrift = {global_std_drift:.3e} sec/cnt^2\n") 

        f.write("-" * 10 + "\n")

        # Global Summary Line
        f.write(f"{first_utc.strftime('%Y:%j:%H:%M:%S.%f')}  {first_vcdu:.0f}  {global_rate:.12f}"
                f"  {global_drift:.7e}  {span_days:.1f} days\n")
        
        f.write(f"timezero = {first_utc.strftime('%Y:%j:%H:%M:%S.%f')}\n\n")

        # =========================================================
        # --- SECTION 3: PRIMARY CORRELATION RESULTS (TABLE FORMAT)
        # =========================================================
        # Explanatory Paragraph
        f.write("The above results are obtained by simultaneously fitting data from all \n")
        f.write("contacts.  The OFLS SCLK application does a separate, \"primary\", fit for \n")
        f.write("each contact and saves the results as intermediate data.  These data are \n")
        f.write("then processed to produce the \"combined\" correlation.  The OFLS algorithm, \n")
        f.write("inherited from HST, has the alleged advantage of processing data for each \n")
        f.write("contact just once.  The disadvantage is increased complexity.  The \n")
        f.write("following results are obtained with the \"primary/combined\" method plus \n")
        f.write("experimental enhancements to be considered for improvement to SCLK.   \n\n")

        f.write("-" * 42 + "\n")
        f.write("Primary Correlation Results\n")

        # Legacy Table Header
        f.write("ref time                  ref vcdu    clock rate       drift        num    rmsres    maxres    minres    TimeAdj\n")

        # Loop through the dataframe pass by pass to extract the Cubic pipeline results
        previous_raw_vcdu = 0
        rollover_offset = 0

        for pass_num, (pass_id, group) in enumerate(nrt_df.groupby('pass_id'), start=1):
            
            p_reftime_str = group['datetime'].iloc[0].strftime('%Y:%j:%H:%M:%S.%f')
            
            # Determine if VCDU rolled over (Compare RAW to RAW)
            raw_vcdu = group['vcdu'].iloc[0]
            rollover_offset += 2**24 if previous_raw_vcdu > raw_vcdu else 0
            previous_raw_vcdu = raw_vcdu
            p_refcnt = raw_vcdu + rollover_offset

            p_clkrate = group['pass_cubic_rate'].iloc[0]
            p_clkdrift = group['pass_cubic_drift'].iloc[0]
            p_numpts = len(group)
            
            # Variance to Microseconds
            p_rms_resid = np.sqrt(group['pass_resid_variance'].iloc[0]) * 1e6
            
            # Extract Max and Min residuals dynamically from your calculated array
            if 'resid_musec' in group.columns:
                p_maxres = group['resid_musec'].max()
                p_minres = group['resid_musec'].min()
            else:
                p_maxres = 0.0
                p_minres = 0.0
                
            # TimeAdj placeholder (Usually 0.0 unless there was an explicit ground command shift)
            p_timeadj = 0.0 
            
            # Formatted with precise string padding to match the legacy column alignment
            f.write(f"{p_reftime_str:<24}  {p_refcnt:<8.0f}  {p_clkrate:.13f}  {p_clkdrift:>11.3E}   "
                    f"{p_numpts:<4}     {p_rms_resid:>5.3f}     {p_maxres:>5.3f}    {p_minres:>6.3f}    {p_timeadj:>6.3f}\n")

        # =========================================================
        # --- SECTION 3 FOOTER: OVERALL RESIDUALS
        # =========================================================
        # Calculate overall RMS and Max Absolute Residual across the entire dataset
        if 'resid_musec' in nrt_df.columns:
            overall_rms = np.sqrt((nrt_df['resid_musec']**2).mean())
            max_abs_resid = nrt_df['resid_musec'].abs().max()
        else:
            overall_rms = 0.0
            max_abs_resid = 0.0

        f.write(f"RMS residual = {overall_rms:>8.3f}, Maximum abs(residual) = {max_abs_resid:>8.3f} microsec\n")
        f.write("-" * 42 + "\n")

        # =========================================================
        # --- SECTION 4: QUADRATIC FIT SUMMARY
        # =========================================================
        f.write(f"Quadratic fit of reference times from {total_passes} primary correlations\n")
        f.write(f"refcnt   = {first_vcdu:.1f}\n")
        
        # stdtim in microseconds
        stdtim_micsec = np.sqrt(global_variance) * 1e6
        
        # Use specific spacing and scientific notation to match the legacy Fortran/Pascal printout
        f.write(f"reftim   = {first_abs_time:.9f} sec,   stdtim   = {stdtim_micsec:>7.2f} micsec\n")
        f.write(f"clkrate  = {global_rate:18.15f} sec/cnt, stdrate  = {global_std_rate:>12.3E} sec/cnt\n")
        f.write(f"clkdrift = {global_drift:18.7E} sec/cnt^2, stddrift = {global_std_drift:>12.3E} sec/cnt^2\n")
        f.write("-" * 42 + "\n")

        # =========================================================
        # --- SECTION 5: UNCERTAINTY PROPAGATION
        # =========================================================
        f.write("Uncertainty of computed times at regular intervals\n")
        f.write("Time (UTC)                   count  delta-cnt  uncertainty (microsec)\n")

        # Calculate the nominal VCDU counts that tick by in exactly 24 hours
        counts_per_day = 86400.0 / global_rate

        # Determine how many days to project (Span of data + 2 days into the future)
        total_days_to_project = int(math.ceil(span_days)) + 2 

        current_date = first_utc
        current_vcdu = first_vcdu
        
        for day in range(total_days_to_project + 1):
            date_str = current_date.strftime('%Y:%j:%H:%M:%S.%f')
            delta_cnt = day * counts_per_day
            
            # --- UNCERTAINTY MATH PLACEHOLDER ---
            # To get the true statistical "Bow-Tie", you must multiply delta_cnt against your 3x3 Covariance Matrix here.
            # For now, we will print the baseline stdtim so the text layout is completed.
            uncert_micsec = stdtim_micsec 
            
            # Print the daily step. Note the specific right-alignment padding to keep the columns perfectly stacked.
            f.write(f"{date_str:<24}  {int(current_vcdu):>8d}  {int(delta_cnt):>9d}   {uncert_micsec:>4.2f}\n")
            
            # Step forward exactly 24 hours and add 1 day's worth of VCDU counts
            current_date += timedelta(days=1)
            current_vcdu += counts_per_day

    print(f"Report successfully initialized and written to {output_filepath}")
