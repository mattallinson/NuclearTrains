#!/usr/bin/env python3

import datetime
from hashlib import md5
import requests

URL_PREFIX = "https://api.rtt.io/api/v1/json"
LOCATION_SEARCH = "searchv2"
TRAIN_SEARCH = "servicev2"
DATE_FORMAT = "%Y/%m/%d"
TIME_FORMAT = "%H%M"
ONE_DAY = datetime.timedelta(days=1)
NO_SCHEDULE = "Couldn't find the schedule..."


class Location():

    def __init__(self, name, tiploc, wtt_arr, wtt_dep, real_arr, real_dep, delay, crs=None):

    # 3 letter code is now handled by "crs" which is a code that only exists AFAIK for extant passenger staions    
        self.name = name.strip()
        self.crs = crs
        self.tiploc = tiploc 
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
        arriving = " arriving " + self.arr.strftime("%H:%M:%S")\
            if self.arr else ""
        departing = " departing " + self.dep.strftime("%H:%M:%S")\
            if self.dep else ""
        return "{}:{}{}".format(self.name, arriving, departing)

    def __repr__(self):
        return "<{}.Location(name='{}', ...)>".format(__name__, self.name)

    def remove_day(self):
        for loc_time in [self.wtt_arr, self.wtt_dep,
                         self.real_arr, self.real_dep]:
            if loc_time is not None:
                loc_time -= ONE_DAY


class Train():

    def __init__(self, uid, date, api_key):
        self.uid = uid
        self.date = date
        self.api_key = api_key

        self.webpage_checksum = 0
        self.url = "/".join([URL_PREFIX, TRAIN_SEARCH, self.uid,
                            self.date.strftime(DATE_FORMAT)])

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
        return "<{}.Train(uid='{}', date='{:%Y-%m-%d}')>".format(__name__,
                                                                 self.uid,
                                                                 self.date)

    def update_locations(self, train_json):
        locations = []
        
        for place in train_json['locations']:
            name = place['description']
            tiploc = place['tiploc']
            if 'crs' in place.keys():
                crs = place['crs']
            else:
                crs_code = None
            if 'wttBookedArrival' in place.keys():
                wtt_arr = _location_datetime(self.date, place['wttBookedArrival'])
            else:
                wtt_arr = None
            
            if 'wttBookedDeparture' in place.keys():
                wtt_dep = _location_datetime(self.date, place['wttBookedDeparture'])
            elif 'wttBookedPass' in place.keys():
                wtt_dep = _location_datetime(self.date, place['wttBookedPass'])
            else: #terminus 
                wtt_dep = None

            if 'realtimeArrival' in place.keys():
                real_arr = _location_datetime(self.date, place['realtimeArrival'])
            else:
                real_arr = None
            if 'realtimeDeparture' in place.keys():
                real_dep = _location_datetime(self.date, place["realtimeDeparture"])
            elif "realtimePass" in place.keys():
                real_dep = _location_datetime(self.date, place["realtimePass"])
            else:
                real_dep = None

            # Negative delay indicates train is early.
            for keys in place.keys():
                if 'Lateness' in key:
                    delay = place[key]
                else:
                    delay = 0


            locations.append(Location(name, tiploc, wtt_arr, wtt_dep,
                                      real_arr, real_dep, delay, crs))

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
        # print("Getting data for {}".format(self))
        r = requests.get(self.url, auth = self.api_key)

        # if website text's hash is the same as before, do nothing
        md5sum = md5(r.text.encode("utf-8")).digest()
        if md5sum == self.webpage_checksum:
            # print("{} unchanged".format(self))
            return False
        else:
            self.webpage_checksum = md5sum
        
        if 'No schedule found' in r.text:
            self.running = False
            raise RuntimeError("schedule not found")
        else:
            self.running = True

        #info = schedule_info.find_all("strong")
        #self.stp_code = info[0]

        self.update_locations(r.json())
        return True


def _location_datetime(loc_date, loc_timestring):
    """Creates a datetime object for a train calling location from
    loc_date: a given date as a date object, and
    """
    # Some values will not translate to a datetime object
    # First four digits are in the simple form of HHMM
    loc_time = datetime.datetime.strptime(loc_timestring[:4],
                                          TIME_FORMAT).time()
    loc_datetime = datetime.datetime.combine(loc_date, loc_time)
    # Sometimes the time is actual a 6 digit Hrs Mins Seconds time. This is designed to hand this.
    if len(loc_timestring) == 6:
        loc_datetime += datetime.timedelta(seconds= int(loc_timestring[4:]))
    return loc_datetime


def _search_url(station, search_date=None, to_station=None, to_time=None):
    if search_date is None:
        search_date = datetime.datetime.today()
    url_date = search_date.strftime(DATE_FORMAT)
    
    if to_station is not None:
        search_url = "/".join([URL_PREFIX, LOCATION_SEARCH, station, "to", to_station, url_date])
    else:
        search_url = "/".join([URL_PREFIX, LOCATION_SEARCH, station, url_date])
    
    if to_time is not None: #adds time specific searching - I think this might be quite buggy at the RTT end and is best avoided
        time_string = to_time.strftime(TIME_FORMAT)
        search_url += "/"+time_string 

    return search_url



def search(api_key, station, search_date = None, to_station=None, time=None):
    trains = []
    if search_date is None:
        search_date = datetime.datetime.today()

    url = _search_url(station, to_station = to_station, search_date = search_date,  to_time = time)
    request = requests.get(url, auth = api_key)

    feed = request.json()["services"]

    for train_service in feed:
        uid = train_service["serviceUid"]
        trains.append(Train(uid, search_date, api_key))

    return trains
