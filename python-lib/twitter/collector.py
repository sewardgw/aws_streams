import re
import datetime as dt
import json
import tweepy
import time

import sys
sys.path.append('.')
from kinesis import KinesisBasketballStreamer as KBS

consumer_key = "tZ5LF2MjGS1epE4V7wknCVzih"
consumer_secret = "0pqqFBu9cBnZlxhL9IXdq8kkCQhl3vzqUhzh13OOvxkdE8pEfy"
access_token = "1535457050-Ic7xQ3PsinpD3USly9O1PHvVbyfWNpB8gfzaxbJ"
access_token_secret = "ZeWMu0R7iYwkZPEVpzM55rrRDNPtkkjWrC0aMRFSNOvFb"

# Tweepy API
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

emoji_pattern = re.compile(
    u"(\ud83d[\ude00-\ude4f])|"  # emoticons
    u"(\ud83c[\udf00-\uffff])|"  # symbols & pictographs (1 of 2)
    u"(\ud83d[\u0000-\uddff])|"  # symbols & pictographs (2 of 2)
    u"(\ud83d[\ude80-\udeff])|"  # transport & map symbols
    u"(\ud83c[\udde0-\uddff])"  # flags (iOS)
    "+", flags=re.UNICODE)

class MyStreamListener(tweepy.StreamListener):
    def __init__(self):
        super(MyStreamListener, self).__init__()
        self.kbs = KBS()

    def on_status(self, status):
        self.get_user_tweet_info(status)

    def get_user_tweet_info(self, status):
        user_string = self.get_user_info_from_tweet(status)
        tweet_string = self.get_tweet_info(status)
        self.kbs.send_msg_to_stream('TwitterBBallUserStream', user_string)
        # self.kbs.send_msg_to_stream('bball_tweet_info', tweet_string)
        print(user_string)
        print(tweet_string)

    def get_user_info_from_tweet(self, tweet):
        user = tweet.user
        return_val = {
            'name': emoji_pattern.sub(r'', user.name),
            'location': user.location,
            'verified': user.verified,
            'created_at': user.created_at.strftime('%Y-%m-%d'),
            'user_age_at_post': (dt.datetime.now() - user.created_at).days,
            'tz': user.time_zone
        }
        return json.dumps(return_val) + '\n'

    def get_tweet_info(self, tweet):
        return_val = {
            'text': tweet.text,
            'about_lebron': 'lebron' in tweet.text.lower(),
            'source': tweet.source,
            'retweet_cnt': tweet.retweet_count,
            'created_at': tweet.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        return json.dumps(return_val) + '\n'


def run():
    myStreamListener = MyStreamListener()
    myStream = tweepy.Stream(auth = api.auth, listener=myStreamListener)
    myStream.filter(track=['basketball'])
