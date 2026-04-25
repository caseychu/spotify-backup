#!/usr/bin/env python3

import argparse 
import base64
import codecs
import hashlib
import http.client
import http.server
import json
import logging
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

logging.basicConfig(level=20, datefmt='%I:%M:%S', format='[%(asctime)s] %(message)s')


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
		code_verifier = SpotifyAPI._generate_code_verifier()
		code_challenge = SpotifyAPI._generate_code_challenge(code_verifier)
		state = secrets.token_urlsafe(16)
		redirect_uri = SpotifyAPI._redirect_uri()
		url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode({
			'response_type': 'code',
			'client_id': client_id,
			'scope': scope,
			'redirect_uri': redirect_uri,
			'code_challenge_method': 'S256',
			'code_challenge': code_challenge,
			'state': state
		})

		# Start listening before opening the browser so the redirect cannot race the server startup.
		server = SpotifyAPI._AuthorizationServer('127.0.0.1', SpotifyAPI._SERVER_PORT,
		                                          client_id, code_verifier, redirect_uri, state)
		logging.info(f'Logging in (click if it doesn\'t open automatically): {url}')
		webbrowser.open(url)
		try:
			while True:
				server.handle_request()
		except SpotifyAPI._Authorization as auth:
			return SpotifyAPI(auth.access_token)
		except SpotifyAPI._AuthorizationError as err:
			logging.error(f'Authorization failed: {err}')
			sys.exit(1)

	@staticmethod
	def _redirect_uri():
		return 'http://127.0.0.1:{}/redirect'.format(SpotifyAPI._SERVER_PORT)

	@staticmethod
	def _generate_code_verifier():
		alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
		return ''.join(secrets.choice(alphabet) for _ in range(64))

	@staticmethod
	def _generate_code_challenge(code_verifier):
		digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
		return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')

	@staticmethod
	def _exchange_authorization_code(client_id, code_verifier, redirect_uri, code):
		data = urllib.parse.urlencode({
			'client_id': client_id,
			'grant_type': 'authorization_code',
			'code': code,
			'redirect_uri': redirect_uri,
			'code_verifier': code_verifier
		}).encode('utf-8')
		req = urllib.request.Request('https://accounts.spotify.com/api/token', data=data)
		req.add_header('Content-Type', 'application/x-www-form-urlencoded')
		try:
			res = urllib.request.urlopen(req)
		except urllib.error.HTTPError as err:
			reader = codecs.getreader('utf-8')
			message = err.reason
			try:
				error = json.load(reader(err))
				message = error.get('error_description') or error.get('error') or message
			except Exception:
				pass
			raise SpotifyAPI._AuthorizationError(message)

		reader = codecs.getreader('utf-8')
		response = json.load(reader(res))
		access_token = response.get('access_token')
		if not access_token:
			raise SpotifyAPI._AuthorizationError('Spotify did not return an access token')
		return access_token
	
	# The port that the local server listens on. Don't change this,
	# as Spotify only will redirect to certain predefined URLs.
	_SERVER_PORT = 43019
	
	class _AuthorizationServer(http.server.HTTPServer):
		def __init__(self, host, port, client_id, code_verifier, redirect_uri, state):
			self.client_id = client_id
			self.code_verifier = code_verifier
			self.redirect_uri = redirect_uri
			self.state = state
			http.server.HTTPServer.__init__(self, (host, port), SpotifyAPI._AuthorizationHandler)
		
		# Disable the default error handling.
		def handle_error(self, request, client_address):
			raise
	
	class _AuthorizationHandler(http.server.BaseHTTPRequestHandler):
		def do_GET(self):
			parsed_url = urllib.parse.urlparse(self.path)
			if parsed_url.path != '/redirect':
				self.send_error(404)
				return

			params = urllib.parse.parse_qs(parsed_url.query)
			error = params.get('error', [None])[0]
			if error:
				error_description = params.get('error_description', [error])[0]
				self._send_authorization_error(400, f'Spotify returned: {error_description}')

			if params.get('state', [None])[0] != self.server.state:
				self._send_authorization_error(400, 'Spotify response state did not match the request')

			code = params.get('code', [None])[0]
			if not code:
				self._send_authorization_error(400, 'Spotify did not return an authorization code')

			try:
				access_token = SpotifyAPI._exchange_authorization_code(self.server.client_id,
				                                                     self.server.code_verifier,
				                                                     self.server.redirect_uri,
				                                                     code)
			except SpotifyAPI._AuthorizationError as err:
				self._send_authorization_error(500, f'Could not exchange authorization code: {err}')
			self.send_response(200)
			self.send_header('Content-Type', 'text/html')
			self.end_headers()
			self.wfile.write(b'<script>close()</script>Thanks! You may now close this window.')
			logging.info('Received access token from Spotify.')
			raise SpotifyAPI._Authorization(access_token)

		def _send_authorization_error(self, status, message):
			self.send_response(status)
			self.send_header('Content-Type', 'text/html')
			self.end_headers()
			self.wfile.write(message.encode('utf-8'))
			raise SpotifyAPI._AuthorizationError(message)
		
		# Disable the default logging.
		def log_message(self, format, *args):
			pass
	
	class _Authorization(Exception):
		def __init__(self, access_token):
			self.access_token = access_token

	class _AuthorizationError(Exception):
		pass


