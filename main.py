import os
import ssl
import sys
import json
import smtplib
import spotipy
import datetime
import webbrowser
import spotipy.util as util
from json.decoder import JSONDecodeError

import sqlite3

from cred import getCredentials

# create another file in current directory called "cred.py" and paste in this function, and fill in the appropriate credentials for the API and sender email
############################
# def getCredentials(username, client_id, client_secret, redirect_uri, admin_email, admin_email_password):
#     username = YOUR_USERNMAE
#     client_id = YOUR_CLIENT_ID
#     client_secret = YOUR CLIENT_SECRET
#     redirect_uri = YOUR_REDIRECT_URI
#     admin_email = YOUR_ADMIN_EMAIL           #email you want to send the updates from
#     admin_email_password = YOUR_ADMIN_EMAIL_PASSWORD
#     return username, client_id, client_secret, redirect_uri, admin_email, admin_email_password
################################

username=''
client_id=''
client_secret=''
redirect_uri=''
admin_email=''
admin_email_password=''
# get credentials from cred.py file
username, client_id, client_secret, redirect_uri, admin_email, admin_email_password = getCredentials(username, client_id, client_secret, redirect_uri, admin_email, admin_email_password)

scope = 'playlist-modify-private playlist-modify-public user-follow-read ugc-image-upload'

token = util.prompt_for_user_token(username, scope, client_id, client_secret, redirect_uri)     #get token

sp = spotipy.Spotify(token)         #declare spotipy token as a global variable

#connect to SQLite database
script_directory = os.path.dirname(os.path.abspath(__file__))
dbPath = os.path.join(script_directory, 'playlists.db')
conn = sqlite3.connect(dbPath)     

c = conn.cursor()               # initialize cursor


def readFile(user_file):
    '''
    Opens user_file.txt and returns list of plahylist URIs

    Parameters: IO TextWrapper file 'user.txt'
    Return: dictionary of users as keys and lists of playlist uris as respective values
    '''
    mainTable_dict = {}

    # iterate through user_file.txt and assign a list value of all uris to each user 
    line = user_file.readline()

    while line != "END":
        if line[0] == '#': 
            line = user_file.readline()         # ignore lines with # as the first character in the line
            continue
        
        elif 'email:' in line:
            user = line.split()[1]
            line = user_file.readline()
            while line != '\n':
                if 'https://open.spotify.com/playlist/' in line:
                    start = line.rindex('/')+1
                    end = line.rindex('?')
                    playlist_id = line[start:end]
                    if playlist_id not in mainTable_dict:
                        mainTable_dict[playlist_id] = [user]
                    else:
                        if user not in mainTable_dict[playlist_id]:
                            mainTable_dict[playlist_id].append(user)
                    line = user_file.readline()
                else:
                    line = user_file.readline()
        else:
            line = user_file.readline()

    return mainTable_dict


def updateMainTable(mainTable_dict):
    '''
    Update the main table that has the playlist_idS and their respective users

    Parameters: mainTable_dict - dictionary { playlist playlist_id : users }
    Return: None
    '''
    c.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='MainTable'")

    last_date = ''

    if c.fetchone()[0]:
        c.execute("SELECT * FROM MainTable LIMIT 1")

        last_date = c.fetchone()[3]

        c.execute("DROP TABLE MainTable")
        conn.commit()
    else:
        last_date = datetime.datetime.utcnow().isoformat()[:-7] + 'Z'    #Get current datetime

    c.execute("CREATE TABLE MainTable (playlist_name text, playlist_id text, users text, last_update text)")
    conn.commit()

    for playlist_id in mainTable_dict.keys():
        user_string = ''
        for user in mainTable_dict[playlist_id]:
            user_string += user
            user_string += ','
        playlist_name = sp.playlist(playlist_id)['name'].encode('utf-8')

        c.execute("INSERT INTO MainTable VALUES (?, ?, ?, ?)", (playlist_name, playlist_id, user_string, last_date))
        conn.commit()
    

