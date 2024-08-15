"Telemetry Request Methods for Daily Plots Tools"

import json
import urllib
from Ska.engarchive import fetch_eng as fetch


def data_request(user_vars,msid):
    """
    Description: Request ska_eng archive for telemetry
    Input: User defined variables, MSID
    Output: dict or JSON of data
    """
    user_vars.ts.format = "yday"
    user_vars.tp.format = "yday"
    base_url = "https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m="

    if user_vars.data_source in ("SKA High Rate", "SKA Abreviated"):
        fetch.data_source.set("maude")
        if user_vars.data_source == "SKA High Rate":
            fetch.data_source.set("maude allow_subset=False")
        else:
            fetch.data_source.set("maude allow_subset=True")
        data = fetch.MSID(f"{msid}",user_vars.ts,user_vars.tp)
    else:
        url = base_url + msid + "&ts=" +str(user_vars.ts.value) + "&tp=" + str(user_vars.tp.value)
        response = urllib.request.urlopen(url)
        html = response.read()

    return data if not user_vars.data_source in ("MAUDE Web") else json.loads(html)
