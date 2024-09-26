"Misc Data Methods for MSID Plotter Tool"

import json
import urllib.request
from Ska.engarchive import fetch_eng as fetch


def check_msid_validity(msid_input):
    """
    Description: Check if an MSID is valid. Do a mini MAUDE url request on MSID.
    Input: MSID
    Output: True/False
    """
    url = (
        f"https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/"
        f"msid.json?m={msid_input}&ts=2024:001:00:00:00.000&tp=2024:001:00:00:05.000"
    )
    try:
        urllib.request.urlopen(url)
        return True
    except BaseException:
        return False


def data_request(user_vars,msid):
    """
    Description: Data request for a general timeframe and MSID, returns json or data dict
    Input: User Variables, MSID
    Output: Data dict or JSON
    """
    print(f"  - Requesting {user_vars.data_source} data for {msid}...")
    user_vars.ts.format = "yday"
    user_vars.tp.format = "yday"
    base_url = "https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m="

    if user_vars.data_source in ("High Rate SKA","Abbreviated SKA"):
        fetch.data_source.set("maude")
        if user_vars.data_source in ("High Rate SKA"):
            fetch.data_source.set("maude allow_subset=False")
        else:
            fetch.data_source.set("maude allow_subset=True")
        data = fetch.MSID(f"{msid}",user_vars.ts,user_vars.tp)
    else:
        url = base_url + msid + "&ts=" +str(user_vars.ts.value) + "&tp=" + str(user_vars.tp.value)
        response = urllib.request.urlopen(url)
        html = response.read()

    return data if not user_vars.data_source in ("MAUDE Web") else json.loads(html)
