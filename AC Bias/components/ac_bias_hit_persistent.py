"AC Bias HIT Persistent Tracker Tool"

import os
os.environ['SKA'] = '/proj/sot/ska3/flight'
os.environ['ENG_ARCHIVE'] = '/proj/sot/ska3/flight/data/eng_archive'

import urllib.request
import json
import numpy as np
from cxotime import CxoTime
from datetime import timedelta
from datetime import datetime
from datetime import timezone
from cheta import fetch_eng
import plotly.io as pio
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import shutil
import time


def MAUDERequestLast(MSID):
    """ Requests the last value for a particular MSID for an interval"""
    base_url = 'https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m='
    url = base_url + MSID
    response = urllib.request.urlopen(url)
    html = response.read()
    return json.loads(html)


def MAUDERequest(ts,tp,MSID):
    """ Requests a particular MSID for an interval"""
    #sanitize timeformats
    ts.format = 'yday'
    tp.format = 'yday'
    base_url = 'https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m='
    url = base_url + MSID + '&ts=' +str(ts) + '&tp=' + str(tp)
    response = urllib.request.urlopen(url)
    html = response.read()
    return json.loads(html)


def jsontime2cxo(time_in):
    # sanitize input
    time_str = str(time_in)
    return CxoTime(time_str[0:4]+ ':' +time_str[4:7]+':' +time_str[7:9]+':' +time_str[9:11]+':' +time_str[11:13]+'.' +time_str[13:])


def getLastPBTime(m_ret):
    """ From m_ret MAUDERequest return value, extract the last playback time. Return None if no playbacks """
    vals = m_ret['data-fmt-1']['values']
    times = m_ret['data-fmt-1']['times']
    if '0' in vals:
        idx = ''.join(vals).rindex('0')
        time_PB = jsontime2cxo(str(times[idx]))
        #time_str = str(times[idx])
        #time_str_dl = time_str[0:4]+ ':' +time_str[4:7]+':' +time_str[7:9]+':' +time_str[9:11]+':' +time_str[11:13]+'.' +time_str[13:]
        return time_PB
    else:
        return None


def getLastPB(ts,tp):
    """ returns last playback within the given timer interval from ts to tp, else None"""
    ssr_a = getLastPBTime(MAUDERequest(ts,tp,'TR_COSAPBEN'))
    ssr_b = getLastPBTime( MAUDERequest(ts,tp,'TR_COSBPBEN'))
    if ssr_a  is None:
        if ssr_b is None:
            print('ERR: no playbacks present')
            return None
        else:                    # A is None, B has a value
            if ssr_b  > ts:
                return ('B', ssr_b)
            else: 
                return None
    else:
        if ssr_b is None: # A has val, B is None
            if ssr_a  > ts:
                return ('A', ssr_a)
            else: 
                return None
        else:  # both have values
            if ssr_a > ssr_b:
                if ssr_a  > ts:
                    return ('A', ssr_a)
                else: 
                    return None
            else:
                if ssr_b  > ts:
                    return ('B', ssr_b)
                else: 
                    return None


def getACISBiastimes(ts,tp):
    """ returns lists of start and stop times for ACIS Bias packets """
    #base_url = 'https://occweb.cfa.harvard.edu/occweb/web/webapps/ifot/ifot.php?r=home&t=qserver&a=show&format=list&columns=tstart,tstop,properties&size=auto&e=BIAS.&tstart='
    base_url = 'https://occweb.cfa.harvard.edu/occweb/web/webapps/ifot/ifot.php?r=home&t=qserver&a=show&format=list&columns=tstart,tstop,properties,duration,type_desc&size=auto&e=OBS.MODE,BIAS.&tstart='
    url  = base_url+str(ts)+'&tstop='+str(tp) +'&ul=6'    
    response = urllib.request.urlopen(url)
    html = response.read()
    return html


def genRTheta(addr_start,addr_stop,addr_max,r,n):
    r_list = []
    if addr_stop < addr_start:      # unwrap around crossover
        addr_stop += addr_max        
    theta_interp = np.linspace(360* addr_start/addr_max, 360* addr_stop/addr_max,n)
    theta_interp = np.insert(theta_interp,0,theta_interp[0])
    theta_interp = np.append(theta_interp,theta_interp[-1])
    r_list = r[0]*np.ones_like(theta_interp)
    r_list[1:-1] = r[1]
    r_list = np.concatenate((r_list,r[0]*np.ones_like(r_list)))
    theta_interp = np.concatenate((theta_interp,np.flip(theta_interp)))
    return r_list,theta_interp
               # wraparound, go the other way


