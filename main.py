#!/usr/bin/env python3

import datetime
import json
import sys
import difflib
from time import sleep

import tweepy
from apscheduler.schedulers.background import BackgroundScheduler

import realtimetrains as rtt

# Configuration
# !! Never put the API key and secret here !!
# Auth data file read from command line to avoid it being in repo
STATION_FILE = "data/stations.json"
TOWN_FILE = "data/urban.json"
TWEET_FILE = "data/tweets.txt"
AUTH_FILE = sys.argv[1]

def make_twitter_api():
    with open(AUTH_FILE, "r") as auth_file:
        auth_data = json.load(auth_file)

    auth = tweepy.OAuthHandler(auth_data["consumer_key"],
                               auth_data["consumer_secret"])
    auth.set_access_token(auth_data["access_token"],
                          auth_data["access_secret"])
    return tweepy.API(auth)

def make_tweets(train):
    # This needs an overhaul when Locations use datetime objects
    tweets = []
    time = train.origin.dep
    when = datetime.datetime.combine(current_date, datetime.datetime.strptime(time, "%H%M").time())
    what = tweet_templates[1].format(uid=train.uid, origin=train.origin.name,
        destination=train.destination.name, url=train.url)
    tweets.append((when, what))

    for location in train.calling_points:
        if location.code in towns.keys():
            time = location.arr if location.arr != "pass" else location.dep
            town = towns[location.code]
            when = datetime.datetime.combine(current_date, datetime.datetime.strptime(time, "%H%M").time())
            what = tweet_templates[0].format(uid=train.uid, town=town, url=train.url)
            tweets.append((when, what))

    time = train.destination.arr
    when = datetime.datetime.combine(current_date, datetime.datetime.strptime(time, "%H%M").time())
    what = tweet_templates[2].format(uid=train.uid,
        destination=train.destination.name, url=train.url)
    tweets.append((when, what))

    return tweets

def get_trains(stations, current_date):
    all_trains = []
    for station in stations:
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

def get_nuclear_trains(stations, current_date):
    all_trains = get_trains(stations["to"].keys(), current_date)
    nuclear_trains = []
    for train in all_trains:
        if train.running and is_nuclear(train, stations)\
                and train.uid not in [t.uid for t in nuclear_trains]:
            nuclear_trains.append(train)
    return nuclear_trains

# Initialisation
with open(STATION_FILE, "r") as station_file:
    stations = json.load(station_file)
with open(TOWN_FILE, "r") as town_file:
    towns = json.load(town_file)
with open(TWEET_FILE, "r") as tweet_file:
    tweet_templates = tweet_file.readlines()

current_date = datetime.date.today()
sched = BackgroundScheduler()
sched.start()
api = make_twitter_api()

def main():
    nuclear_trains = get_nuclear_trains(stations, current_date)
    for train in nuclear_trains:
        tweets = make_tweets(train)
        print(train)
        for when, what in tweets:
            print('{:%Y-%m-%d %H:%M} "{}"'.format(when, what))
            # Give the job an id so we can refer to it later if needs be
            job_id = when.strftime("%H%M") + train.uid
            sched.add_job(api.update_status, "date", run_date=when, args=[what], id=job_id)

    sched_jobs = sched.get_jobs()
    while len(sched_jobs) > 0:
        sched.print_jobs()
        sleep(300)
        sched_jobs = sched.get_jobs()

if __name__ == '__main__':
    main()
