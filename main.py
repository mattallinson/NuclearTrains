#!/usr/bin/env python3

import datetime
import json
import sys
import difflib

import tweepy

import realtimetrains as rtt

# Configuration
# !! Never put the API key and secret here !!
# Auth data file read from command line to avoid it being in repo
STATIONS = "data/stations.json"
URBAN_AREAS = "data/urban.json"
TWEET_TEMPLATES = "data/tweets.txt"

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
        print(station)
        trains = rtt.search(station, current_date)
        if trains is not None:
            # Incredbly cludgy way of dealing with cases where train's
            # start date is not the same as search date
            for train in trains:
                try:
                    train.populate()
                except RuntimeError:
                    print("No schedule for {}".format(train))
                else:
                    all_trains.append(train)
        else:
            print("No trains at "+ station)
    return all_trains

def is_nuclear(train, stations):
    return train.origin.name in stations["from"].values() and\
           train.destination.name in stations["to"].values()

def nuclear_trains(stations, current_date):
    all_trains = get_trains(stations["to"].keys(), current_date)
    nuclear_trains = []
    for train in all_trains:
        if train.running and is_nuclear(train, stations)\
                and train.uid not in [t.uid for t in nuclear_trains]:
            nuclear_trains.append(train)
    return nuclear_trains

# Test code until main() is implemented
if __name__ == "__main__":
    AUTH_FILE = sys.argv[1]
    current_date = datetime.date.today()
    api = make_twitter_api()

    with open(STATIONS, "r") as station_file:
        stations = json.load(station_file)
    with open(URBAN_AREAS, "r") as town_file:
        towns = json.load(town_file)
    with open(TWEET_TEMPLATES, "r") as tweet_file:
        tweet_templates = tweet_file.readlines()


    #print(rtt._search_url("CREWSYC", current_date))
    nuclear_trains = nuclear_trains(stations, current_date)

    for train in nuclear_trains:
        print("\n\nNuclear {}".format(train))
        print("From {} to {}".format(train.origin.name, train.destination.name))
        for location in train.calling_points:
            if location.code in towns.keys():
                print("Tweet: {} at {}".format(towns[location.code], location.dep))
                print(tweet_templates[0].format(train.uid, towns[location.code], train.url))
