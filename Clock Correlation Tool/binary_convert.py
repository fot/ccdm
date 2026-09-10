from pathlib import Path
import numpy as np
import struct
import pandas as pd
import os
from scipy.optimize import fsolve


# Local Imports
from misc import log_callback, get_constants


# Pull Constants
CONSTANTS = get_constants()
JD_1985 = CONSTANTS['JD_1985']


def apply_fresh_padding(filepath, block_size=512):
    # Because you added/removed rows, the old padding is useless.
    # We calculate completely fresh padding to ensure it fits the OS sector boundary.
    current_size = os.path.getsize(filepath)
    remainder = current_size % block_size
    if remainder != 0:
        padding_needed = block_size - remainder
        with open(filepath, 'ab') as file:
            # We use Null bytes (\x00) for padding as it's the safest legacy default
            file.write(b'\x00' * padding_needed)


def format_for_binary_export(nrt_df):
    """
    Transforms the processed nrt_df into the exact OP19 fixed-width binary specification.
    Includes a toggle ('cubic' or 'quadratic') to select which fit results are exported.
    """
    op19_records = []

    c1 = nrt_df['global_predicted_time'].iloc[0]
    c2 = nrt_df['global_rate'].iloc[0]
    c3 = nrt_df['global_drift'].iloc[0] / 2.0  
    c4 = 0.0

    std_dev_array = (
        float(f"{nrt_df['global_std_dev_utc0'].iloc[0]:.4e}"),
        float(f"{nrt_df['global_std_dev_rate'].iloc[0]:.4e}"),
        float(f"{nrt_df['global_std_dev_drift'].iloc[0]:.4e}"),
        0.0
    )
    resid_var = nrt_df['global_variance'].iloc[0]

    # --- EPOCH SHIFTS (1958 -> 1985) ---
    adj_data_l = nrt_df['adjusted_ground_time'].iloc[0] - JD_1985
    adj_data_f = nrt_df['adjusted_ground_time'].iloc[-1] - JD_1985
    ref_gmt = c1 - JD_1985

    # --- GLOBAL ERROR GROWTH (SMART HEURISTICS APPLIED) ---
    thresholds = [0.0001, 0.0010, 0.0100]
    errtime_array = [0.0, 0.0, 0.0]
    sigma_meas = np.sqrt(resid_var)
    n = len(nrt_df)
    d = (nrt_df['vcdu'].iloc[-1] - nrt_df['vcdu'].iloc[0]) / 2.0

    if n > 0 and d > 0 and sigma_meas > 0:
        coeff_multiplier = sigma_meas / np.sqrt(n)

        for i, target_error in enumerate(thresholds):
            def objective(t):
                ratio = t / d
                expected_var = (coeff_multiplier)**2 * (9.0/4.0 + 3.0*(ratio**2) + 45.0/4.0*(ratio**4) - 15.0/2.0*(ratio**2))
                return expected_var - (target_error**2)

            # 1. Check if the threshold is already exceeded at t=0
            if objective(0.0) >= 0:
                errtime_array[i] = 0.0
                continue

            # 2. Derive a dynamic initial guess based on the dominant polynomial term
            ratio_guess = ((target_error**2) / ((coeff_multiplier**2) * 11.25)) ** (1.0 / 4.0)
            smart_guess = d * ratio_guess

            try:
                t_counts = fsolve(objective, x0=[smart_guess])[0]
                errtime_array[i] = float(f"{(ref_gmt + (t_counts + d) * c2):.4f}")
            except Exception:
                errtime_array[i] = 0.0

    # Record generation
    op19_records.append({
        "odb_clock_adj_data_l": float(adj_data_l),
        "odb_clock_adj_data_f": float(adj_data_f),
        "odb_clock_ref_cnts": float(nrt_df['vcdu'].iloc[0]),
        "odb_clock_ref_gmt": float(ref_gmt),
        "odb_clock_std_dev": std_dev_array,
        "odb_clock_rate": float(c2),
        "odb_clock_drift": float(c3 * 2.0),
        "odb_clock_der_drift": float(c4 * 6.0),
        "odb_clock_errtime": tuple(errtime_array),
        "odb_clock_variance": float(resid_var),
        "odb_clock_majfm_cnt": 0,
        "odb_clock_majfm_utc": 0.0,
        "odb_clock_key": -int(adj_data_l),
        "odb_clock_key_char": "C**********",
        "odb_clock_base_ref": "1985:001:00:00:00.000"
    })

    return pd.DataFrame(op19_records[::-1])


