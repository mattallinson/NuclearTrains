#!/usr/bin/env python3

import datetime
import json

from bs4 import BeautifulSoup
import requests
import tweepy

# Configuration
# !! Never put the API key and secret here !!
AUTH_FILE = ""
URL_PREFIX = "http://www.realtimetrains.co.uk"
URL_TIME = "0000-2359"
TIMETABLE_KEYS = ["ind", "plan_arr", "act_arr", "origin", "platform",
                  "id_url", "toc", "destination", "plan_dep", "act_dep"]

stations = ["CREWSYC"]
current_date = datetime.date.today()
url_date = current_date.strftime("%Y/%m/%d")

def get_search_url(station):
    return "/".join([URL_PREFIX, "search/advanced", station, url_date, URL_TIME])

def get_train_url(id_url):
    return URL_PREFIX + id_url

def get_trains(station):
    trains = []

    url = get_search_url(station)
    r = requests.get(url)
    page = BeautifulSoup(r.text, "html.parser")

    table = page.find("table", attrs={"class":"table table-condensed servicelist advanced"})
    rows = table.find_all("tr")[1:] # Discard the first table row, as it is the header.

    for row in rows:
        # The information we want is the text in each table cell.
        row_data = [td.text for td in row.find_all("td")]
        # Except ID, which is a link to the train's journey. We want the link address.
        row_data[5] = row.find("a")["href"]

        trains.append(dict(zip(TIMETABLE_KEYS, row_data)))

    return trains

for station in stations:
    print(get_search_url(station))
    trains = get_trains(station)
    print(trains)
    print(get_train_url(trains[0]["id_url"]))
