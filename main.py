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
ROUTES_FILE = "data/routes.json"
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
    tweets = []
    when = train.origin.dep
    what = tweet_templates[1].format(uid=train.uid, origin=train.origin.name,
        destination=train.destination.name, time=when.strftime("%H:%M"), url=train.url)
    tweets.append((when, what))

    for location in train.calling_points:
        if location.code in towns.keys():
            when = location.arr if location.arr != None else location.dep
            what = tweet_templates[0].format(uid=train.uid,
                town=towns[location.code], url=train.url)
            tweets.append((when, what))

    when = train.destination.arr
    what = tweet_templates[2].format(uid=train.uid,
        destination=train.destination.name, url=train.url)
    tweets.append((when, what))

    return tweets

def get_trains(routes, current_date):
    all_trains = []
    for route in routes:
        trains = rtt.search(route["from"], current_date, to_station=route["to"])
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
            print("No trains from {} to {}".format(route["from"], route["to"]))
    return all_trains

def make_jobs():
    current_date = datetime.date.today()
    all_trains = get_trains(routes, current_date)
    nuclear_trains = [train for train in all_trains if train.running]
    for train in nuclear_trains:
        tweets = make_tweets(train)
        print(train)
        for when, what in tweets:
            print('{:%Y-%m-%d %H:%M} "{}"'.format(when, what))
            # Give the job an id so we can refer to it later if needs be
            job_id = when.strftime("%H%M") + train.uid
            sched.add_job(api.update_status, "date", run_date=when, args=[what], id=job_id)

# Initialisation
with open(ROUTES_FILE, "r") as routes_file:
    routes = json.load(routes_file)
with open(TOWN_FILE, "r") as town_file:
    towns = json.load(town_file)
with open(TWEET_FILE, "r") as tweet_file:
    tweet_templates = tweet_file.readlines()

sched = BackgroundScheduler()
sched.start()
api = make_twitter_api()

def main():
    sched.add_job(make_jobs, "cron", hour=0, minute=5)

    while len(sched.get_jobs) > 0:
        sched.print_jobs()
        sleep(300)

if __name__ == '__main__':
    main()
