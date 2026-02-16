"SCS107 Run Detection for use in status_report.py"

import dataclasses
from cxotime import CxoTime
from components.tlm_request import data_request


@dataclasses.dataclass
class SCS107DataPoint:
    "Data class for SCS107 runs"
    start_time: None
    end_time: None


def scs107_detection(user_vars, file):
    "Detect a run of SCS107, then write it to console and report file"
    print(" - SCS107 Detection...")
    data_list= []
    data= data_request(user_vars.ts,user_vars.tp,"SKA High Rate","COSCS107S")
    data_point= SCS107DataPoint(None, None) # Initial data_point

    for index, (value, time) in enumerate(zip(data.vals, data.times)):

        # Populate data_point as SCS107 changes state
        if (value in ("DISA", "ACT")) and (data.vals[index - 1]== "INAC") and (index > 0):
            data_point.start_time= CxoTime(time).yday
        elif (value== "INAC") and (data.vals[index - 1]== "DISA") and (index > 0):
            data_point.end_time= CxoTime(time).yday

        # Append data_list if at last sample w/ partially filled data_point.
        if (index + 1 == len(data.vals) and
              ((data_point.start_time is not None) or (data_point.end_time is not None))):
            data_list.append(data_point)
        # Append data_list if data_point fills, then make a new empty data_point.
        elif (data_point.start_time is not None) and (data_point.end_time is not None):
            data_list.append(data_point)
            data_point= SCS107DataPoint(None, None)
        # Append data_list if an end_time is found before a start_time, make an empty data_point.
        elif (data_point.start_time is None) and (data_point.end_time is not None):
            data_list.append(data_point)
            data_point= SCS107DataPoint(None, None)

    # Write SCS107 runs found
    if data_list:
        for data_item in data_list:
            if (data_item.start_time is not None) and (data_item.end_time is not None):
                print(f"   - Found a run of SCS107 on {data_item.start_time} "
                      f"and was re-enabled on {data_item.end_time}.")
                file.write(f"  - SCS107 ran on {data_item.start_time} "
                           f"and was re-enabled on {data_item.end_time}.\n")
            elif (data_item.start_time is not None) and (data_item.end_time is None):
                print(f"   - Found a run of SCS107 on {data_item.start_time}.")
                file.write(f"  - SCS107 ran on {data_item.start_time} "
                           "and hasn't been re-enabled yet.\n")
            elif (data_item.start_time is None) and (data_item.end_time is not None):
                print("   - Found a previous run of SCS 107 out of input range.")
                file.write(f"  - SCS107 prevously ran on a time outside of input "
                        f"range and was re-enabled on {data_item.end_time}.\n")
    else:
        print("   - No run of SCS107 detected.")
        file.write("  - No run of SCS107 detected.\n")