def format_duration(duration_ms):
	if duration_ms is None:
		return ''
	total_seconds = int(duration_ms) // 1000
	minutes, seconds = divmod(total_seconds, 60)
	hours, minutes = divmod(minutes, 60)
	if hours:
		return f'{hours}:{minutes:02}:{seconds:02}'
	return f'{minutes}:{seconds:02}'


def thumbnail_url(album):
	images = album.get('images') or []
	if not images:
		return None
	return min(images, key=lambda image: (image.get('height') or sys.maxsize) *
	                                  (image.get('width') or sys.maxsize)).get('url')


def simplified_track(track):
	album = track.get('album') or {}
	artists = track.get('artists') or []
	artist_names = [artist['name'] for artist in artists if artist.get('name')]
	return {
		'artist': ', '.join(artist_names),
		'name': track.get('name'),
		'album': album.get('name'),
		'thumbnail': thumbnail_url(album),
		'duration': format_duration(track.get('duration_ms')),
		'stream': None
	}


def track_uri_from_item(item):
	if not isinstance(item, dict):
		return None
	track = item.get('track')
	if not isinstance(track, dict):
		return None
	return track.get('uri')


def album_uri_from_item(item):
	if not isinstance(item, dict):
		return None
	album = item.get('album')
	if not isinstance(album, dict):
		return None
	return album.get('uri')


def dedupe_playlist_tracks(playlists):
	seen = set()
	removed = 0
	for playlist in playlists:
		deduped_tracks = []
		for item in playlist['tracks']:
			uri = track_uri_from_item(item)
			if uri:
				if uri in seen:
					removed += 1
					continue
				seen.add(uri)
			deduped_tracks.append(item)
		playlist['tracks'] = deduped_tracks
	return removed


def dedupe_albums(albums):
	seen = set()
	deduped_albums = []
	removed = 0
	for item in albums:
		uri = album_uri_from_item(item)
		if uri:
			if uri in seen:
				removed += 1
				continue
			seen.add(uri)
		deduped_albums.append(item)
	return deduped_albums, removed


def merged_json_export(user, playlists):
	tracks = []
	seen = set()
	for playlist in playlists:
		for item in playlist['tracks']:
			if not isinstance(item, dict):
				continue
			track = item.get('track')
			if track is None:
				continue
			uri = track_uri_from_item(item)
			if uri:
				if uri in seen:
					continue
				seen.add(uri)
			tracks.append(simplified_track(track))
	return {
		'name': 'Spotify Backup',
		'id': user['id'],
		'tracks': tracks
	}


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
	parser.add_argument('--client-id', default=os.environ.get('SPOTIFY_CLIENT_ID'),
	                    help='Spotify application client ID (default: SPOTIFY_CLIENT_ID or bundled client ID)')
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
		spotify = SpotifyAPI.authorize(client_id=args.client_id or '5c098bcc800e45d49e476265bc9b6934',
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
		playlist_data = spotify.list('me/playlists', {'limit': 50})
		logging.info(f'Found {len(playlist_data)} playlists')

		# List all tracks in each playlist
		for playlist in playlist_data:
			logging.info('Loading playlist: {name} ({tracks[total]} songs)'.format(**playlist))
			playlist['tracks'] = spotify.list(playlist['tracks']['href'], {'limit': 100})
		playlists += playlist_data

	duplicate_tracks = dedupe_playlist_tracks(playlists)
	if duplicate_tracks:
		logging.info(f'Removed {duplicate_tracks} duplicate tracks by Spotify URI')
	liked_albums, duplicate_albums = dedupe_albums(liked_albums)
	if duplicate_albums:
		logging.info(f'Removed {duplicate_albums} duplicate albums by Spotify URI')
	
	# Write the file.
	logging.info('Writing files...')
	with open(args.file, 'w', encoding='utf-8') as f:
		# JSON file.
		if args.format == 'json':
			export = merged_json_export(me, playlists)
			json.dump(export, f, ensure_ascii=False, indent=2)
			logging.info(f'Merged {len(export["tracks"])} unique tracks into JSON export')
		
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
