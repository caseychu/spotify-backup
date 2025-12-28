#!/usr/bin/env python3

import argparse 
import codecs
import http.client
import http.server
import json
import logging
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import secrets
import string
import base64
import hashlib

logging.basicConfig(level=20, datefmt='%I:%M:%S', format='[%(asctime)s] %(message)s')


def generate_pkce_pair(length: int = 64) -> tuple[str, str]:
	# https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow#code-verifier
    chars = string.ascii_letters + string.digits
    code_verifier = ''.join(secrets.choice(chars) for _ in range(length))

    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = (
        base64.urlsafe_b64encode(digest)
        .rstrip(b"=")
        .decode("ascii")
    )

    return code_verifier, code_challenge

class SpotifyAPI:
	
	# Requires an OAuth token.
	def __init__(self, auth):
		self._auth = auth
	
	# Gets a resource from the Spotify API and returns the object.
	def get(self, url, params={}, tries=3):
		# Construct the correct URL.
		if not url.startswith('https://api.spotify.com/v1/'):
			url = 'https://api.spotify.com/v1/' + url
		if params:
			url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
	
		# Try the sending off the request a specified number of times before giving up.
		for _ in range(tries):
			try:
				req = urllib.request.Request(url)
				req.add_header('Authorization', 'Bearer ' + self._auth)
				res = urllib.request.urlopen(req)
				reader = codecs.getreader('utf-8')
				return json.load(reader(res))
			except Exception as err:
				logging.info('Couldn\'t load URL: {} ({})'.format(url, err))
				time.sleep(2)
				logging.info('Trying again...')
		sys.exit(1)
	
	# The Spotify API breaks long lists into multiple pages. This method automatically
	# fetches all pages and joins them, returning in a single list of objects.
	def list(self, url, params={}):
		last_log_time = time.time()
		response = self.get(url, params)
		items = response['items']

		while response['next']:
			if time.time() > last_log_time + 15:
				last_log_time = time.time()
				logging.info(f"Loaded {len(items)}/{response['total']} items")

			response = self.get(response['next'])
			items += response['items']
		return items
	
	# Pops open a browser window for a user to log in and authorize API access.
	@staticmethod
	def authorize(client_id, scope):
		code_verifier, code_challenge = generate_pkce_pair()

		url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode({
			'response_type': 'code',
			'client_id': client_id,
			'scope': scope,
			'redirect_uri': 'http://127.0.0.1:{}/redirect'.format(SpotifyAPI._SERVER_PORT),
			'code_challenge_method': 'S256',
			'code_challenge': code_challenge,
		})
		logging.info(f'Logging in (click if it doesn\'t open automatically): {url}')
		webbrowser.open(url)
	
		# Start a simple, local HTTP server to listen for the authorization token... (i.e. a hack).
		server = SpotifyAPI._AuthorizationServer('127.0.0.1', SpotifyAPI._SERVER_PORT)
		try:
			while True:
				server.handle_request()
		except SpotifyAPI._Authorization as auth:
			# https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow#request-an-access-token
			body = bytes(urllib.parse.urlencode({
				'grant_type': 'authorization_code',
				'code': auth.access_code,
				'redirect_uri': 'http://127.0.0.1:{}/redirect'.format(SpotifyAPI._SERVER_PORT),
				'client_id': client_id,
				'code_verifier': code_verifier,
			}), encoding='utf-8')
			req = urllib.request.Request("https://accounts.spotify.com/api/token", data=body)
			req.add_header('content-type', 'application/x-www-form-urlencoded')
			res = urllib.request.urlopen(req)
			reader = codecs.getreader('utf-8')
			return SpotifyAPI(json.load(reader(res))['access_token'])
	
	# The port that the local server listens on. Don't change this,
	# as Spotify only will redirect to certain predefined URLs.
	_SERVER_PORT = 43019
	
	class _AuthorizationServer(http.server.HTTPServer):
		def __init__(self, host, port):
			http.server.HTTPServer.__init__(self, (host, port), SpotifyAPI._AuthorizationHandler)
		
		# Disable the default error handling.
		def handle_error(self, request, client_address):
			raise
	
	class _AuthorizationHandler(http.server.BaseHTTPRequestHandler):
		def do_GET(self):
			# Read access_token and use an exception to kill the server listening...
			if self.path.startswith('/redirect?code'):
				self.send_response(200)
				self.send_header('Content-Type', 'text/html')
				self.end_headers()
				self.wfile.write(b'<script>close()</script>Thanks! You may now close this window.')

				code = re.search('code=([^&]*)', self.path).group(1)
				logging.info(f'Received access code from Spotify: {code}')

				raise SpotifyAPI._Authorization(code)
			else:
				self.send_error(404)
		
		# Disable the default logging.
		def log_message(self, format, *args):
			pass
	
	class _Authorization(Exception):
		def __init__(self, access_code):
			self.access_code = access_code


