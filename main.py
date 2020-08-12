import os
import ssl
import sys
import json
import smtplib
import spotipy
import webbrowser
import spotipy.util as util
from json.decoder import JSONDecodeError

# TODO: set environment variables USERNAME, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, ADMIN_EMAIL, ADMIN_EMAIL_PASSWORD

username = os.getenv('USERNAME')
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
redirect_uri = os.getenv('REDIRECT_URI')
admin_email = os.getenv('ADMIN_EMAIL')
admin_email_password = os.getenv('ADMIN_EMAIL_PASSWORD')


scope = 'playlist-modify-private playlist-modify-public user-follow-read ugc-image-upload'

token = util.prompt_for_user_token(username=username, scope=scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
sp = spotipy.Spotify(token)

files_used = []

def cleanDirectory(files_used):
    directory = 'C:/Users/bryan/Documents/vscode projects/spotify_development'
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            if filename not in files_used and filename != 'user_file.txt':
                os.remove(directory + '/' + filename)


def readFile():
    '''
    function opens user_file.txt and returns list of plahylist URIs
    '''
    file = open(r'user_file.txt')

    user_dict = {}
    
    user = ''

    for line in file:
        if line[0] == '#':
            continue

        if 'email:' in line:
            user = line.split()[1]
            user_dict[user] = []

        if 'spotify:playlist:' in line:
            uri = line.split()[0]
            user_dict[user].append(uri)

    return user_dict


def updatePlaylists(uri_list):
    '''
    1. read through uris
    2. for each playlist, use current uri to get playlist name
    3. open the 2 files with the playlist name ('x-current.txt / 'x-last_update.txt'), otherwise create new files
    4. update current.txt, add to current={set}
    5. iterate through last_updat.txt, last_updat={set} 
    6. compare sets, add new songs to message.txt
    '''
    if uri_list:

        update_dict = {}

        for index in range(0, len(uri_list)):
            
            playlist_items = sp.playlist_tracks(uri_list[index], fields='items', limit=100)
            name = sp.playlist(uri_list[index])['name']
            
            old_set = set()
            new_set = set()
            
            try:
                last_update = open(name + ' (last_update).txt', 'r', encoding='utf-8')
                files_used.append(last_update.name)
                for track in last_update:
                    if '\n' in track:
                        old_set.add(track[0:-1])
                    else:
                        old_set.add(track)
                last_update.close()
                
                current = open(name + ' (current).txt', 'w', encoding='utf-8')
                files_used.append(current.name)
                for song in playlist_items['items']:      # for song in list
                    track = song['track']['name'] + '  ―  ' + song['track']['artists'][0]['name']  #type str (ex. Super Rich Kids by Frank Ocean)
                    if '\n' in track:
                        new_set.add(track[0:-1])
                    else:
                        new_set.add(track)
                    
                    current.write(track)
                    current.write('\n')
                current.close()

                new_songs = []
                deleted_songs = []

                to_add = new_set - old_set
                for song in to_add:
                    new_songs.append(song)
                new_songs.sort(reverse=True, key=str.casefold)

                to_remove = old_set - new_set
                for song in to_remove:
                    deleted_songs.append(song)
                deleted_songs.sort(reverse=True, key=str.casefold)


                last_update = open(name + ' (last_update).txt', 'w', encoding='utf-8')
                current = open(name + ' (current).txt', 'r', encoding='utf-8')
                for song in current:      # for song in list
                    last_update.write(song)
                last_update.close()

                update_dict[name] = {'new_songs': new_songs, 'deleted_songs': deleted_songs}


            except FileNotFoundError:                       # new playlist, so create and update both playlist files and do nothing
                
                last_update = open(name + ' (last_update).txt', 'w', encoding='utf-8')
                current = open(name + ' (current).txt', 'w', encoding='utf-8')
                files_used.append(last_update.name)
                files_used.append(current.name)
                for song in playlist_items['items']:      # for song in list
                    last_update.write(song['track']['name'] + '  ―  ' + song['track']['artists'][0]['name'])
                    last_update.write('\n')
                    current.write(song['track']['name'] + '  ―  ' + song['track']['artists'][0]['name'])
                    current.write('\n')

                last_update.close()
                current.close()

                print('new files were created for {}'.format(name), file=sys.stderr)
                update_dict[name] = {'new_songs': '(new playlist)', 'deleted_songs': '(new playlist)'}

        return update_dict
    
    else:
        print('\nThis user has no playlists selected\n', file=sys.stderr)


def user_message(update_dict, uri_list):

    playlist_names = []
    for uri in uri_list:
        playlist_names.append(sp.playlist(uri)['name'])
    message = "Subject: Here's your update for this week.\n\n\n"

    for name in playlist_names:
        message += '[ Update for ' + name + ': ]\n\n'
        if update_dict[name]['new_songs'] == '(new playlist)':
            message += ('     Playlist has been added to the Updater! You will now get updates for this playlist.\n\n\n')
            continue
        new_songs = update_dict[name]['new_songs']
        deleted_songs = update_dict[name]['deleted_songs']

        if new_songs:
            message += '+++++Songs Added+++++\n\n'
    
            while len(new_songs) != 0:
                message += '+ ' + new_songs[-1] + '\n'
                new_songs.pop()
            message += '\n'

        else:
            message += '~ No new songs were added. ~\n\n\n'
        
        if deleted_songs:
            message += '\n'
            message += '-----Songs Removed-----\n\n'

            while len(deleted_songs) != 0:
                message += '- ' + deleted_songs[-1] + '\n'
                deleted_songs.pop()
            
            message += '\n\n\n'
        else:
            message += '~ No songs were deleted. ~\n\n\n'
            
        message += '\n'

    return message


def sendEmail(user_email, message):
    
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = admin_email  # Enter your address
    receiver_email = user_email  # Enter receiver address
    password = admin_email_password
    
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)

        server.sendmail(sender_email, receiver_email, message.encode('utf-8'))
        print("sent email", file=sys.stderr)



def main():
    user_dict = readFile()
    
    for user_email, uri_list in user_dict.items():
        print(user_email)
        update_dict = updatePlaylists(uri_list)
        print(update_dict)
        print()
        
        message = user_message(update_dict, uri_list)
        print(message)
        sendEmail(user_email, message)
        print(files_used)

    cleanDirectory(files_used)

        

if __name__ == "__main__":
    main()