def genRThetaSingle(addr,addr_max,r):    
    th = [360*addr/addr_max]*len(r)
    return r,th


def ptr2addr(t,ref):
    """ Given a reference time/address, return the expected address at time t for the default record rate of 2kwords/sec
        ref = tuple (rec_t,rec_ptr)
    """
    rec_rate = 2000  # words/sec = 32000 bits/sec
    addr_max  = 134217696
    cur_addr = ref[1]
    if t > ref[0]: # the normal case reference was some time ago        
        td = t-ref[0]
        addr_delta =  td.to_value('sec')*rec_rate       
        new_addr = (cur_addr + addr_delta ) % addr_max
    else:
        td = ref[0] -t
        addr_delta =  td.to_value('sec')*rec_rate
        new_addr = (cur_addr - addr_delta ) % addr_max
    return new_addr


def ptr2time(addr,ref,sign=1):
    """ Given a reference time/address, return the expected time at address addr for the default record rate of 2kwords/sec
        ref = tuple (rec_t,rec_ptr)
        **NOTE** by default This function assumes ADDR occurs AFTER REF_ADDR.  No way a priori to tell which comes first.
        e.g given the reference record pointer/time, this function would return the time when the clockwise moving record  pointer would
        advance to addr at the record rate of 2000 words/sec
    """
    rec_rate = 2000  # words/sec = 32000 bits/sec
    addr_max  = 134217696
    addr_delta = (sign*(addr - ref[1])) % addr_max  
    time_delta_secs =timedelta(seconds=addr_delta/rec_rate) # assumes that addr occurs at a time LATER than ref_addr.
    time_out = ref[0] + sign*time_delta_secs
    return time_out