def dis_file_to_dataframe(filepath):
    # Based on the OP19 Section 3.40 spec and the file's hex dump
    log_callback(f"Loading base database: {filepath.name}")

    HEADER_SIZE = 38
    RECORD_SIZE = 175
    output_data = []

    with open(filepath, 'rb') as file:
        # 1. Read the 38-byte ASCII file header
        header_data = file.read(HEADER_SIZE) 

        # 2. Extract the total record count dynamically
        try:
            header_text = header_data.decode('ascii', errors='ignore')
            header_values = header_text.split()
            total_records = int(header_values[1])
        except (ValueError, IndexError):
            print("[ERROR] Could not read record count from header. Defaulting to read all.")
            total_records = float('inf')

        record_count = 0

        # 3. Loop only for the exact number of valid records
        while record_count < total_records:
            chunk = file.read(RECORD_SIZE)
            if len(chunk) < RECORD_SIZE:
                break

            record_count += 1

            # The ASCII fields at the tail of the record
            key_char = chunk[142:153].decode('ascii', errors='ignore').strip()
            base_ref = chunk[153:174].decode('ascii', errors='ignore').strip()

            # Unpack the binary math
            binary_payload = chunk[6:142] 
            unpacked = struct.unpack('<15d i d i', binary_payload)

            # Map everything to the Section 3.40 definitions
            record = {
                "odb_clock_adj_data_l": unpacked[0],
                "odb_clock_adj_data_f": unpacked[1],
                "odb_clock_ref_cnts":   unpacked[2],
                "odb_clock_ref_gmt":    unpacked[3],
                "odb_clock_std_dev":    unpacked[4:8],
                "odb_clock_rate":       unpacked[8],
                "odb_clock_drift":      unpacked[9],
                "odb_clock_der_drift":  unpacked[10],
                "odb_clock_errtime":    unpacked[11:14],
                "odb_clock_variance":   unpacked[14],
                "odb_clock_majfm_cnt":  unpacked[15],
                "odb_clock_majfm_utc":  unpacked[16],
                "odb_clock_key":        unpacked[17],
                "odb_clock_key_char":   key_char,
                "odb_clock_base_ref":   base_ref
            }
            output_data.append(record)

    return pd.DataFrame(output_data)


def dat_file_to_dataframe(filepath):
    """
    Reads a raw binary .DAT clock correlation file.
    Returns a DataFrame with the extracted records.
    """
    log_callback(f"Loading base database: {filepath.name}")

    RECORD_SIZE = 170
    output_data = []

    with open(filepath, 'rb') as file:
        record_count = 0

        while True:
            chunk = file.read(RECORD_SIZE)
            if len(chunk) < RECORD_SIZE:
                break

            record_count += 1

            # The ASCII fields at the tail of the record
            key_char = chunk[136:147].decode('ascii', errors='ignore').strip()
            base_ref = chunk[147:168].decode('ascii', errors='ignore').strip()

            # Unpack the binary math using Big-Endian (>)
            binary_payload = chunk[0:136] 
            unpacked = struct.unpack('>15d i d i', binary_payload)

            # Map to Section 3.40 definitions
            record = {
                "odb_clock_adj_data_l": unpacked[0],
                "odb_clock_adj_data_f": unpacked[1],
                "odb_clock_ref_cnts":   unpacked[2],
                "odb_clock_ref_gmt":    unpacked[3],
                "odb_clock_std_dev":    unpacked[4:8],
                "odb_clock_rate":       unpacked[8],
                "odb_clock_drift":      unpacked[9],
                "odb_clock_der_drift":  unpacked[10],
                "odb_clock_errtime":    unpacked[11:14],
                "odb_clock_variance":   unpacked[14],
                "odb_clock_majfm_cnt":  unpacked[15],
                "odb_clock_majfm_utc":  unpacked[16],
                "odb_clock_key":        unpacked[17],
                "odb_clock_key_char":   key_char,
                "odb_clock_base_ref":   base_ref
            }
            output_data.append(record)

    return pd.DataFrame(output_data)