def getNewTracks(mainTable_dict):
    '''
    Get all tracks added in the past week

    Parameters: mainTable_dict - dictionary { playlist playlist_id : users }
    Return: newTracks_dict - dictionary { playlist playlist_id : [new tracks] }
    '''
    newTracks_dict = {}

    for playlist_id in mainTable_dict.keys():
        
        newTracks_dict[playlist_id] = []

        playlist_items = sp.playlist_tracks(playlist_id)
        raw_tracks = playlist_items['items']

        # get tracks past 100-track limit
        while playlist_items['next']:
            playlist_items = sp.next(playlist_items)
            raw_tracks.extend(playlist_items['items'])
        
        c.execute("SELECT * FROM MainTable LIMIT 1")
        last_date = c.fetchone()[3]

        for track in raw_tracks:
            if track['track']:
                if track['added_at'] > last_date:

                    formatted_track = track['track']['name'] + '   -   ' + track['track']['artists'][0]['name']  #type str (ex. Super Rich Kids //  Frank Ocean)
                    if track['is_local']:
                        formatted_track += " ***Locally-added track may be unavailable*** "
                    newTracks_dict[playlist_id].append(formatted_track)

    return newTracks_dict


def composeMessages(mainTable_dict, newTracks_dict):
    '''
    Composing and sending emails to all users

    Parameters: mainTable_dict - dictionary { URL : [users] }, newTracks_dict - dictionary { URL : [new Tracks] }
    Return: message_dict - dictionary { user : str(message) }
    '''
    message_dict = {}

    for playlist_id in mainTable_dict.keys():
        if newTracks_dict[playlist_id]:
            user_list = mainTable_dict[playlist_id]
            for user in user_list:
                if user not in message_dict:
                    message_dict[user] = "Subject: Here's your update for this week.\n\n"
                    message_dict[user] += "Playlists with songs added this week:\n\n\n\n"

                name = sp.playlist(playlist_id)['name']
                added_message = 'NEW SONGS ADDED TO "{}":\n\n\n'.format(name)
                for song in newTracks_dict[playlist_id]:
                    added_message += '     {}\n\n'.format(song)
                added_message += "\n\n"
                message_dict[user] += added_message
    
    all_users = set()                   # create a message for users who don't have any updates for the given week
    for playlist_id in mainTable_dict.keys():
        for user in mainTable_dict[playlist_id]:
            all_users.add(user)

    for user in all_users:
        if user not in message_dict:
            message_dict[user] = "Subject: Here's your update for this week.\n\n"
            message_dict[user] += "We looked throught the playlists that you've selected to get updates on, but none of those playlists have any new songs added this week.\n"
        
        message_dict[user] += "Check in next week for more updates."
         
    return message_dict


def emailMessages(message_dict):
    '''
    Send Each user their message

    Paramters: message_dict - dictionary { user : str(message) }
    Return: None
    '''
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = admin_email  # Enter your address
    password = admin_email_password
    
    context = ssl.create_default_context()      #encrypt message
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        
        server.login(sender_email, password)        # login to email

        for receiver_email in message_dict.keys():
            message = message_dict[receiver_email]
            try:
                server.sendmail(sender_email, receiver_email, message.encode('utf-8'))      #send email with utf-8 encodeding to account for speical charecters / emojis
                print("SUCCESS: email sent!", file=sys.stderr)
            except: 
                print('FAILURE: email failed to send')


def main():
    
    user_file = open(r'user_file.txt')             
    mainTable_dict = readFile(user_file)          # read user data from user_file.txt
    
    updateMainTable(mainTable_dict)               # update the table that holds user info
    
    newTracks_dict = getNewTracks(mainTable_dict)       # get the tracks to each playlist since the last update

    message_dict = composeMessages(mainTable_dict, newTracks_dict)     # compose a custom message for each user

    emailMessages(message_dict)                     # send out all emails

    last_date = datetime.datetime.utcnow().isoformat()[:-7] + 'Z'    # Update last date updated in table with current datetime
    c.execute("UPDATE MainTable SET last_update=?", (last_date,))
    conn.commit()

    user_file.close()


if __name__ == "__main__":
    main()