def getACISBiasAddr(ts,tp,ssr):
    """ Returns Record Pointer Addresses and SSR in use as a list of lists for the ACIS bias times since the last playback
        Inputs:
            ts- Start of time window to search over, typically 24-48 hours before present.  Should be greater than largest gap in comm
            tp- End of window to search over - typically ~ 2 hours before present
            ssr- user says which ssr should be active when looking for pointers
    """
    t = datetime.now(timezone.utc)   # Get UTC Timezone value of current time
    cur_time  = CxoTime(t)
    cur_time.format = 'yday'
    last_pb = getLastPB(ts,tp)
    #ACIS_raw = getACISBiastimes(last_pb[1],cur_time) # go from last playback to last playback + 18 hours
    ACIS_raw = getACISBiastimes(last_pb[1],last_pb[1]+timedelta(seconds=60*60*24)) # go from last playback to last playback + 24 hours
    df_list = pd.read_html(ACIS_raw) # grab table from returned iFOT data
    df = df_list[-1]
    acis_bias_rng = []
    #traverse array in reverse and populate obs type column of bias packets
    ## populate rows with associated observation (if any)
    cur_type = 'UNK'
    for row in df.iloc[::-1].iterrows():
        if row[1][3] == 'Observation':
            cur_type = row[1][4]
        else:
            df.iloc[row[0],4] = cur_type
    # Grab the rows that are just the bias packets and annotate them
    bias_df = df[df[3]=='ACIS BIAS Packet'].copy(deep=True)   
    #Initialize columns
    bias_df[5] = '' * len(bias_df[0])
    bias_df[6] = '' * len(bias_df[0])
    for row in bias_df.iterrows():
        row[1][0] = CxoTime(row[1][0])
        row[1][1] = CxoTime(row[1][1])
        tmp = list(map(float,row[1][2].split(':')))
        dur_secs = tmp[0]*86400 + tmp[1]*3600 + tmp[2]*60 +tmp[3]
        row[1][2] = timedelta(seconds=dur_secs)        
        if row[1][4].startswith("TE"):
            if row[1][2] > timedelta(seconds=24*60): # TE Long
                row[1][5] = "TE_LONG"
            else:
                row[1][5] = "TE_SHORT"
        elif row[1][4].startswith("CC"):
            row[1][5] = "CC"
        else:
            row[1][5] = "UNK"            
    time_thr = last_pb[1]+timedelta(seconds=60*60*18)
    for row in bias_df.iterrows():  # NOW DROP ROWS WHO START > 18 HOURS PAST LAST PLAYBACK
        if row[1][0] > time_thr:
            row[1][5] = None
    bias_df.dropna(axis=0,how='any',subset=None,inplace=True)

    #Get Reference Pointer, e.g. Record pointer val at last pb time
    rcpt = MAUDERequest(last_pb[1],last_pb[1] +timedelta(seconds=63),'COS'+ssr+'RCPT')
    ref_rcpt_val = int(rcpt['data-fmt-1']['values'][0])
    ref_rcpt_time = jsontime2cxo(str(rcpt['data-fmt-1']['times'][0]))    
    # Now for each time in each  ACIS Bias Range, convert to address values using the record pointer
    for row in bias_df.iterrows():
        # For each acis range, calculate the corresponding address pointers
        # and the corresponding record pointer.  
        # **NOTE** Doesn't handle rollovers during an acis packet     
        # output row is [ acis_ts,addr_ts,acis_tp,addr_tp,OBS_STR,OBS_TYPE, concern_addr_list, concern_time_list ]
        acis_ts = CxoTime(row[1][0])
        acis_tp = CxoTime(row[1][1])
        addr_ts =ptr2addr(acis_ts,(ref_rcpt_time,ref_rcpt_val))
        addr_tp =ptr2addr(acis_tp,(ref_rcpt_time,ref_rcpt_val))
        # now calculate concern times in address space....
        concern = []
        concern_time = []
        if row[1][5] == 'TE_SHORT':
            concern.append([ptr2addr(acis_ts + timedelta(seconds=60),[ref_rcpt_time,ref_rcpt_val]),ptr2addr(acis_ts + timedelta(seconds=120),[ref_rcpt_time,ref_rcpt_val])])  # concenrn period 1
            concern_time.append([acis_ts + timedelta(seconds=60),acis_ts + timedelta(seconds=120)])
            d_acis = acis_tp - acis_ts            
            concern.append([ptr2addr(acis_ts + d_acis/2,[ref_rcpt_time,ref_rcpt_val]),ptr2addr(acis_tp + timedelta(seconds=120),[ref_rcpt_time,ref_rcpt_val])])  # concenrn period 2
            concern_time.append([acis_ts + d_acis/2,acis_tp + timedelta(seconds=120)])
        elif row[1][5] == 'TE_LONG':
            concern.append([ptr2addr(acis_ts + timedelta(seconds=60),[ref_rcpt_time,ref_rcpt_val]),ptr2addr(acis_ts + timedelta(seconds=120),[ref_rcpt_time,ref_rcpt_val])])  # concenrn period 1
            concern_time.append([acis_ts + timedelta(seconds=60),acis_ts + timedelta(seconds=120)])
            concern.append([ptr2addr(acis_ts + timedelta(seconds=12*60),[ref_rcpt_time,ref_rcpt_val]),ptr2addr(acis_tp + timedelta(seconds=4*60),[ref_rcpt_time,ref_rcpt_val])])  # concenrn period 2
            concern_time.append([acis_ts + timedelta(seconds=12*60),acis_tp + timedelta(seconds=4*60)])
        elif row[1][5] == 'CC':
            concern.append([ptr2addr(acis_ts + timedelta(seconds=60),[ref_rcpt_time,ref_rcpt_val]),ptr2addr(acis_tp + timedelta(seconds=536),[ref_rcpt_time,ref_rcpt_val])])  # concenrn period 1
            concern_time.append([acis_ts + timedelta(seconds=60),acis_tp + timedelta(seconds=536)])
        # output row is [ acis_ts,addr_ts,acis_tp,addr_tp,OBS_STR,OBS_TYPE, concern_addr_list, concern_time_list ]
        row_out = [ acis_ts,addr_ts,acis_tp,addr_tp,row[1][4],row[1][5],concern,concern_time  ]
        acis_bias_rng.append(row_out) # Grab the record pointers at begin 
    return acis_bias_rng