def dataframe_to_dis_file(df, init_length, input_filepath, output_filepath):
    HEADER_SIZE = 38
    RECORD_SIZE = 175
    
    # --- 1. EXTRACT ORIGINAL HEADER & CALCULATE NEW SIZES ---
    with open(input_filepath, 'rb') as orig_file:
        orig_header_data = orig_file.read(HEADER_SIZE)
        orig_header_text = orig_header_data.decode('ascii', errors='ignore')
        orig_values = orig_header_text.split()
    
    orig_record_count = int(orig_values[1])
    orig_data_byte_size = int(orig_values[3]) 

    new_record_count = len(df)
    new_data_byte_size = HEADER_SIZE + (new_record_count * RECORD_SIZE)

    # Reconstruct the header safely
    header_str = f"{orig_values[0]:<8}{new_record_count:<5}{orig_values[2]:<6}{new_data_byte_size:<8}{orig_values[4]:<6}{orig_values[5]:<5}"
    header_bytes = header_str.ljust(HEADER_SIZE)[:HEADER_SIZE].encode('ascii')

    # --- 2. WRITE THE EDITED DATA RECORDS ---
    with open(output_filepath, 'wb') as outfile:
        outfile.write(header_bytes)

        for index, row in df.iterrows():
            prefix = b"   169"
            std_dev = row['odb_clock_std_dev']
            errtime = row['odb_clock_errtime']

            payload = struct.pack(
                '<15d i d i',
                row['odb_clock_adj_data_l'], row['odb_clock_adj_data_f'],
                row['odb_clock_ref_cnts'], row['odb_clock_ref_gmt'],
                std_dev[0], std_dev[1], std_dev[2], std_dev[3], 
                row['odb_clock_rate'], row['odb_clock_drift'], row['odb_clock_der_drift'],
                errtime[0], errtime[1], errtime[2],             
                row['odb_clock_variance'], int(row['odb_clock_majfm_cnt']),
                row['odb_clock_majfm_utc'], int(row['odb_clock_key'])
            )

            key_val = row['odb_clock_key_char']
            if pd.isna(key_val) or key_val == 'nan':
                key_val = "C          "
            key_bytes = str(key_val).ljust(11)[:11].encode('ascii')
            time_bytes = str(row['odb_clock_base_ref']).ljust(21)[:21].encode('ascii')
            
            full_record = prefix + payload + key_bytes + time_bytes + b"\x00"
            outfile.write(full_record)

        # --- 3. DYNAMICALLY REBUILD THE INDEX BLOCK ---
        INDEX_ENTRY_SIZE = 20

        # Grab the proprietary prefix from the original file (if it exists) to maintain consistency
        with open(input_filepath, 'rb') as orig_file:
            orig_file.seek(orig_data_byte_size)
            orig_index_blob = orig_file.read(INDEX_ENTRY_SIZE)
            # Use the first 10 bytes as the proprietary binary prefix
            last_proprietary_prefix = orig_index_blob[:-10] if len(orig_index_blob) >= 10 else b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

        for i in range(new_record_count):
            # Calculate physical byte location for record i
            new_offset = HEADER_SIZE + (i * RECORD_SIZE)

            # Format offset as a 10-character right-aligned ASCII string
            offset_bytes = f"{new_offset:>10}".encode('ascii')

            # Write new entry
            outfile.write(last_proprietary_prefix + offset_bytes)

    apply_fresh_padding(output_filepath)
    log_callback(f"Update complete! {new_record_count - init_length} new record(s) appended, total of "
                 f"{new_record_count} records. Saved to {output_filepath.name}")


