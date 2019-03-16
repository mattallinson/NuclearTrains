#!/usr/bin/env python3

import datetime
import json
import logging
import sys
from time import sleep

import tweepy
from mastodon import Mastodon
from apscheduler.schedulers.background import BackgroundScheduler

import realtimetrains as rtt

logging.basicConfig(filename='nt.log', level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
tweets = {} #Needed for tweet_threader see below

# Configuration
# !! Never put the API key and secret here !!
# Auth data file read from command line to avoid it being in repo
ROUTES_FILE = "data/routes.json"
TOWN_FILE = "data/urban.json"
TWEET_FILE = "data/messages.txt"
AUTH_FILE = sys.argv[1]

with open(ROUTES_FILE, "r") as routes_file:
    routes = json.load(routes_file)
with open(TOWN_FILE, "r") as town_file:
    towns = json.load(town_file)
with open(TWEET_FILE, "r") as tweet_file:
    tweet_templates = tweet_file.readlines()
with open(AUTH_FILE, "r") as auth_file:
        auth_data = json.load(auth_file)

sched = BackgroundScheduler()
sched.start()


def make_twitter_api():
    auth = tweepy.OAuthHandler(auth_data["twitter"]["consumer_key"],
                               auth_data["twitter"]["consumer_secret"])
    auth.set_access_token(auth_data["twitter"]["access_token"],
                          auth_data["twitter"]["access_secret"])
    return tweepy.API(auth)


def make_mastodon_api():
    return Mastodon(api_base_url="https://botsin.space",
                    access_token=auth_data["mastodon"]["access_token"])


def make_messages(train):
    origin = towns[train.origin.name]
    dest = towns[train.destination.name]
    messages = []

    for location in train.calling_points:
        if location.crs in towns.keys() or location.name in towns.keys():
            when = location.arr if location.arr is not None else location.dep
            #handles case for LlanfairPG
            if location.crs == "LPG":
                what = tweet_templates[0].format(url=train.web_url)
            else:
                what = tweet_templates[1].format(origin=origin,
                                                 destination=dest,
                                                 town=towns[location.crs],
                                                 url=train.web_url)

            loc = location.name
            messages.append((when, what, loc))

    # handle special case for origin
    when = train.origin.dep
    what = tweet_templates[2].format(origin=origin,
                                     destination=dest,
                                     url=train.web_url)
    loc = train.origin.name
    messages.append((when, what, loc))

    # handle special case for desination
    when = train.destination.arr
    what = tweet_templates[3].format(origin=origin,
                                     destination=dest,
                                     url=train.web_url)
    loc = train.destination.name
    messages.append((when, what, loc))

    return messages


def get_trains(routes):
    all_trains = []
    for route in routes:
        trains = rtt.search(route["from"], to_station=route["to"])
        if trains:
            # Incredbly cludgy way of dealing with cases where train's
            # start date is not the same as search date
            for train in trains:
                try:
                    train.populate()
                except RuntimeError:
                    logger.warning("No schedule for {}".format(train))
                else:
                    all_trains.append(train)
        else:
            logger.info(
                "No trains from {} to {}".format(route["from"], route["to"]))
    return all_trains


def make_jobs(trains):
    nuclear_trains = []
    for train in trains:
        train.populate()
        if train.running and train not in nuclear_trains:
            nuclear_trains.append(train)

    for train in nuclear_trains:
        train.populate()
        messages = make_messages(train)
        for when, what, loc in messages:
            # Give the jobs an id so we can refer to them later if needs be
            tweet_job_id = "tweet {}: {}".format(train.uid, loc)
            toot_job_id = "toot {}: {}".format(train.uid, loc)
            current_job_ids = [job.id for job in sched.get_jobs()]

            if tweet_job_id not in current_job_ids:
                sched.add_job(tweet_threader, trigger="date",
                              run_date=when, args=[train, what], id=tweet_job_id)
            else:
                sched.reschedule_job(tweet_job_id, trigger="date", run_date=when)

            if toot_job_id not in current_job_ids:
                sched.add_job(mastodon_api.toot, trigger="date",
                              run_date=when, args=[what], id=toot_job_id)
            else:
                sched.reschedule_job(toot_job_id, trigger="date", run_date=when)


def tweet_threader(train, tweet_text):
    # tweets is a dict of a list of tweets per train
    if train not in tweets:
        #creates new key in list for that train and add the first tweet
        tweets[train] = [twitter_api.update_status(tweet_text)]
    else: #takes the most recent tweet for that train
        previous_tweet = tweets[train][-1]
        #tweets and add the newest tweet to the end of the list   
        tweets[train].append(twitter_api.update_status(tweet_text,
                        in_reply_to_status_id=previous_tweet.id)) 


twitter_api = make_twitter_api()
mastodon_api = make_mastodon_api()


def main():

    current_date = datetime.date.today()
    all_trains = get_trains(routes)
    make_jobs(all_trains)
    sched.add_job(make_jobs, "cron", args=[all_trains],
                  minute="*/1", day=current_date.day)

    while sched.get_jobs():
        try:
            for job in sched.get_jobs():
                logger.info("{}, {}".format(job.id, job.trigger))
            sleep(300)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception as e:
            logger.exception("{!r}".format(e))


if __name__ == '__main__':
    main()
