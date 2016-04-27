#!/usr/bin/env python3

import datetime
from time import sleep
import sys
import json

from apscheduler.schedulers.background import BackgroundScheduler

import realtimetrains as rtt
import main

FORMAT = "%H%M"

sched = BackgroundScheduler()
sched.start()
main.AUTH_FILE = sys.argv[1]
current_date = datetime.date.today()
api = main.make_twitter_api()

with open(main.STATIONS, "r") as station_file:
    stations = json.load(station_file)
with open(main.URBAN_AREAS, "r") as town_file:
    towns = json.load(town_file)
with open(main.TWEET_TEMPLATES, "r") as tweet_file:
    tweet_templates = tweet_file.readlines()

now = datetime.datetime.now()
begin = now + datetime.timedelta(minutes=2)
call = now + datetime.timedelta(minutes=5)
end = now + datetime.timedelta(minutes=10)

test_origin = rtt.Location("Sodor Nuclear Electric", None, begin.strftime(FORMAT), None, begin.strftime(FORMAT), None)
test_call = rtt.Location("Cark [CAK]", "pass", call.strftime(FORMAT), "pass", call.strftime(FORMAT), None)
test_destination = rtt.Location("your house", end.strftime(FORMAT), None, end.strftime(FORMAT), None, None)

test_train = rtt.Train("TEST01", current_date)
test_train.origin = test_origin
test_train.destination = test_destination
test_train.calling_points = [test_call]

tweets = main.make_tweets(test_train)
jobs = []
for when, what in tweets:
    print('{:%Y-%m-%d %H:%M} "{}"'.format(when, what))
    job_id = when.strftime("%H%M") + test_train.uid
    job = sched.add_job(api.update_status, "date", run_date=when, args=[what], id=job_id)
    jobs.append(job)

sched_jobs = sched.get_jobs()
while len(sched_jobs) > 0:
    sched.print_jobs()
    sleep(60)
    sched_jobs = sched.get_jobs()
