#!/usr/bin/env python3

import datetime

from bs4 import BeautifulSoup
import requests

URL_PREFIX = "http://www.realtimetrains.co.uk"
DEFAULT_FROM = "0000"
DEFAULT_TO = "2359"
DATE_FORMAT = "%Y/%m/%d"
TIME_FORMAT = "%H%M"
FRAC_TIMES = {
        "¼":datetime.timedelta(seconds=15),
        "½":datetime.timedelta(seconds=30),
        "¾":datetime.timedelta(seconds=45)}
ONE_DAY = datetime.timedelta(days=1)
NO_SCHEDULE = "Couldn't find the schedule..."

class Location():

    def __init__(self, name, wtt_arr, wtt_dep, real_arr, real_dep, delay):
        # Some names have a three-letter code. If so, separate this
        if "[" in name:
            name_parts = name.strip().split()
            self.code = name_parts[-1].strip("[]")
            self.name = " ".join(name_parts[:-1])
        else:
            self.name = name.strip()
            self.code = None

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
        arriving = " arriving " + self.arr.strftime("%H:%M:%S") if self.arr else ""
        departing = " departing " + self.dep.strftime("%H:%M:%S") if self.dep else ""
        return "{}:{}{}".format(self.name, arriving, departing)

    def __repr__(self):
        return "<{}.Location(name='{}', ...)>".format(__name__, self.name)

    def remove_day(self):
        for loc_time in [self.wtt_arr, self.wtt_dep,
                         self.real_arr, self.real_dep]:
            if loc_time is not None:
                loc_time -= ONE_DAY

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

    def __eq__(self, other):
        return self.uid == other.uid and self.date == other.date

    def __str__(self):
        return "train {} on {}: {}".format(self.uid,
                                           self.date.strftime(DATE_FORMAT),
                                           self.url)

    def __repr__(self):
        return "<{}.Train(uid='{}', date='{:%Y-%m-%d}')>".format(__name__, self.uid, self.date)

    @property
    def url(self):
        return "/".join([URL_PREFIX, "train", self.uid,
                         self.date.strftime(DATE_FORMAT), "advanced"])

    def soup(self):
        r = requests.get(self.url)
        soup = BeautifulSoup(r.text, "html.parser")
        if soup.text == NO_SCHEDULE:
            self.running = False
            raise RuntimeError("schedule not found")
            return None
        return soup

    def update_locations(self, soup):
        print("Getting locations of {}".format(self))
        locations = []
        # First two rows of train page are headers
        rows = soup.find("table").find_all("tr")[2:]
        for row in rows:
            cells = row.find_all("td")
            name = cells[0].text
            wtt_arr = _location_datetime(self.date, cells[2].text)
            wtt_dep = _location_datetime(self.date, cells[3].text)
            if len(cells) <= 10: # No realtime report
                real_arr = real_dep = delay = None
            else:
                real_arr = _location_datetime(self.date, cells[4].text)
                real_dep = _location_datetime(self.date, cells[5].text)
                delay = cells[6].text
            locations.append(Location(name, wtt_arr, wtt_dep,
                                      real_arr, real_dep, delay))

        self.origin = locations[0]
        self.destination = locations[-1]
        self.calling_points = locations[1:-1]
        # If train runs past midnight, some locations will be on the
        # wrong day; correct by comparing to the origin:
        for location in self.calling_points:
            if location.wtt_dep < self.origin.wtt_dep:
                location.remove_day()
        # And for destination, which doesn't have a departure time:
        if self.destination.wtt_arr < self.origin.wtt_dep:
            self.destination.remove_day()

    def populate(self):
        print("Populating {}".format(self))
        soup = self.soup()
        # Top of page shows schedule info, including if a
        # runs-as-required train is active
        schedule_info = soup.find("div",
                        attrs={"class":"detailed-schedule-info"})
        # Text in schedule_info isn't tagged well
        if "Running" in schedule_info.text:
            self.running = True
            print("Running!")
        # Important info is in <strong> tags. Their absolute position
        # is used, assuming it won't change as rtt isn't maintained
        info = schedule_info.find_all("strong")
        self.stp_code = info[0]

        self.update_locations(soup)

def _location_datetime(loc_date, loc_timestring):
    """Creates a datetime object for a train calling location from
    loc_date: a given date as a date object, and
    loc_timestring: the location's 4- or 5-digit time string"""
    # Some values will not translate to a datetime object
    if loc_timestring in ["", "pass", "N/R"]:
        return None
    # First four digits are in the simple form of HHMM
    loc_time = datetime.datetime.strptime(loc_timestring[:4], TIME_FORMAT).time()
    loc_datetime = datetime.datetime.combine(loc_date, loc_time)
    # Sometimes there is a final fractional digit, whose value in
    # seconds stored as timedeltas can be looked up
    if len(loc_timestring) == 5:
        loc_datetime += FRAC_TIMES[loc_timestring[4]]
    return loc_datetime

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
                         "to", to_station, url_date, url_time])
    else:
        return "/".join([URL_PREFIX, "search/advanced",
                         station, url_date, url_time])

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
    if table == None:
        return None
    # Discard the first table row, as it is the header
    rows = table.find_all("tr")[1:]

    for row in rows:
        id_url = row.find("a")["href"]
        # url is in form of "/train/H61429/2016/04/23/advanced"
        # we want the UID, the third part of this
        uid = id_url.split("/")[2]

        trains.append(Train(uid, search_date))

    return trains
