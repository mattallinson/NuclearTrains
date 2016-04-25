#!/usr/bin/env python3

import datetime

from bs4 import BeautifulSoup
import requests

URL_PREFIX = "http://www.realtimetrains.co.uk"
DEFAULT_FROM = "0000"
DEFAULT_TO = "2359"
DATE_FORMAT = "%Y/%m/%d"
TIME_FORMAT = "%H%M"

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
        self.trailing_load = info[9

def _search_url(station, search_date, to_station=None,
                from_time=None, to_time=None):
    url_date = search_date.strftime(DATE_FORMAT)
    if from_time is not None:
        from_string = from_time.strftime(TIME_FORMAT)
    else:
        from_string = DEFAULT_FROM
    if to_time is not None:
        to_string = to_time.strftime(TIME_FORMAT)
    else:
        to_string = DEFAULT_TO
    url_time = from_string + "-" + to_string
    if to_station is not None:
        return "/".join([URL_PREFIX, "search/advanced", station,
                         "to", to_station, url_date, URL_TIME])
    else:
        return "/".join([URL_PREFIX, "search/advanced",
                         station, url_date, URL_TIME])

def search(station, search_date, to_station=None,
           from_time=None, to_time=None):
    trains = []
    # This could be a one-liner but Exception handling of the request
    # will need to be implemented at some point
    url = _search_url(station, search_date, to_station)
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