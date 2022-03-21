from flask import Flask, render_template, redirect, session, url_for, request, flash
from flask_mysqldb import MySQL
import MySQLdb
import tweepy
import emoji
import unicodedata
import _json
from dateutil import parser
import sys
import os
import csv
import re
from joblib import load

# load the pipeline object
pipeline = load("dep_classification.joblib")

app = Flask(__name__)
app.secret_key = "12345"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "Type your DB_NAME"

db = MySQL(app)

# Twitter Api Credentials
consumerKey = "consumerKey"
consumerSecret = "consumerSecret"
accessToken = "accessToken"
accessTokenSecret = "accessTokenSecret"

# Create the authentication object
authenticate = tweepy.OAuthHandler(consumerKey, consumerSecret)

# Set the access token and access token secret
authenticate.set_access_token(accessToken, accessTokenSecret)

# Creating the API object while passing in auth information
api = tweepy.API(authenticate, wait_on_rate_limit=True)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'username' in request.form and 'psw' in request.form:
            username = request.form['username']
            psw = request.form['psw']
            cursor = db.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT * FROM user WHERE userName=%s AND psw=%s", (username, psw))
            info = cursor.fetchone()
            print(info)
            if info is not None:
                if info['userName'] == username and info['psw'] == psw:
                    print('correct')
                    session['loginsuccess'] = True
                    
                    cursor.execute("SELECT twitter_userName FROM user WHERE userName= %s", [username])
                    info2 = cursor.fetchone()
                    twitter_name = info2['twitter_userName']
                    session['twitter_name'] = twitter_name
                    print(twitter_name)
                    # Extract 100 tweets from the twitter user
                    posts = api.user_timeline(screen_name=twitter_name, count=1000, lang="si", tweet_mode="extended")
                    # Print the last 5 tweets
                    print("Show the 5 recent tweets:\n")
                    i = 1

                    #To create the 'tweets' table : > CREATE TABLE tweets (tweet_id BIGINT, tweet varchar(510) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,user_name varchar(510), user_id int, created_at DATETIME, inserted_at DATETIME, language varchar(25), label varchar(50))
                    for tweet in posts[:]:
                        print(str(i) + ') ' + tweet.full_text)
                        print('Created @', tweet.created_at)
                        print('tweet Id', tweet.id)
                        print('user Id', tweet.user.id)
                        session['twitter_user_id'] = tweet.user.id
                        # remove Emojis from the tweet
                        emoji_removed_tweet = get_emoji_removed_tweet(tweet.full_text)
                        print("Emoji Removed Tweet : ", emoji_removed_tweet)

                        # clean tweet
                        cleaned_tweet = get_cleaned_text(emoji_removed_tweet)
                        print(cleaned_tweet)

                        if not cleaned_tweet:
                            cleaned_tweet="Empty"

                        if not cleaned_tweet.strip():
                            cleaned_tweet = "Empty"

                        lang = ""
                        label = ""

                        # remove duplicate entries
                        cursor.execute("SELECT tweet_id FROM tweets WHERE tweet=%s", [emoji_removed_tweet])
                        if cursor.rowcount == 0:
                            # x=cleaned_tweet.lstrip()

                            if cleaned_tweet != cleaned_tweet.lstrip():
                                print(cleaned_tweet)
                                if is_sinhala(cleaned_tweet):
                                    lang = "Sinhala"
                                    #print(model.classify_tweet([cleaned_tweet]))
                                    print(pipeline.predict([cleaned_tweet]))

                                    #for j in model.classify_tweet([cleaned_tweet]):
                                    for j in pipeline.predict([cleaned_tweet]):
                                        if j == 1:
                                            label = "depressive tweet"
                                        else:
                                            label = "non-depressive tweet"
                                else:
                                    lang = "non-Sinhala"
                                    label = "Not-classified"

                            else:
                                if is_sinhala(cleaned_tweet):
                                    lang = "Sinhala"
                                    print(pipeline.predict([cleaned_tweet]))

                                    for j in pipeline.predict([cleaned_tweet]):
                                        if j == 1:
                                            label = "depressive tweet"
                                        else:
                                            label = "non-depressive tweet"
                                else:
                                    lang = "non-Sinhala"
                                    label = "Not-classified"

                            cursor.execute("INSERT INTO tweets (tweet_id, tweet, user_name, user_id, language, label, created_at, inserted_at) "
                                           "VALUES (%s, %s, %s, %s, %s, %s, %s, NOW());",
                                           (tweet.id, emoji_removed_tweet, tweet.author.screen_name, tweet.author.id, lang, label, tweet.created_at))
                            db.connection.commit()

                        i = i + 1
                    return redirect(url_for('profile'))
                else:
                    print('wrong')
            else:
                session['loginsuccess'] = False
                flash('Invalid password or user name provided')
                return redirect(url_for('index'))

    return render_template("login.html")

@app.route('/new', methods=['GET', 'POST'])
def new_user():
    if request.method == "POST":
        if "user_name" in request.form and "psw" in request.form and "email" in request.form and "twitter_user_name" in request.form:
            username = request.form['user_name']
            psw = request.form['psw']
            email = request.form['email']
            twitter_usr = request.form['twitter_user_name']
            cur = db.connection.cursor(MySQLdb.cursors.DictCursor)
            cur.execute("INSERT INTO `user` (`userName`, `email`, `psw`, `twitter_userName`) VALUES (%s,%s,%s,%s)",
                        (username, email, psw, twitter_usr))
            db.connection.commit()
            return redirect(url_for('index'))

    return render_template("register.html")


@app.route('/new/profile')
def profile():
    if session['loginsuccess'] == True:
        cursor = db.connection.cursor(MySQLdb.cursors.DictCursor)
        user_name=session['twitter_name']
        cursor.execute("SELECT * FROM tweets WHERE user_name=%s",[user_name])
        info3=cursor.fetchall()
        print(info3)
        return render_template('profile.html', data=info3)


@app.route('/new/logout')
def logout():
    session.pop('loginsuccess', None)
    return redirect(url_for('index'))

@app.route('/new/filter')
def filter():
    if session['loginsuccess'] == True:
        cursor = db.connection.cursor(MySQLdb.cursors.DictCursor)
        user_name=session['twitter_name']
        cursor.execute("SELECT * FROM tweets WHERE user_name=%s AND label=%s",(user_name, "depressive tweet"))
        info4=cursor.fetchall()
        print(info4)
    return render_template('filter_tweets.html', data=info4)

def get_emoji_removed_tweet(text):
    return emoji.get_emoji_regexp().sub(r'', text)

def get_cleaned_text(text):
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r'^RT @\w*: ', ' ', text)
    text = re.sub(r'@\w*', ' ', text)
    text = re.sub(r'[!@#&*$.?,]', ' ', text)
    text = re.sub(r'\n', ' ', text)
    text = re.sub("'", '', text)
    text = re.sub(r'[a-z]', '', text)
    text = re.sub(r'[A-Z]', '', text)
    return (text)

def is_sinhala(tweet):
    return 'SINHALA' in unicodedata.name(tweet.strip()[0])

if __name__ == '__main__':
    app.run(debug=True)
