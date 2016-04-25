#!/usr/bin/env python3

import datetime
import json
import sys

import tweepy

import realtimetrains as rtt

# Configuration
# !! Never put the API key and secret here !!
# Auth data file read from command line to avoid it being in repo
STATIONS = "data/stations.json"
URBAN_AREAS = "data/urban.json"

def make_twitter_api():
    with open(AUTH_FILE, "r") as auth_file:
        auth_data = json.load(auth_file)

    auth = tweepy.OAuthHandler(auth_data["consumer_key"],
                               auth_data["consumer_secret"])
    auth.set_access_token(auth_data["access_token"],
                          auth_data["access_secret"])
    return tweepy.API(auth)

def get_trains(stations, current_date):
    all_trains = []
    for station in stations:
        trains = rtt.search(station, current_date)
        if trains is not None:
            all_trains += trains
        else:
            print("No trains at "+ station)
    return all_trains

def is_nuclear(train, stations):
    return train.origin in stations["from"] and\
           train.destination in stations["to"]

# Test code until main() is implemented
if __name__ == "__main__":
    AUTH_FILE = sys.argv[1]
    current_date = datetime.date(2016, 4, 21) # for testing purposes only
    with open(STATIONS, "r") as station_file:
        stations = json.load(station_file)
    with open(URBAN_AREAS, "r") as town_file:
        towns = json.load(town_file)

    #print(rtt._search_url("CREWSYC", current_date))
    nuclear_trains = [train for train
                      in get_trains(stations["to"], current_date)
                      if train.running and is_nuclear(train, stations)]
    print(nuclear_trains)
    api = make_twitter_api()
