import Algorithmia
import yaml
import traceback
import seaborn as sb
import pandas as pd
import numpy as np
from io import BytesIO
import os
import requests 
import matplotlib.pyplot as plt
import seaborn as sns; sns.set(style="ticks", color_codes=True)

with open("bad_list.txt") as f:
    bad_list_array = f.read().splitlines()

def outputGraph():


    labels = 'positive', 'neutral', 'negative'
    values  = [sentiment_averages["positive"], sentiment_averages["neutral"], sentiment_averages["negative"]]
    fig1 = plt.figure() 
    values = np.asarray(values)
    fig1, ax1 = plt.subplots()
    ax1.pie(values, labels=labels, autopct='%1.1f%%',
        shadow=True, startangle=90)
    plt.title('Sentiment Analysis Graph')

    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    fig1.savefig('SentimentVisuals.png')

    curr_path = os.getcwd()
    new_path = curr_path + '/SentimentVisuals.png'

    my_file = {
    'file' : (new_path, open(new_path, 'rb'), 'png')
    }

    payload={
    "filename":"SentimentVisuals.png", 
    "token":CONFIG["SLACK_TOKEN"], 
    "channels":['#weworkchat'], 
    }

    r = requests.post("https://slack.com/api/files.upload", params=payload, files=my_file)

CONFIG = yaml.load(file("rtmbot.conf", "r"))

ALGORITHMIA_CLIENT = Algorithmia.client(CONFIG["ALGORITHMIA_KEY"])
ALGORITHM = ALGORITHMIA_CLIENT.algo('nlp/SocialSentimentAnalysis/0.1.4')

outputs = []

sentiment_results = {
    "negative": 0,
    "neutral": 0,
    "positive": 0
}

sentiment_averages = {
    "negative": 0,
    "neutral": 0,
    "positive": 0,
    "total": 0,
}


def display_current_mood(channel):
    reply = ""

    # something has gone wrong if we don't have a channel do nothing
    if not channel:
        return

    # loop over our stats and send them in the
    # best layout we can.
    for k, v in sentiment_averages.iteritems():
        if k == "total":
            continue
        reply += "{}: {}%\n ".format(k.capitalize(), v)

    outputs.append([channel, str(reply)])
    return

def process_message(data):

    text = data.get("text", None)

    if not text or data.get("subtype", "") == "channel_join":
        return

    # remove any odd encoding
    text = text.encode('utf-8')
    words = text.split()


    if "current mood?" in text:
        return display_current_mood(data.get("channel", None))

    if "bot function?" in text:
        outputs.append([data["channel"], "this bot analyzes sentiments in the group"])
    for i in range(len(words)):
        if words[i] in bad_list_array:
            outputs.append([data["channel"], "please refrain from using sensitive words!"])
    if "show graph?" in text:
        outputGraph()
        return
    # don't log the bot replies!
    if data.get("subtype", "") == "bot_message":
        return

    try:
        sentence = {
            "sentence": text
        }

        result = ALGORITHM.pipe(sentence)

        results = result.result[0]

        verdict = "neutral"
        compound_result = results.get('compound', 0)

        if compound_result == 0:
            sentiment_results["neutral"] += 1
        elif compound_result > 0:
            sentiment_results["positive"] += 1
            verdict = "positive"
        elif compound_result < 0:
            sentiment_results["negative"] += 1
            verdict = "negative"

        # increment counter so we can work out averages
        sentiment_averages["total"] += 1

        for k, v in sentiment_results.iteritems():
            if k == "total":
                continue
            if v == 0:
                continue
            sentiment_averages[k] = round(
                float(v) / float(sentiment_averages["total"]) * 100, 2)

        if compound_result < -0.75:
            outputs.append([data["channel"], "Easy there, negative Nancy!"])

        # print to the console what just happened
        print 'Comment "{}" was {}, compound result: {}'.format(text, verdict, compound_result)

    except Exception as exception:
        # a few things can go wrong but the important thing is keep going
        # print the error and then move on
        print "Something went wrong processing the text: {}".format(text)
        print traceback.format_exc(exception)