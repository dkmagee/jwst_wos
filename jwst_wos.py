#!/usr/bin/env python

import bs4
import requests
from itertools import accumulate
import datetime as dt
import pandas as pd
import streamlit as st
from awesome_table import AwesomeTable
from awesome_table.column import Column, ColumnDType


# STScI main URL
STSCI_URL = "https://www.stsci.edu"
# the JWST weekly observing schedule URL
JWST_WOS_URL = "https://www.stsci.edu/jwst/science-execution/observing-schedules"

# get the n latest JWST weekly observing schedule reports
LOOKBACK = 5

response = requests.get(JWST_WOS_URL)
data = bs4.BeautifulSoup(response.text, "html.parser")

# get the JWST weekly observing report links
report_links = []

for l in data.find_all("a"):
    if (
        "_report_" in l["href"]
        and l["href"].split("/")[-1].startswith(str(dt.datetime.now().year))
        and l["href"].split("/")[-1].endswith(".txt")
    ):
        report_links.append(f'{STSCI_URL}{l["href"]}')


# parse the JWST weekly observing schedule text files
wos_data = []
for rlnk in report_links[:LOOKBACK]:
    wos_txt = requests.get(rlnk, stream=True).text.splitlines()
    col_widths = [len(i) + 2 for i in wos_txt[3].split()]
    # set the width of the last column (keywords) to 300 characters for parsing
    col_widths[-1] = 300
    idx = list(accumulate(col_widths, initial=0))
    col_titles = [
        wos_txt[2][i:j].strip().replace(" ", "_") for i, j in zip(idx[:-1], idx[1:])
    ]
    for wt in wos_txt[4:]:
        wtl = [wt[i:j].strip() for i, j in zip(idx[:-1], idx[1:])]
        wos_data.append(dict(zip(col_titles, wtl)))

# clean up the schedule columns
# convert SCHEDULED_START_TIME to datetime object
prev_sst = ""
prev_vid = ""
for i, wd in enumerate(wos_data):
    if wd["VISIT_ID"] == "":
        wd["VISIT_ID"] = prev_vid
    prev_vid = wd["VISIT_ID"]

    sst = wd["SCHEDULED_START_TIME"]
    if sst == "^ATTACHED TO PRIME^":
        sst = prev_sst
    if sst == "":
        sst = prev_sst
    wd["SCHEDULED_START_TIME"] = dt.datetime.strptime(sst, "%Y-%m-%dT%H:%M:%SZ")
    prev_sst = sst

    if wd["DURATION"]:
        wd["DURATION"] = wd["DURATION"].split("/")[1]

st.set_page_config(page_title="JWST Weekly Schedule", layout="wide")
st.title("JWST Weekly Schedules")

st.session_state["order_column"] = "SCHEDULED_START_TIME"
st.session_state["order_ascending"] = "Descending"

AwesomeTable(
    pd.json_normalize(wos_data),
    columns=[
        Column(name="VISIT_ID", label="Visit ID"),
        Column(name="PCS_MODE", label="PCS Mode"),
        Column(name="VISIT_TYPE", label="Visit Type"),
        Column(
            name="SCHEDULED_START_TIME",
            label="Scheduled Start Time",
            dtype=ColumnDType.DATETIME,
        ),
        Column(name="DURATION", label="Duration"),
        Column(name="SCIENCE_INSTRUMENT_AND_MODE", label="Science Instrument and Mode"),
        Column(name="TARGET_NAME", label="Target Name"),
        Column(name="CATEGORY", label="Category"),
        Column(name="KEYWORDS", label="Keywords"),
    ],
    show_search=True,
    show_order=True,
)
