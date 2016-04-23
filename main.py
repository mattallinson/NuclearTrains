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
DATE_FORMAT = "%Y/%m/%d"
TIMETABLE_KEYS = ["ind", "plan_arr", "act_arr", "origin", "platform",
                  "id_url", "toc", "destination", "plan_dep", "act_dep"]

stations = ["CREWSYC"] # Will be read from file, eventually

class Location():

    def __init__(self, name, wtt_arr, wtt_dep, real_arr, real_dep, delay):
        # Some names have a three-letter code. If so, separate this
        if "[" in name:
            name_parts = name.split()
            self.code = name_parts[-1].strip("[]")
            self.name = " ".join(name_parts[:-1])
        else:
            self.name = name

        self.wtt_arr = wtt_arr
        self.wtt_dep = wtt_dep
        self.real_arr = real_arr
        self.real_dep = real_dep
        self.delay = delay

        self._arr = None
        self._dep = None

    @property
    def arr(self):
        if self.real_arr is not None:
            self._arr = self.real_arr
        else:
            self._arr = self.wtt_arr
        return self._arr

    @property
    def dep(self):
        if self.real_dep is not None:
            self._dep = self.real_dep
        else:
            self._dep = self.wtt_dep
        return self._dep

    def __str__(self):
        if self.arr == None or self.arr == "pass":
            arriving = ""
        else:
            arriving = " arriving " + self.arr
        departing = " departing " + self.dep if self.dep else ""
        return "{}:{}{}".format(self.name, arriving, departing)

class Train():

    def __init__(self, uid, date):
        self.uid = uid
        self.date = date

        self.origin = None
        self.destination = None
        self.calling_points = None
        self.stp_code = None
        self.trailing_load = None
        self.running = False

        self._soup = None

    @property
    def url(self):
        return "/".join([URL_PREFIX, "train", self.uid,
                         self.date.strftime(DATE_FORMAT), "advanced"])

    @property
    def soup(self):
        if self._soup is not None:
            return self._soup
        else:
            r = requests.get(self.url)
            self._soup = BeautifulSoup(r.text, "html.parser")
            return self._soup

    def update_locations(self):
        locations = []
        # First two rows of train page are headers
        rows = self.soup.find("table").find_all("tr")[2:]
        for row in rows:
            cells = row.find_all("td")
            name = cells[0].text
            wtt_arr = cells[2].text
            wtt_dep = cells[3].text
            if len(cells) == 10: # No realtime report, thus colspan=3
                real_arr = real_dep = delay = None
            else:
                real_arr = cells[4].text
                real_dep = cells[5].text
                delay = cells[6].text
            locations.append(Location(name, wtt_arr, wtt_dep,
                                      real_arr, real_dep, delay))
        self.origin = locations[0]
        self.destination = locations[-1]
        self.calling_points = locations[1:-1]

    def populate(self):
        self.update_locations()
        # Top of page shows schedule info, including if a
        # runs-as-required train is active
        print("populate")
        print(self.soup is not None)
        schedule_info = self.soup.find("div",
                                  attrs={"class":"detailed-schedule-info"})
        # Text in schedule_info isn't tagged well
        if "Realtime Status" in schedule_info.text:
            self.running = True
        # Important info is in <strong> tags. Their absolute position
        # is used, assuming it won't change as rtt isn't maintained
        info = schedule_info.find_all("strong")
        self.stp_code = info[0]
        self.trailing_load = info[9]

def get_search_url(station, search_date, to_station=None):
    url_date = search_date.strftime(DATE_FORMAT)
    if to_station is not None:
        return "/".join([URL_PREFIX, "search/advanced", station,
                         "to", to_station, url_date, URL_TIME])
    else:
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

def get_trains(station, search_date):
    trains = []
    # This could be a one-liner but Exception handling of the request
    # will need to be implemented at some point
    url = get_search_url(station, search_date)
    r = requests.get(url)
    page = BeautifulSoup(r.text, "html.parser")
    # For one, there is only the one table on the page
    table = page.find("table")
    # Discard the first table row, as it is the header
    rows = table.find_all("tr")[1:]

    for row in rows:
        id_url = row.find("a")["href"]
        # url is in form of "/train/H61429/2016/04/23/advanced"
        # we want the UID, the third part of this
        uid = id_url.split("/")[2]

        trains.append(Train(uid, search_date))

    return trains

# Test code until main() is implemented
if __name__ == "__main__":
    current_date = datetime.date.today()
    for station in stations:
        #print(get_search_url(station, current_date))
        trains = get_trains(station, current_date)
        for train in trains:
            print(train.running)
        test_train = trains[2]
        test_train.populate()
        print(test_train.origin)
        for loc in test_train.calling_points:
            print(loc)
        print(test_train.destination)
        api = make_twitter_api()
