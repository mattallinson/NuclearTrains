#!/usr/bin/env python3

import datetime
import json
import sys

import tweepy

import realtimetrains as rtt

# Configuration
# !! Never put the API key and secret here !!
# Auth data file read from command line to avoid it being in repo
AUTH_FILE = sys.argv[1]

stations = ["CREWSYC"] # Will be read from file, eventually

def make_twitter_api():
    with open(AUTH_FILE, "r") as auth_file:
        auth_data = json.load(auth_file)

    auth = tweepy.OAuthHandler(auth_data["consumer_key"],
                               auth_data["consumer_secret"])
    auth.set_access_token(auth_data["access_token"],
                          auth_data["access_secret"])
    return tweepy.API(auth)

# Test code until main() is implemented
if __name__ == "__main__":
    current_date = datetime.date.today()
    for station in stations:
        #print(get_search_url(station, current_date))
        trains = rtt.search(station, current_date)
        for train in trains:
            print(train.running)
        test_train = trains[2]
        test_train.populate()
        print(test_train.origin)
        for loc in test_train.calling_points:
            print(loc)
        print(test_train.destination)
        api = make_twitter_api()
