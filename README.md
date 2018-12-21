# NuclearTrains

```
a bot that auto-trainspots british nuclear waste trains 
may be the most ballardian thing I've seen on this hell site
```
-- twitter user [@cszabla](https://twitter.com/cszabla/status/1072663099256254464?s=19) 12/12/18

This is powered by RealTimeTrains http://www.realtimetrains.co.uk/
API access for RTT is registered for at https://api.rtt.io/

Thank you to Tom Cairns and the rest of the RTT for providing this service and for being speedy with tech support.
Shut up and let them take your money https://secure.realtimetrains.co.uk/fundraising/

## Introduction

Using real-time open data from network rail via the Real Time Trains API, Nuclear Trains is a twitter bot that tweets when a freight train departs a nuclear power plant: including a link detailing its time and position.

Trains are not guaranteed to be pulling nuclear waste flasks, and even if they are, the flasks may or may not be full.

**This project has no stance on nuclear energy, and its main objective is to provide a quantitative and real-time source of information about the movement of nuclear waste in the UK.**

Check out our twitter here [@nuclearTrains](https://twitter.com/nucleartrains). We're working on a slightly less crap website at the moment

Any more features/whatnot you can tweet at us or raise an issue here. 

## Usage

By default this is set up to use the `servicev2` and `searchv2` endpoints because these are the endpoint that work for Freight Trains which is what we need for our application. 
If you are using this module and haivng problems getting resonpses from the server and your username and password are definitely correct, try changing

```realtimetrains.py
30 LOCATION_SEARCH = "searchv2"
31 TRAIN_SEARCH = "servicev2"
``` 
to 
```realtimetrains.py
30 LOCATION_SEARCH = "search"
31 TRAIN_SEARCH = "service"
``` 

### Twitter bot usage
```
$ python3 main.py /path/to/RTT_Auth.json /path/to/twitter_auth.json
```

More detailed documentaion coming soon maybe. 