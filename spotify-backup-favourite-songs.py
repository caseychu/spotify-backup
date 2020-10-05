#!/usr/bin/env python3

import argparse 
import codecs
import http.client
import http.server
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

import importlib  
spotifyBackup = importlib.import_module('spotify-backup')
SpotifyAPI = spotifyBackup.SpotifyAPI
log = spotifyBackup.log

def main():
	# Parse arguments.
	parser = argparse.ArgumentParser(description='Exports your Spotify favourite songs. By default, opens a browser window '
	                                           + 'to authorize the Spotify Web API, but you can also manually specify'
	                                           + ' an OAuth token with the --token option.')
	parser.add_argument('--token', metavar='OAUTH_TOKEN', help='use a Spotify OAuth token (requires the '
	                                           + '`user-library-read` permission)')
	parser.add_argument('--format', default='txt', choices=['json', 'txt'], help='output format (default: txt)')
	parser.add_argument('--scope', default='user-library-read', choices=['user-library-read'], help='Spotify Scope to use, to get favorite songs.  (default: user-library-read)')
	parser.add_argument('file', help='output filename', nargs='?')
	args = parser.parse_args()
	
	# If they didn't give a filename, then just prompt them. (They probably just double-clicked.)
	while not args.file:
		args.file = input('Enter a file name (e.g. playlists.txt): ')
		args.format = args.file.split('.')[-1]
	
	# Log into the Spotify API.
	if args.token:
		spotify = SpotifyAPI(args.token)
	else:
		spotify = SpotifyAPI.authorize(client_id='5c098bcc800e45d49e476265bc9b6934', scope=args.scope)
	
	# Get the ID of the logged in user.
	me = spotify.get('me')
	log('Logged in as {display_name} ({id})'.format(**me))
	
	# List all favorite songs
	log('Loading favourite songs')
	favourites = spotify.list('me/tracks', {'limit': 50})
	
	# Write the file.
	log('Writing files...')
	with open(args.file, 'w', encoding='utf-8') as f:
		# JSON file.
		if args.format == 'json':
			json.dump(favourites, f)
		
		# Tab-separated file.
		elif args.format == 'txt':
			for track in favourites:
				f.write('{name}\t{artists}\t{album}\t{uri}\t{added_at}\n'.format(
					uri=track['track']['uri'],
					name=track['track']['name'],
					artists=', '.join([artist['name'] for artist in track['track']['artists']]),
					album=track['track']['album']['name'],
					added_at=track['added_at']
				))
	log('Wrote file: ' + args.file)

if __name__ == '__main__':
	main()
