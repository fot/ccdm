from pathlib import Path
import struct
import pandas as pd
import os  # Added to check file sizes for padding


FILEPATH = Path("C:/Users/RHoover/Desktop")


def dis_file_to_dataframe(filepath):
    # Based on the OP19 Section 3.40 spec and the file's hex dump
    HEADER_SIZE = 38
    RECORD_SIZE = 175
    output_data= []

    with open(FILEPATH / filepath, 'rb') as file:
        # 1. Read the 38-byte ASCII file header
        header_data = file.read(HEADER_SIZE) 
        
        # 2. Extract the total record count dynamically
        try:
            header_text = header_data.decode('ascii', errors='ignore')
            header_values = header_text.split()
            total_records = int(header_values[1])
            print(f"Header dynamically indicates {total_records} valid records.")
        except (ValueError, IndexError):
            print("Could not read record count from header. Defaulting to read all.")
            total_records = float('inf')
            
        record_count = 0
        
        # 3. Loop only for the exact number of valid records
        while record_count < total_records:
            chunk = file.read(RECORD_SIZE)
            if len(chunk) < RECORD_SIZE:
                break

            record_count += 1

            # The ASCII fields at the tail of the record
            key_char= chunk[142:153].decode('ascii', errors='ignore').strip()
            base_ref= chunk[153:174].decode('ascii', errors='ignore').strip()

            # Unpack the binary math
            binary_payload = chunk[6:142] 
            unpacked= struct.unpack('<15d i d i', binary_payload)
            
            # Map everything to the Section 3.40 definitions
            record = {
                "odb_clock_adj_data_l": unpacked[0],
                "odb_clock_adj_data_f": unpacked[1],
                "odb_clock_ref_cnts": unpacked[2],
                "odb_clock_ref_gmt": unpacked[3],
                "odb_clock_std_dev": unpacked[4:8],
                "odb_clock_rate": unpacked[8],
                "odb_clock_drift": unpacked[9],
                "odb_clock_der_drift": unpacked[10],
                "odb_clock_errtime": unpacked[11:14],
                "odb_clock_variance": unpacked[14],
                "odb_clock_majfm_cnt": unpacked[15],
                "odb_clock_majfm_utc": unpacked[16],
                "odb_clock_key": unpacked[17],
                "odb_clock_key_char": key_char,
                "odb_clock_base_ref": base_ref
            }
            output_data.append(record)

    return pd.DataFrame(output_data)


def dataframe_to_dis_file(df, original_filename):
    HEADER_SIZE= 38
    RECORD_SIZE= 175
    output_filename= FILEPATH / f"CLKHST_{int(original_filename[7:11]) + 1}.DIS"
    input(output_filename)
    
    # --- 1. EXTRACT ORIGINAL HEADER & CALCULATE NEW SIZES ---
    with open(FILEPATH / original_filename, 'rb') as orig_file:
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
    with open(FILEPATH / output_filename, 'wb') as outfile:
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
                key_val = "C**********"
            key_bytes = str(key_val).ljust(11)[:11].encode('ascii')
            time_bytes = str(row['odb_clock_base_ref']).ljust(21)[:21].encode('ascii')
            
            full_record = prefix + payload + key_bytes + time_bytes + b"\x00"
            outfile.write(full_record)

        # --- 3. DYNAMICALLY REBUILD THE INDEX BLOCK ---
        INDEX_ENTRY_SIZE = 20
        
        with open(FILEPATH / original_filename, 'rb') as orig_file:
            orig_file.seek(orig_data_byte_size)
            true_index_size = orig_record_count * INDEX_ENTRY_SIZE
            pure_index_blob = orig_file.read(true_index_size)
            
            if new_record_count <= orig_record_count:
                # If rows were removed or stayed the same, slice the index safely
                new_index_blob = pure_index_blob[:new_record_count * INDEX_ENTRY_SIZE]
                outfile.write(new_index_blob)
                
            else:
                # If rows were ADDED, we write the old index, then generate new pointers
                outfile.write(pure_index_blob)
                
                # Grab the 10-byte proprietary binary prefix from the last known entry
                last_proprietary_prefix = pure_index_blob[-INDEX_ENTRY_SIZE : -10]
                
                records_added = new_record_count - orig_record_count
                for i in range(records_added):
                    current_record_index = orig_record_count + i
                    
                    # Calculate the exact physical byte location of the new record
                    new_offset = HEADER_SIZE + (current_record_index * RECORD_SIZE)
                    
                    # Format it as a 10-character right-aligned ASCII string (e.g., "     17013")
                    offset_bytes = f"{new_offset:>10}".encode('ascii')
                    
                    # Combine the binary prefix with the new calculated offset and write
                    new_entry = last_proprietary_prefix + offset_bytes
                    outfile.write(new_entry)

    print(f"Success! Base file written with {new_record_count} records.")
    apply_fresh_padding(FILEPATH / output_filename)


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
        print(f"Added {padding_needed} bytes of fresh padding to align with {block_size}-byte sectors.")


def edit_dataframe(df):

    # 2. Duplicate the last row and append it
    print(f"Original Row Count: {len(df)}")
    df = pd.concat([df, df.tail(1)], ignore_index=True)
    print(f"New Row Count: {len(df)}")
    return df


# ==========================================
# EXECUTION WORKFLOW
# ==========================================

dis_file_data= dis_file_to_dataframe("CLKHST_2136.DIS")
# dis_file_data= edit_dataframe(dis_file_data)
# dataframe_to_dis_file(dis_file_data, "CLKHST_2135.DIS")

dis_file_data.to_csv(FILEPATH / "CLKHST_2136.csv", index= False)
