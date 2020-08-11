import os
import ssl
import sys
import json
import smtplib
import spotipy
import webbrowser
import spotipy.util as util
from json.decoder import JSONDecodeError

# username = os.environ.get('ACCOUNT_OWNER')
# client_id = os.environ.get('CLIENT_ID')
# client_secret = os.environ.get('CLIENT_SECRET')
# redirect_uri = os.environ.get('REDIRECT_URI')

# print(username)
# print(client_id)
# print(client_secret)
# print(redirect_uri)

username = 'bryanvi'
client_id = '3e23d0e194824d46aa6a3a8a821ea72f'
client_secret = '61703860a06941d588248515ecad9452'
redirect_uri = 'http://localhost:8080/'
scope = 'playlist-modify-private playlist-modify-public user-follow-read ugc-image-upload'

token = util.prompt_for_user_token(username=username, scope=scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
sp = spotipy.Spotify(token)

playlists = sp.user_playlists('bryanvi', limit=50)

for item in playlists.items():
    print(item)