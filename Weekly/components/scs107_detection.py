"SCS 107 Detection for CCDM Weekly"

import dataclasses
from cxotime import CxoTime
from components.data_requests import ska_data_request as ska_data

@dataclasses.dataclass
class SCS107DataPoint:
    "Data class for SCS107 runs"
    start_time: None
    end_time: None


def scs107_detection(user_vars):
    "Base method for SCS107 Detection"
    print("SCS 107 Detection...")
    scs107s = get_scs107s(user_vars)
    scs107s_string = gen_scs107s_string(scs107s)
    return scs107s_string if scs107s_string else None


def get_scs107s(user_vars):
    "Detect a run of SCS107, then write it to console and return data"
    data_list= []
    data= ska_data(user_vars.ts,user_vars.tp, "COSCS107S", True)
    data_point= SCS107DataPoint(None, None) # Initial data_point

    for index, (value, time) in enumerate(zip(data.vals, data.times)):
        # Populate data_point as SCS107 changes state
        if (value in ("DISA", "ACT")) and (data.vals[index - 1]== "INAC") and (index > 0):
            data_point.start_time= CxoTime(time).yday
        elif (value== "INAC") and (data.vals[index - 1]== "DISA") and (index > 0):
            data_point.end_time= CxoTime(time).yday

        # Append data_list if at last sample w/ partially filled data_point.
        elif (index + 1 == len(data.vals) and
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

    return data_list


def gen_scs107s_string(scs107s):
    "Write SCS107 runs found"
    if scs107s:
        return_string = ""
        for data_item in scs107s:
            if (data_item.start_time is not None) and (data_item.end_time is not None):
                print(f"   - Found a run of SCS107 on {data_item.start_time} "
                      f"and was re-enabled on {data_item.end_time}.")
                return_string += (f"<li>SCS107 ran on {data_item.start_time} "
                                 f"and was re-enabled on {data_item.end_time}.</li>\n")
            elif (data_item.start_time is not None) and (data_item.end_time is None):
                print(f"   - Found a run of SCS107 on {data_item.start_time}.")
                return_string += (f"<li>SCS107 ran on {data_item.start_time} "
                                 "and hasn't been re-enabled yet.</li>\n")
            elif (data_item.start_time is None) and (data_item.end_time is not None):
                print("   - Found a previous run of SCS 107 out of date range.")
                return_string = (f"<li>SCS107 prevously ran on a time outside of date "
                                 f"range and was re-enabled on {data_item.end_time}.</li>\n")
    else:
        return_string = None
        print("   - No run of SCS107 detected.")

    return return_string if return_string else None