def dataframe_to_dat_file(df, init_length, output_filepath):
    """
    Writes the dataframe to a new raw binary .DAT file.
    Enforces Big-Endian (>) packing and strictly sequential 170-byte writes.
    """
    record_count = 0

    with open(output_filepath, 'wb') as outfile:
        for index, row in df.iterrows():
            std_dev = row['odb_clock_std_dev']
            errtime = row['odb_clock_errtime']

            # Pack using Big-Endian (>)
            payload = struct.pack(
                '>15d i d i',
                row['odb_clock_adj_data_l'], row['odb_clock_adj_data_f'],
                row['odb_clock_ref_cnts'], row['odb_clock_ref_gmt'],
                std_dev[0], std_dev[1], std_dev[2], std_dev[3], 
                row['odb_clock_rate'], row['odb_clock_drift'], row['odb_clock_der_drift'],
                errtime[0], errtime[1], errtime[2],             
                row['odb_clock_variance'], int(row['odb_clock_majfm_cnt']),
                row['odb_clock_majfm_utc'], int(row['odb_clock_key'])
            )

            key_val = row['odb_clock_key_char']
            if pd.isna(key_val) or key_val == 'nan':
                key_val = "C**********"
            key_bytes = str(key_val).ljust(11)[:11].encode('ascii')
            time_bytes = str(row['odb_clock_base_ref']).ljust(21)[:21].encode('ascii')

            # Pad with a null byte and a newline character to perfectly hit 170 bytes
            full_record = payload + key_bytes + time_bytes + b"\x00\n"
            outfile.write(full_record)
            record_count += 1

    apply_fresh_padding(output_filepath)
    log_callback(f"Update complete! {record_count - init_length} new record(s) appended, total of "
                 f"{record_count} records. Saved to {output_filepath.name}")


def convert_dis_file(nrt_df, input_filepath):
    """
    Read a .DIS file, convert it to a DataFrame, edit it,
    and write it back to a new .DIS file.
    """
    input_path = Path(input_filepath)
    input_filename = input_path.name

    # Increment the file number (assumes format like CLKHST_XXXX.DIS)
    try:
        base_name, ext = input_filename.split('.')
        # Split by underscore and increment the numeric portion
        name_parts = base_name.split('_')
        file_num = int(name_parts[-1])
        output_filename = f"{name_parts[0]}_{file_num + 1}.{ext}"
    except (IndexError, ValueError):
        output_filename = f"NEW_{input_filename}"

    output_filepath = input_path.parent / output_filename

    # 1. Read existing database
    dis_file_data = dis_file_to_dataframe(input_path)
    # dis_file_data.to_csv(Path(f"{input_path.parent}/{input_filename}.csv"), index=False)

    # 2. Format new telemetry data
    append_data = format_for_binary_export(nrt_df)

    # 3. Combine DataFrames
    combined_data = pd.concat([append_data, dis_file_data], ignore_index=True)
    # combined_data.to_csv(Path(f"{output_filepath.parent}/{output_filename}.csv"), index=False)

    # 4. Write new binary file
    dataframe_to_dis_file(combined_data, len(dis_file_data), input_path, output_filepath)


def convert_dat_file(nrt_df, input_filepath):
    """
    Read a .DAT file, convert it to a DataFrame, format new data,
    reverse the append order, and write back to a new .DAT file.
    """
    input_path = Path(input_filepath)
    input_filename = input_path.name

    # Increment the file number (assumes format like CLKHST_XXXX.DAT)
    try:
        base_name, ext = input_filename.split('.')
        name_parts = base_name.split('_')
        file_num = int(name_parts[-1])
        output_filename = f"{name_parts[0]}_{file_num + 1}.{ext}"
    except (IndexError, ValueError):
        output_filename = f"NEW_{input_filename}"

    output_filepath = input_path.parent / output_filename

    # 1. Read existing database
    dat_file_data = dat_file_to_dataframe(input_path)
    # dat_file_data.to_csv(Path(f"{input_path.parent}/{input_filename}.csv"), index=False)

    # 2. Format new telemetry data
    append_data = format_for_binary_export(nrt_df)

    # 3. Combine DataFrames
    combined_data = pd.concat([dat_file_data, append_data], ignore_index=True)
    # combined_data.to_csv(Path(f"{output_filepath.parent}/{output_filename}.csv"), index=False)

    # 4. Write new binary file
    dataframe_to_dat_file(combined_data, len(dat_file_data), output_filepath)