def main():
	# Parse arguments.
	parser = argparse.ArgumentParser(description='Exports your Spotify playlists. By default, opens a browser window '
	                                           + 'to authorize the Spotify Web API, but you can also manually specify'
	                                           + ' an OAuth token with the --token option.')
	parser.add_argument('--token', metavar='OAUTH_TOKEN', help='use a Spotify OAuth token (requires the '
	                                                         + '`playlist-read-private` permission)')
	parser.add_argument('--dump', default='playlists', choices=['liked,playlists', 'playlists,liked', 'playlists', 'liked'],
	                    help='dump playlists or liked songs, or both (default: playlists)')
	parser.add_argument('--format', default='txt', choices=['json', 'txt'], help='output format (default: txt)')
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
		spotify = SpotifyAPI.authorize(client_id='5c098bcc800e45d49e476265bc9b6934',
		                               scope='playlist-read-private playlist-read-collaborative user-library-read')
	
	# Get the ID of the logged in user.
	logging.info('Loading user info...')
	me = spotify.get('me')
	logging.info('Logged in as {display_name} ({id})'.format(**me))

	playlists = []
	liked_albums = []

	# List liked albums and songs
	if 'liked' in args.dump:
		logging.info('Loading liked albums and songs...')
		liked_tracks = spotify.list('me/tracks', {'limit': 50})
		liked_albums = spotify.list('me/albums', {'limit': 50})
		playlists += [{'name': 'Liked Songs', 'tracks': liked_tracks}]

	# List all playlists and the tracks in each playlist
	if 'playlists' in args.dump:
		logging.info('Loading playlists...')
		playlist_data = spotify.list('users/{user_id}/playlists'.format(user_id=me['id']), {'limit': 50})
		logging.info(f'Found {len(playlist_data)} playlists')

		# List all tracks in each playlist
		for playlist in playlist_data:
			logging.info('Loading playlist: {name} ({tracks[total]} songs)'.format(**playlist))
			playlist['tracks'] = spotify.list(playlist['tracks']['href'], {'limit': 100})
		playlists += playlist_data
	
	# Write the file.
	logging.info('Writing files...')
	with open(args.file, 'w', encoding='utf-8') as f:
		# JSON file.
		if args.format == 'json':
			json.dump({
				'playlists': playlists,
				'albums': liked_albums
			}, f)
		
		# Tab-separated file.
		else:
			f.write('Playlists: \r\n\r\n')
			for playlist in playlists:
				f.write(playlist['name'] + '\r\n')
				for track in playlist['tracks']:
					if track['track'] is None:
						continue
					f.write('{name}\t{artists}\t{album}\t{uri}\t{release_date}\r\n'.format(
						uri=track['track']['uri'],
						name=track['track']['name'],
						artists=', '.join([artist['name'] for artist in track['track']['artists']]),
						album=track['track']['album']['name'],
						release_date=track['track']['album']['release_date']
					))
				f.write('\r\n')
			if len(liked_albums) > 0:
				f.write('Liked Albums: \r\n\r\n')
				for album in liked_albums:
					uri = album['album']['uri']
					name = album['album']['name']
					artists = ', '.join([artist['name'] for artist in album['album']['artists']])
					release_date = album['album']['release_date']
					album = f'{artists} - {name}'

					f.write(f'{name}\t{artists}\t-\t{uri}\t{release_date}\r\n')

	logging.info('Wrote file: ' + args.file)

if __name__ == '__main__':
	main()
