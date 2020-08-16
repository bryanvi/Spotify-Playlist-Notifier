import os
import ssl
import sys
import json
import smtplib
import spotipy
import webbrowser
import spotipy.util as util
from json.decoder import JSONDecodeError

from cred import getCredentials

# create another file called "cred.py" and paste in this function, and fill in the appropriate credntials for the API and sender email

# def getCredentials(username, client_id, client_secret, redirect_uri, admin_email, admin_email_password):
#     username = YOUR_USERNMAE
#     client_id = YOUR_CLIENT_ID
#     client_secret = YOUR CLIENT_SECRET
#     redirect_uri = YOUR_REDIRECT_URI
#     admin_email = YOUR_ADMIN_EMAIL           #email you want to send the updates from
#     admin_email_password = YOUR_ADMIN_EMAIL_PASSWORD
#     return username, client_id, client_secret, redirect_uri, admin_email, admin_email_password
username=''
client_id=''
client_secret=''
redirect_uri=''
admin_email=''
admin_email_password=''

username, client_id, client_secret, redirect_uri, admin_email, admin_email_password = getCredentials(username, client_id, client_secret, redirect_uri, admin_email, admin_email_password)

scope = 'playlist-modify-private playlist-modify-public user-follow-read ugc-image-upload'

token = util.prompt_for_user_token(username=username, scope=scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
sp = spotipy.Spotify(token)


files_used = []
def cleanDirectory(files_used):
    '''
    Delete unused text files in directory

    parameters: list of files used
    return: None
    '''
    directory = 'C:/Users/bryan/Documents/vscode projects/spotify_development'
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            if filename not in files_used and filename != 'user_file.txt':
                os.remove(directory + '/' + filename)


def readFile(file):
    '''
    Opens user_file.txt and returns list of plahylist URIs

    Parameters: IO TextWrapper file 'user.txt'
    Return: dictionary of users as keys and lists of playlist uris as respective values
    '''
    user_dict = {}
    
    user = ''

    # iterate through user_file.txt and assign a list value of all uris to each user 
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



def getAllTracks(sp, playlist_id, all_tracks):
    '''
    Get all tracks from playlist

    '''

    playlist_items = sp.playlist_tracks(playlist_id)
    raw_tracks = playlist_items['items']
    while playlist_items['next']:
        playlist_items = sp.next(playlist_items)
        raw_tracks.extend(playlist_items['items'])
    
    for song in raw_tracks:      # for song in playlist, add songs in current plalist to new_set
        track = song['track']['name'] + '  ―  ' + song['track']['artists'][0]['name']  #type str (ex. Super Rich Kids by Frank Ocean)
        all_tracks.append(track)


    return all_tracks



def updatePlaylists(uri_list):
    '''
    Read throught the user's playlist uris. If the playlist uri was recently added to the list of
    playlists to get updated on, create two text files of the playlist tracks. If the files have already been created, 
    compare the two text files to check what songs have been added or deleted.

    Paramters: a list of plalist uris
    Return: a dictionary holding all the songs that were added since the last update and the songs that were deleted
    '''
    if uri_list:

        update_dict = {}

        
        for index in range(0, len(uri_list)):
            # for each playlist, use current uri to get playlist name            
            name = sp.playlist(uri_list[index])['name']
            
            # create sets to compare later on
            old_set = set()
            new_set = set()
            
            # attempt to open playlist track files if the playlist had already had updates made on it
            try:
                last_update = open(name + ' (last_update).txt', 'r', encoding='utf-8')
                files_used.append(last_update.name)     #file is being used
                
                for track in last_update:           # add tracks from previous update to old_set
                    if '\n' in track:
                        old_set.add(track[0:-1])
                    else:
                        old_set.add(track)
                last_update.close()
                
                current = open(name + ' (current).txt', 'w', encoding='utf-8')
                files_used.append(current.name)

                all_tracks = []
                all_tracks = getAllTracks(sp, uri_list[index], all_tracks)

                for track in all_tracks:      # for song in playlist, add songs in current plalist to new_set
                    new_set.add(track)
                    
                    current.write(track)        # update text file of songs in current playlist
                    current.write('\n')
                current.close()

                new_songs = []
                deleted_songs = []

                to_add = new_set - old_set      # if there are songs in new_set that aren't in old_set, add to list of new songs
                for song in to_add:
                    new_songs.append(song)
                
                new_songs.sort(reverse=True, key=str.casefold)      #sort songs list in reverse alphabetical order

                to_remove = old_set - new_set   #if there are songs in old_set that aren't in new_set, add to list of deleted_songs
                for song in to_remove:
                    deleted_songs.append(song)
                
                deleted_songs.sort(reverse=True, key=str.casefold)      #sort songs list in reverse alphabetical order


                last_update = open(name + ' (last_update).txt', 'w', encoding='utf-8')      # update last_update.txt to be the same as current update
                current = open(name + ' (current).txt', 'r', encoding='utf-8')
                for song in current:      # for song in list
                    last_update.write(song)
                last_update.close()

                update_dict[name] = {'new_songs': new_songs, 'deleted_songs': deleted_songs}        #create dictionary to return


            except FileNotFoundError:              # new playlist, so create and update both playlist files and do nothing else
                
                last_update = open(name + ' (last_update).txt', 'w', encoding='utf-8')
                current = open(name + ' (current).txt', 'w', encoding='utf-8')

                files_used.append(last_update.name)     #files are being user, so don't delete
                files_used.append(current.name)

                all_tracks = []
                all_tracks = getAllTracks(sp, uri_list[index], all_tracks)
                for track in all_tracks:      # for song in list

                    # create two files of all songs in playlist to compare for next update
                    last_update.write(track)
                    last_update.write('\n')
                    current.write(track)
                    current.write('\n')

                last_update.close()
                current.close()

                update_dict[name] = {'new_songs': '(new playlist)', 'deleted_songs': '(new playlist)'}      #create dictionary to return, but with no songs

        return update_dict



def user_message(update_dict, uri_list):
    '''
    Writes neatly formatted update message to send in an email

    Parameters: dictionary of playlists to update, list of uris to get playlist names
    Return: string message to send in email
    '''
    #get playlist names
    playlist_names = []
    for uri in uri_list:
        playlist_names.append(sp.playlist(uri)['name'])

    message = "Subject: Here's your update for this week.\n\n\n"        # begin message

    for name in playlist_names:
        message += '[ Update for ' + name + ': ]\n\n'

        # check to see if playlist has just been added to user_file.txt
        if update_dict[name]['new_songs'] == '(new playlist)':
            message += ('     Playlist has been added to the Updater! You will now get updates for this playlist.\n\n\n')
            continue


        new_songs = update_dict[name]['new_songs']
        deleted_songs = update_dict[name]['deleted_songs']

        # write to message the songs that have been added since the last update
        if new_songs:
            message += '+++++Songs Added+++++\n\n'
            while len(new_songs) != 0:
                message += '+ ' + new_songs[-1] + '\n'
                new_songs.pop()
            message += '\n'
        else:               # if no songs have been added, tell user
            message += '~ No new songs were added. ~\n\n\n'
        
        # write to message the songs that have been deleted since the last update
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

    
    context = ssl.create_default_context()      #encrypt message
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        
        server.login(sender_email, password)        # login to email

        try:
            server.sendmail(sender_email, receiver_email, message.encode('utf-8'))      #send email with utf-8 encodeding to account for speical charecters / emojis
            print("sent email", file=sys.stderr)
        except: 
            print('email failed to send')



def main():

    file = open(r'user_file.txt')
    user_dict = readFile(file)          # get users and the playlists they want to be updates on
    
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