def CreateTable(ssr_sel,ac_bias):
    #ssr_sel = 'B'
    #ac_bias = getACISBiasAddr(ts,tp, ssr_sel)
    # output row is [ acis_ts,addr_ts,acis_tp,addr_tp,OBS_STR,OBS_TYPE, concern_addr_list, concern_time_list ]
    #reformat ac_bias times as a table
    ac_times = []
    ac_addr = []
    ac_obs = []
    ac_type = []

    for bias in ac_bias:
        ac_times.append(bias[0])  # ts
        ac_addr.append(bias[1])   # addr_ts
        ac_obs.append(bias[4] ) # OBS_ID - TYPE
        ac_type.append('AC Bias Start - ' + bias[5] ) # OBS_ID 
        ac_times.append(bias[2])  # tp
        ac_addr.append(bias[3])  # tp
        ac_obs.append(bias[4] ) # OBS_ID 
        ac_type.append('AC Bias Stop - ' + bias[5] ) # TYPE
        con_idx = 1
        for con_addr,con_t in zip(bias[6],bias[7]): # concern time list
            ac_times.append(con_t[0])  # ts
            ac_addr.append(con_addr[0])
            ac_obs.append(bias[4] ) # OBS_ID
            ac_type.append('CON# ' +str(con_idx)+' - Start') # OBS_ID - TYPE
            ac_times.append(con_t[1])  # ts
            ac_addr.append(con_addr[1])
            ac_obs.append(bias[4] ) # OBS_ID
            ac_type.append('CON# ' +str(con_idx)+' - Stop') # OBS_ID - TYPE
            con_idx += 1
    # start by adding current playback pointer and converting address to record time.  
    #  1. Get last record address/ Time  as reference
    #  2. Assume PB_ptr time is AFTER (>)  ref_time
    #  3. PB_ptr_time = ref_time + (PB_ptr_addr -  ref_addr)/rec_rate
    # Reference window... 24 hours (should be sufficient to have a pass)


    # put AC Bias times into a list 

    # last record pointer
    t = datetime.now(timezone.utc)   # Get UTC Timezone value of current time
    cur_time  = CxoTime(t)
    t_win = 24*3600 # seconds
    cur_ts = cur_time - timedelta(seconds=t_win)
    #ref_rcpt = MAUDERequest(cur_ts,cur_time,'COS'+ssr_sel+'RCPT')
    ref_rcpt = MAUDERequestLast('COS'+ssr_sel+'RCPT')
    ref_rcpt_val = int(ref_rcpt['data-fmt-1']['values'][-1])
    ref_rcpt_time = jsontime2cxo(ref_rcpt['data-fmt-1']['times'][-1])

    #  determine what spacecraft time is currently being played back
    #pbpt = MAUDERequest(cur_ts,cur_time,'COSBPBPT')
    pbpt = MAUDERequestLast('COS'+ssr_sel+'PBPT')
    pbpt_val = int(pbpt['data-fmt-1']['values'][-1])
    pbpt_rec_time = ptr2time(pbpt_val,(ref_rcpt_time,ref_rcpt_val),-1)

    # add playback pointer row
    ac_times.append(pbpt_rec_time)
    ac_type.append('PB POINTER')
    ac_addr.append(pbpt_val)
    ac_obs.append('LATEST PB')

    ac_table = {}
    ac_table['type'] = ac_type
    ac_table['times'] = ac_times
    ac_table['addr'] = map(np.floor,ac_addr)
    ac_table['obs'] = ac_obs
    # insert colors based on PB Pointer field.  Will need to do the same for AC_BIAS hits
    colors = ['lightgray']*len(ac_obs) 
    tmp = ac_table_pd.index[ac_table_pd['type']=='PB POINTER']
    print(tmp.values[0])
    print(colors[12])
    colors[tmp.values[0]] = 'darkgray'
    ac_table['colors'] = colors
    ac_table_pd = pd.DataFrame.from_dict(ac_table)
    print(ac_table_pd.sort_values('times'))
    ac_sort = ac_table_pd.sort_values('times')

    fig = go.Figure(data=[go.Table(
        header=dict(
        values=["Type", "<b>Times</b>", "<b>ADDR</b>", "<b>OBS</b>"],
        line_color='white', fill_color='white',
        align='center', font=dict(color='black', size=14)
        ),
        cells=dict(
        values=[ac_sort.type, list(map(str,ac_sort.times)),ac_sort.addr,ac_sort.obs],
        fill_color=[ac_sort.colors],
        align='center', font=dict(color='black', size=12)
        ))
    ])
    return fig


