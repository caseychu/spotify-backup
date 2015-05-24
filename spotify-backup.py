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
				log('Couldn\'t load URL: {} ({})'.format(url, err))
				time.sleep(2)
				log('Trying again...')
		sys.exit(1)
	
	# The Spotify API breaks long lists into multiple pages. This method automatically
	# fetches all pages and joins them, returning in a single list of objects.
	def list(self, url, params={}):
		response = self.get(url, params)
		items = response['items']
		while response['next']:
			response = self.get(response['next'])
			items += response['items']
		return items
	
	# Pops open a browser window for a user to log in and authorize API access.
	@staticmethod
	def authorize(client_id, scope):
		webbrowser.open('https://accounts.spotify.com/authorize?' + urllib.parse.urlencode({
			'response_type': 'token',
			'client_id': client_id,
			'scope': scope,
			'redirect_uri': 'http://127.0.0.1:{}/redirect'.format(SpotifyAPI._SERVER_PORT)
		}))
	
		# Start a simple, local HTTP server to listen for the authorization token... (i.e. a hack).
		server = SpotifyAPI._AuthorizationServer('127.0.0.1', SpotifyAPI._SERVER_PORT)
		try:
			while True:
				server.handle_request()
		except SpotifyAPI._Authorization as auth:
			return SpotifyAPI(auth.access_token)
	
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
			# The Spotify API has redirected here, but access_token is hidden in the URL fragment.
			# Read it using JavaScript and send it to /token as an actual query string...
			if self.path.startswith('/redirect'):
				self.send_response(200)
				self.send_header('Content-Type', 'text/html')
				self.end_headers()
				self.wfile.write(b'<script>location.replace("token?" + location.hash.slice(1));</script>')
			
			# Read access_token and use an exception to kill the server listening...
			elif self.path.startswith('/token?'):
				self.send_response(200)
				self.send_header('Content-Type', 'text/html')
				self.end_headers()
				self.wfile.write(b'<script>close()</script>Thanks! You may now close this window.')
				raise SpotifyAPI._Authorization(re.search('access_token=([^&]*)', self.path).group(1))
			
			else:
				self.send_error(404)
		
		# Disable the default logging.
		def log_message(self, format, *args):
			pass
	
	class _Authorization(Exception):
		def __init__(self, access_token):
			self.access_token = access_token

def log(str):
	#print('[{}] {}'.format(time.strftime('%I:%M:%S'), str).encode(sys.stdout.encoding, errors='replace'))
	sys.stdout.buffer.write('[{}] {}\n'.format(time.strftime('%I:%M:%S'), str).encode(sys.stdout.encoding, errors='replace'))
	sys.stdout.flush()

def main():
	# Parse arguments.
	parser = argparse.ArgumentParser(description='Exports your Spotify playlists. By default, opens a browser window '
	                                           + 'to authorize the Spotify Web API, but you can also manually specify'
	                                           + ' an OAuth token with the --token option.')
	parser.add_argument('--token', metavar='OAUTH_TOKEN', help='use a Spotify OAuth token (requires the '
	                                           + '`playlist-read-private` permission)')
	parser.add_argument('--format', default='txt', choices=['json', 'txt'], help='output format (default: txt)')
	parser.add_argument('file', help='output filename', nargs='?')
	args = parser.parse_args()
	
	# If they didn't give a filename, then just prompt them. (They probably just double-clicked.)
	while not args.file:
		args.file = input('Enter a file name (e.g. playlists.txt): ')
	
	# Log into the Spotify API.
	if args.token:
		spotify = SpotifyAPI(args.token)
	else:
		spotify = SpotifyAPI.authorize(client_id='5c098bcc800e45d49e476265bc9b6934', scope='playlist-read-private')
	
	# Get the ID of the logged in user.
	me = spotify.get('me')
	log('Logged in as {display_name} ({id})'.format(**me))

	# List all playlists and all track in each playlist.
	playlists = spotify.list('users/{user_id}/playlists'.format(user_id=me['id']), {'limit': 50})
	for playlist in playlists:
		log('Loading playlist: {name} ({tracks[total]} songs)'.format(**playlist))
		playlist['tracks'] = spotify.list(playlist['tracks']['href'], {'limit': 100})
	
	# Write the file.
	with open(args.file, 'w', encoding='utf-8') as f:
		# JSON file.
		if args.format == 'json':
			json.dump(playlists, f)
		
		# Tab-separated file.
		elif args.format == 'txt':
			for playlist in playlists:
				f.write(playlist['name'] + '\r\n')
				for track in playlist['tracks']:
					f.write('{name}\t{artists}\t{album}\t{uri}\r\n'.format(
						uri=track['track']['uri'],
						name=track['track']['name'],
						artists=', '.join([artist['name'] for artist in track['track']['artists']]),
						album=track['track']['album']['name']
					))
				f.write('\r\n')
	log('Wrote file: ' + args.file)

if __name__ == '__main__':
	main()
