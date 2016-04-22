#!/usr/bin/env python3

import datetime
import json
import sys

from bs4 import BeautifulSoup
import requests
import tweepy

# Configuration
# !! Never put the API key and secret here !!
# Auth data file read from command line to avoid it being in repo
AUTH_FILE = sys.argv[1]
URL_PREFIX = "http://www.realtimetrains.co.uk"
URL_TIME = "0000-2359"
TIMETABLE_KEYS = ["ind", "plan_arr", "act_arr", "origin", "platform",
                  "id_url", "toc", "destination", "plan_dep", "act_dep"]

stations = ["CREWSYC"] # Will be read from file, eventually
current_date = datetime.date.today()
url_date = current_date.strftime("%Y/%m/%d")

def get_search_url(station):
    return "/".join([URL_PREFIX, "search/advanced",
                     station, url_date, URL_TIME])

def get_train_url(id_url):
    return URL_PREFIX + id_url

def make_twitter_api():
    with open(AUTH_FILE, "r") as auth_file:
        auth_data = json.load(auth_file)

    auth = tweepy.OAuthHandler(auth_data["consumer_key"],
                               auth_data["consumer_secret"])
    auth.set_access_token(auth_data["access_token"],
                          auth_data["access_secret"])
    return tweepy.API(auth)

def get_trains(station):
    trains = []
    # This could be a one-liner but Exception handling of the request
    # will need to be implemented at some point
    url = get_search_url(station)
    r = requests.get(url)
    page = BeautifulSoup(r.text, "html.parser")
    # For one, there is only the one table on the page
    table = page.find("table")
    # Discard the first table row, as it is the header
    rows = table.find_all("tr")[1:]

    for row in rows:
        # The information we want is the text in each table cell
        row_data = [td.text for td in row.find_all("td")]
        # Except ID, which is a link to the train's journey. We want the link address
        row_data[5] = row.find("a")["href"]

        trains.append(dict(zip(TIMETABLE_KEYS, row_data)))

    return trains

# Test code until main() is implemented
for station in stations:
    print(get_search_url(station))
    trains = get_trains(station)
    train_url = get_train_url(trains[0]["id_url"])
    api = make_twitter_api()
    api.update_status("Test:" + train_url)