def DrawBias(cur_time,ssr_sel,hrs_prev,pben_val,pb,pb_time,bcw_list,ac_bias,base_dir):
    "Working on it"
    td = timedelta(seconds=3600*24)  #seconds.  Enough time to cover major frame
    cur_ts = cur_time-td
    addr_max  = 134217696

    #In thoery,  only need to update AC_BIAS at the start of a playback

    #rcpt = MAUDERequest(cur_ts,cur_time,'COS'+ssr_sel+'RCPT')
    rcpt = MAUDERequestLast('COS'+ssr_sel+'RCPT')
    rc = int(rcpt['data-fmt-1']['values'][-1])
    rc_time = jsontime2cxo(rcpt['data-fmt-1']['times'][-1])

    # playback time remaining... Need to get bit-rate CIUMBITR
    #br = MAUDERequest(cur_ts,cur_time,'CIUMBITR')
    br = MAUDERequestLast('CIUMBITR')
    br_val = int(br['data-fmt-1']['values'][-1])
    if br_val == 0:
        bit_rate = 2000 # bits/sec
    else:
        bit_rate = 2**(br_val+4) *1000 # bits/sec

    pb_rem_min = 16*((rc - pb) % addr_max) / (bit_rate *60) # minutes of playback (16-bit words)
    #use this to display minutes of recorded data
    #pb_rem_min = ((rc - pb) % addr_max) / (2000 *60) # minutesof recorded data 
    tickrange = np.linspace(0,addr_max/1000000 -addr_max/8000000 ,8)
    tickrange_str =['%.2f' % x for x in tickrange]
    tickvals = np.arange(0,360,45)
    ## Render Figure
    
    fig = make_subplots(rows=1, cols=2,specs=[[{"type": "table"}, {"type": "polar"}]])
    #fig = go.Figure()# should render this conditionally when a playback is active
    r, th = genRTheta(1e-6 * pb, 1e-6 *rc,1e-6 *addr_max,[0,1.5],16)
    if pben_val == 1:
        fig.add_trace(go.Scatterpolar(
                r = r,
                theta = th,
                mode = 'lines',
                name = f"Playback Remaining: {pb_rem_min:.1f} min",  
                showlegend=False,      
                line_color = 'darkseagreen',
                line_width = .25
            ),row=1,col=2)
    pb_r,pb_th = genRThetaSingle(pb,addr_max,[0,1,2])
    rc_r,rc_th = genRThetaSingle(rc,addr_max,[0,1,2])
    pb_str =  f"Playing Back {str(ptr2time(pb,[rc_time,rc],-1))}"
    rec_str = f"Recording    {str(rc_time)}"

    ## Construct Table
    ac_times = []
    ac_addr = []
    ac_obs = []
    ac_type = []

    for bias in ac_bias:
        ac_times.append(bias[0])  # ts
        ac_addr.append(bias[1])   # addr_ts
        ac_obs.append(bias[4] ) # OBS_ID - TYPE
        ac_type.append('AC Bias Start - ' + bias[5] ) # OBS_ID 
        ac_times.append(bias[2])  # tp
        ac_addr.append(bias[3])  # tp
        ac_obs.append(bias[4] ) # OBS_ID 
        ac_type.append('AC Bias Stop - ' + bias[5] ) # TYPE
        con_idx = 1
        for con_addr,con_t in zip(bias[6],bias[7]): # concern time list
            ac_times.append(con_t[0])  # ts
            ac_addr.append(con_addr[0])
            ac_obs.append(bias[4] ) # OBS_ID
            ac_type.append('CON# ' +str(con_idx)+' - Start') # OBS_ID - TYPE
            ac_times.append(con_t[1])  # ts
            ac_addr.append(con_addr[1])
            ac_obs.append(bias[4] ) # OBS_ID
            ac_type.append('CON# ' +str(con_idx)+' - Stop') # OBS_ID - TYPE
            con_idx += 1

    pbpt_rec_time = ptr2time(pb,(rc_time,rc),-1)
    # add playback pointer row
    ac_times.append(pbpt_rec_time)
    ac_type.append('PB POINTER')
    ac_addr.append(pb)
    ac_obs.append('LATEST PB')
    # Update Table Display
    for bcw in bcw_list:
        bcw_rec_time = ptr2time(bcw[0],(rc_time,rc),-1)
        ac_times.append(bcw_rec_time)
        ac_type.append('BCW')
        ac_addr.append(bcw[0])
        ac_obs.append('')

    ac_table = {}
    ac_table['type'] = ac_type
    ac_table['times'] = ac_times
    ac_table['addr'] = map(np.floor,ac_addr)
    ac_table['obs'] = ac_obs
    # insert colors based on PB Pointer field.  Will need to do the same for AC_BIAS hits
    colors = ['lightgray']*len(ac_obs) 
    ac_table['colors'] = colors
    ac_table_pd = pd.DataFrame.from_dict(ac_table)
    tmp = ac_table_pd.index[ac_table_pd['type']=='PB POINTER']
    colors[tmp.values[0]] = 'darkgray'
    tmp = ac_table_pd.index[ac_table_pd['times'] < pbpt_rec_time]  # after PB pointer passes change color
    if len(tmp) >0:
        for idx in tmp.values:
            colors[idx] = 'white'
    if len(bcw_list) > 0 :
        tmp = ac_table_pd.index[ac_table_pd['type']=='BCW']
        for idx in tmp.values:
            colors[idx] = 'coral'
    ac_table_pd['colors'] = colors
    ac_sort = ac_table_pd.sort_values('times')
    

    for bcw in bcw_list: # update Polar Display
        bcw_r, bcw_th = genRThetaSingle(bcw[0],addr_max,[0,1,2])
        bcw_str = f"BCW Time: {str(bcw[1])}"
        fig.add_trace(go.Scatterpolar(
            r = bcw_r,
            theta = bcw_th,
            mode = 'lines+markers',
            hoverinfo= 'text',
            hovertext=  bcw_str,
            #hovertemplate= 'PB Ptr',
            name =bcw_str,        
            line_color = 'red',       
            line_width = 2,
            line=dict(dash='dash')
        ),row=1,col=2)


    fig.add_trace(go.Scatterpolar(
            r = pb_r,
            theta = pb_th,
            mode = 'lines+markers',
            hoverinfo= 'text',
            hovertext=  pb_str,
            #hovertemplate= 'PB Ptr',
            name =pb_str,        
            line_color = 'darkgreen',       
            line_width = 2,
            line=dict(dash='dot')
        ),row=1,col=2)
    fig.add_trace(go.Scatterpolar(
            r = rc_r,
            theta = rc_th,
            mode = 'lines+markers',
            hoverinfo= 'text',
            hovertext= rec_str,
            name = rec_str,             
            line_color = 'Black',
            line_width = 2,
            line=dict(dash='dot')
        ),row=1,col=2)


    for bias in ac_bias:
        ## AC Bias time
        r, th = genRTheta(1e-6 * int(bias[1]), 1e-6 *int(bias[3]),1e-6 *addr_max,[1.75, 2],16)
        dur = (bias[2] - bias[0])
        fig.add_trace(go.Scatterpolar(
            r = r,
            theta = th,
            mode = 'lines',
            #name = bias[4] + ' - '+ bias[5],  
            name = f"{bias[4]}= {dur.sec/60:.1f} min<br>{str(bias[0])}<br>{str(bias[2])}",
            line_color = 'coral',
            line_width = .25
        ),row=1,col=2)
    
        r_con = 1.5
        concern = 1
        con_color = 'orange'
        for con_time in bias[6]:
            r, th = genRTheta(1e-6 * int(con_time[0]), 1e-6 *int(con_time[1]),1e-6 *addr_max,[r_con,r_con+.25],16)
            fig.add_trace(go.Scatterpolar(
                r = r,
                theta = th,
                mode = 'lines',
                name = f"{bias[4]} Con#{concern}",        
                line_color = con_color,
                line_width = .5,
                showlegend=False    
            ),row=1,col=2)
            concern += 1
    fig.update_traces(fill='toself')

    # render table       

    fig.add_trace(go.Table(
    header=dict(
        values=["Type", "<b>Times</b>", "<b>ADDR</b>", "<b>OBS</b>"],
        line_color='white', fill_color='white',
        align='center', font=dict(color='black', size=14)
    ),
    cells=dict(
        values=[ac_sort.type, list(map(str,ac_sort.times)),ac_sort.addr,ac_sort.obs],
        fill_color=[ac_sort.colors],
        align='center', font=dict(color='black', size=12)
    )),row=1,col=1)        

    fig.add_annotation(text=f"<b>SSR-{ssr_sel} Pointer Locations and AC Bias Times</b><br>Current Time    : {cur_time}<br>Last TLM Update : {pb_time}<br>SSR-{ssr_sel} PBEN      : {pben_val}<br>Playback Remain : {pb_rem_min:.2f} min<br>Playback Rate   : {bit_rate/1000:.1f} kbps",
                    xref="paper", yref="paper",
                    x=0.586, y=1.077, showarrow=False,align="left",bordercolor="black",borderwidth=2,borderpad=4,bgcolor="white",opacity=0.8, font= dict(family= 'Courier New, monospace', size=12))

    fig.update_layout(
        template=None,
        hovermode='y unified',
        font_family="Courier New",
        #title=f"SSR-{ssr_sel} Pointer Locations and AC Bias Times",
        polar = dict(
            radialaxis = dict(showticklabels=False, ticks=''),
            angularaxis = dict(showticklabels=False, tickmode='array', tickvals=tickvals,ticktext=tickrange_str,direction='clockwise')
        )
    )
    #fig.write_html('ACBIAS_example.html', auto_open=False)
    #fig.write_html('ACBIAS_example2.html', auto_open=False,include_plotlyjs='directory')
    try:
        fig.write_html(f"{base_dir}/ACBIAS_example.html",include_plotlyjs = "directory", auto_open = False)
    except Exception  as error:
        print(f"NETWORK WRITE ERROR ({error})")
    return ac_sort, fig


