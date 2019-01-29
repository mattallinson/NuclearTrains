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

# Configuration
# !! Never put the API key and secret here !!
# Auth data file read from command line to avoid it being in repo
ROUTES_FILE = "data/routes.json"
TOWN_FILE = "data/urban.json"
TWEET_FILE = "data/tweets.txt"
AUTH_FILE = sys.argv[2]

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
    auth = tweepy.OAuthHandler(auth_data["twitter_consumer_key"],
                               auth_data["twitter_consumer_secret"])
    auth.set_access_token(auth_data["twitter_access_token"],
                          auth_data["twitter_access_secret"])
    return tweepy.API(auth)


def make_mastodon_api():
    return Mastodon(api_base_url="https://botsin.space",
                    access_token=auth_data["mastodon_access_token"])


def make_tweets(train):
    origin = towns[train.origin.name]
    dest = towns[train.destination.name]
    tweets = []

    for location in train.calling_points:
        if location.code in towns.keys() or location.name in towns.keys():
            when = location.arr if location.arr is not None else location.dep
            if location.code == "LPG":
                what = tweet_templates[0].format(url=train.url)
            else:
                what = tweet_templates[1].format(origin=origin,
                                                 destination=dest,
                                                 town=towns[location.code],
                                                 url=train.url)

            loc = location.name
            tweets.append((when, what, loc))

    # handle special case for origin
    when = train.origin.dep
    what = tweet_templates[2].format(origin=origin,
                                     destination=dest,
                                     url=train.url)
    loc = train.origin.name
    tweets.append((when, what, loc))

    # handle special case for desination
    when = train.destination.arr
    what = tweet_templates[3].format(origin=origin,
                                     destination=dest,
                                     url=train.url)
    loc = train.destination.name
    tweets.append((when, what, loc))

    return tweets


def get_trains(routes):
    all_trains = []
    for route in routes:
        trains = rtt.search(route["from"], to_station=route["to"])
        if trains is not None:
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
        tweets = make_tweets(train)
        for when, what, loc in tweets:
            # Give the jobs an id so we can refer to them later if needs be
            job_id = "{}: {}".format(train.uid, loc)
            current_jobs = sched.get_jobs()
            current_ids = [job.id for job in current_jobs]
            if job_id not in current_ids:
                sched.add_job(twitter_api.update_status, trigger="date",
                              run_date=when, args=[what], id="tweet " + job_id)
                sched.add_job(mastodon_api.toot, trigger="date",
                              run_date=when, args=[what], id="toot " + job_id)
            else:
                sched.reschedule_job(job_id, trigger="date", run_date=when)


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
