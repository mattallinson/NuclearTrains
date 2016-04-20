#!/usr/bin/env python3

import datetime

from bs4 import BeautifulSoup

# Configuration
# !! Never put the API key and secret here !!
stations = ["CREWSYC"]
URL_PREFIX = "www.realtimetrains.co.uk/search/advanced"
URL_TIME = "0000-2359"

current_date = datetime.date.today()
url_date = current_date.strftime("%Y/%m/%d")

def get_search_url(station):
	return "/".join([URL_PREFIX, station, url_date, URL_TIME])

for station in stations:
	print(get_search_url(station))