def get_pid():
    "get the PID id for this script when its ran, then save it to a txt file"
    pid = os.getpid()
    base_dir = "/share/FOT/engineering/ccdm/Tools/AC_BIAS/Output"

    with open(f"{base_dir}/pid.txt", "w", encoding="utf-8") as file:
        file.write(f"{pid}")
        file.close()


def main(cur_time, ts):
    "Working on it"
    get_pid()
    [selected_SSR, _] = getLastPB(ts,cur_time)
    base_dir = "/share/FOT/engineering/ccdm/Tools/AC_BIAS/Output"
    ssr_sel = selected_SSR
    hrs_prev = 24 # Window to look back over
    # initialization
    bcw_list = []
    pben_old = float('Inf')
    M1466_old = float('Inf')
    M1966_old = float('Inf')
    #t = datetime(2020, 11, 25, hour=1, minute=32, second=0, microsecond=0, tzinfo=timezone.utc)  # DEBUG visualize old playback
    t = datetime.now(timezone.utc)                  # LIVE DISPLAY
    cur_time  = CxoTime(t)
    print(cur_time)
    cur_time.format = 'yday'
    td = timedelta(seconds=3600*24)  #seconds.  Enough time to cover major frame
    cur_ts = cur_time-td
    # cur_time_old = cur_time-timedelta(seconds=60)
    print(cur_ts)
    print(cur_time)
    #pbpt = MAUDERequest(cur_ts,cur_time,'COS'+ssr_sel+'PBPT')
    pbpt = MAUDERequestLast('COS'+ssr_sel+'PBPT')
    pb = int(pbpt['data-fmt-1']['values'][-1])
    pb_time = jsontime2cxo(pbpt['data-fmt-1']['times'][-1])
    pben_val = 0
    loop_cnt = 500
    # initialize ac-bias fetch
    ac_bias = getACISBiasAddr(cur_ts,cur_time, ssr_sel)

    while True: # LIVE DISPLAY Continuous run
        # try:
        cur_time  = CxoTime(datetime.now(timezone.utc)  )
        cur_time.format = 'yday'
        print(cur_time)
        # Get latest M1466, M1966 and PBEN
        #pbpt = MAUDERequest(cur_ts,cur_time,'COS'+ssr_sel+'PBPT')
        pbpt = MAUDERequestLast('COS'+ssr_sel+'PBPT')
        pb = int(pbpt['data-fmt-1']['values'][-1])
        pb_time = jsontime2cxo(pbpt['data-fmt-1']['times'][-1])
        #pben = MAUDERequest(cur_time_old,cur_time,'COS'+ssr_sel+'PBEN')
        pben = MAUDERequestLast('COS'+ssr_sel+'PBEN')
        if len(pben['data-fmt-1']['values']) >0 :
            pben_val = int(pben['data-fmt-1']['values'][-1])
        else:
            pben_val = pben_val # TBD: remove.  This is old-school VHDL style assignment for comepleteness, 
        #M1466 = MAUDERequest(cur_time_old-timedelta(seconds=10),cur_time,'M1466') # do we have an increment? -- look for increment with a little buffer time
        M1466 = MAUDERequestLast('M1466') # do we have an increment? -- look for increment with a little buffer time
        # for now, just time stamp as current PB pointer (rough)
        if len(M1466['data-fmt-1']['values']) > 0 :
            M1466_val = int(M1466['data-fmt-1']['values'][-1])
            if  (M1466_val > M1466_old) & (pben_val==1):  # we have a hit, find the precise time of change
                bcw_list.append([pb,pb_time])
                #        vals = list(map(int,M1466['data-fmt-1']['values'])) # future exact time determination
                #        val_diff = np.diff(vals,prepend=M1466_old)
                #        val_idx = np.where(val_diff>0)
        else:
            M1466_val = M1466_old # no data, just push forward
        #M1966 = MAUDERequest(cur_time_old,cur_time,'M1966')
        M1966 = MAUDERequestLast('M1966')
        if len(M1966['data-fmt-1']['values']) >0 :
            M1966_val = int(M1966['data-fmt-1']['values'][-1])
            if M1966_val > M1966_old:  # we have a hit, find the precise time of change
                bcw_list.append([pb,pb_time])
        else:
            M1966_val = M1966_old
        # Now Draw the chart
        ac_sort, ac_fig = DrawBias(cur_time,ssr_sel,hrs_prev,pben_val,pb,pb_time,bcw_list,ac_bias,base_dir)
        if (pben_val == 0) & (pben_old == 1): # playback ended reset, the bcw list (and eventually output)
            ac_fig.update_layout(autosize=False,width=2000,height=1000)
            try:
                ac_sort.to_csv(f"{base_dir}/ACBIAS_BCW_{cur_time.strftime('%Y%j_%H%M%S')}.csv")
                ac_fig.write_image(f"{base_dir}/ACBIAS_BCW_{cur_time.strftime('%Y%j_%H%M%S')}.png", engine = "kaleido")
                ac_fig.write_html(f"{base_dir}/ACBIAS_BCW_{cur_time.strftime('%Y%j_%H%M%S')}.html", include_plotlyjs = 'directory', auto_open = False)
            except:
                print('NETWORK WRITE ERROR (main)')
            cur_ts = cur_time-td
            # need to ignore the just completed playback (last 1 hour)
            ac_bias = getACISBiasAddr(cur_ts,cur_time-timedelta(seconds=3600), ssr_sel) # update ac_bias table, ignore playbacks with last [TBR] hour
            bcw_list = []
        if (pben_val == 1) & (pben_old == 0): # start of playback, update table
            cur_ts = cur_time-td
            ac_bias = getACISBiasAddr(cur_ts,cur_time-timedelta(seconds=3600), ssr_sel) # update ac_bias table, ignore playbacks with last [TBR] hour
        # update variables for next iteration
        M1466_old = M1466_val
        M1966_old = M1966_val
        cur_time_old = cur_time
        pben_old = pben_val
        time.sleep(5)


pio.renderers.default = "notebook"

fetch_eng.data_source.set('maude')
def format_dates(cheta_dates):
    return np.array([datetime.strptime(d, '%Y:%j:%H:%M:%S.%f') for d in CxoTime(cheta_dates).date])
addr_max  = 134217696 # calculated or from GRETA Script?

t = datetime.now(timezone.utc)   # Get UTC Timezone value of current time
cur_time  = CxoTime(t)

hrs_prev = 48 # Window to look back over
t_win_start = timedelta(seconds=hrs_prev*3600)
t_win_stop = timedelta(seconds=2*3600)
tp = cur_time - t_win_stop # ignore playbacks ended in the last 2 hours, since these may be replays due to bad codewords
tp.format = 'yday'
ts = cur_time - t_win_start
ts.format = 'yday'
print(str(ts))
print(str(tp))

main(cur_time, ts)
