#!/usr/bin/env python3

import sys, os, re, time
import argparse
import codecs
import urllib.parse, urllib.request, urllib.error
import http.server
import webbrowser
import json
import xspf

class SpotifyAPI:
	
	# Requires an OAuth token.
	def __init__(self, auth):
		self._auth = auth
	
	# Gets a resource from the Spotify API and returns the object.
	def get(self, url, params={}, tries=3, root=''):
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
				response = json.load(reader(res))
				if root: 
					response = response[root]
				return response
			except Exception as err:
				log('Couldn\'t load URL: {} ({})'.format(url, err))
				time.sleep(2)
				log('Trying again...')
		sys.exit(1)
	
	# The Spotify API breaks long lists into multiple pages. This method automatically
	# fetches all pages and joins them, returning in a single list of objects.
	def list(self, url, params={}, root=''):
		response = self.get(url, params, root=root)
		items = response['items']
		while response['next']:
			response = self.get(response['next'])
			items += response['items']
			print('.', end='')
			sys.stdout.flush()
		print()
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

def log(str, end="\n"):
	#print('[{}] {}'.format(time.strftime('%I:%M:%S'), str).encode(sys.stdout.encoding, errors='replace'))
	sys.stdout.buffer.write(('[{}] {}'+end).format(time.strftime('%H:%M:%S'), str).encode(sys.stdout.encoding, errors='replace'))
	sys.stdout.flush()

def main():
	# Parse arguments.
	parser = argparse.ArgumentParser(description='Exports your Spotify playlists. By default, opens a browser window '
	                                           + 'to authorize the Spotify Web API, but you can also manually specify'
	                                           + ' an OAuth token with the --token option.')
	parser.add_argument('-t', '--token', metavar='OAUTH_TOKEN', help='use a Spotify OAuth token (requires the '
	                                           + '`playlist-read-private` permission)')
	parser.add_argument('-f', '--format', default='json', choices=['json', 'xspf', 'txt', 'md'], help='output format (default: json)')
	parser.add_argument('-l', '--load', metavar='JSON_FILE', help='load an existing json file to create txt or markdown output (playlists only currently)')
	parser.add_argument('-i', '--indent', metavar='INDENT_STR', default=None, help='indent JSON output')
	parser.add_argument('file', help='output filename (or directory for xspf)', nargs='?')
	args = parser.parse_args()
	
	# If they didn't give a filename, then just prompt them. (They probably just double-clicked.)
	while not args.file:
		args.file = input('Enter a file name (e.g. playlists.txt) or directory (xspf format): ')
	
	if args.load:
		with open(args.load, 'r', encoding='utf-8') as f:
			data = json.load(f)
	else:
		# Log into the Spotify API.
		if args.token:
			spotify = SpotifyAPI(args.token)
		else:
			spotify = SpotifyAPI.authorize(client_id='5c098bcc800e45d49e476265bc9b6934', scope='user-follow-read user-library-read playlist-read-private playlist-read-collaborative')
		
		# me								https://developer.spotify.com/web-api/get-current-users-profile/
		# follow['artists]	https://developer.spotify.com/web-api/get-followed-artists/
		# albums						https://developer.spotify.com/web-api/get-users-saved-albums/
		# tracks						https://developer.spotify.com/web-api/get-users-saved-tracks/
		# playlists					https://developer.spotify.com/web-api/console/get-playlists/?user_id=wizzler
		data = {}
		
		# Get the ID of the logged in user.
		data['me'] = spotify.get('me')
		log('Logged in as {display_name} ({id})'.format(**data['me']))

		# Get follows - scope user-follow-read
		# "root" workaround for non-consistent API ..
		data['following'] = {}
		following = spotify.get('me/following', {'type': 'artist', 'limit': 1}, root='artists')
		log('Loading followed artists: {total} artists'.format(**following), end='')
		data['following']['artists'] = spotify.list('me/following', {'type': 'artist', 'limit': 50}, root='artists')
		
		# List saved albums - scope user-library-read
		albums = spotify.get('me/albums', {'limit': 1})
		log('Loading saved albums: {total} albums'.format(**albums), end='')
		data['albums'] = spotify.list('me/albums', {'limit': 50})
		
		# List saved tracks - scope user-library-read
		tracks = spotify.get('me/tracks', {'limit': 1})
		log('Loading tracks: {total} songs'.format(**tracks), end='')
		data['tracks'] = spotify.list('me/tracks', {'limit': 50})
		
		# List all playlists and all track in each playlist - scope playlist-read-private, playlist-read-collaborative
		data['playlists'] = spotify.list('users/{user_id}/playlists'.format(user_id=data['me']['id']), {'limit': 50})
		for playlist in data['playlists']:
			log('Loading playlist: {name} ({tracks[total]} songs)'.format(**playlist), end='')
			playlist['tracks'] = spotify.list(playlist['tracks']['href'], {'limit': 100})
	
	# Write the file(s).
	if args.format == 'xspf':
		# Create the specified directory
		if not os.path.exists(args.file):
			os.makedirs(args.file)
		mkvalid_filename = re.compile(r'[/\\:*?"<>|]')
		# Fake the special tracks playlist as regular playlist
		data['playlists'].append({'id': 'saved-tracks', 'name': 'Saved tracks', 'tracks': data['tracks']})
		# Playlists
		for playlist in data['playlists']:
			valid_filename = mkvalid_filename.sub('', playlist['name'])
			with open('{}{}{}___{}.xspf'.format(args.file, os.sep, valid_filename, playlist['id']), 'w', encoding='utf-8') as f: # Avoid conflicts using id
				try:
					x = xspf.Xspf(title=playlist['name'])
					for track in playlist['tracks']:
						x.add_track(
							title=track['track']['name'],
							album=track['track']['album']['name'],
							creator=', '.join([artist['name'] for artist in track['track']['artists']])
						)
					f.write(x.toXml().decode('utf-8'))
				except Exception as e:
					log('Failed in playlist {} ({}) : {}'.format(playlist['id'], playlist['name'], e))
		# Saved albums -- different format & more informations
		for album in data['albums']:
			artist = ', '.join(a['name'] for a in album['album']['artists'])
			filename = 'Saved album - '+artist+' - '+album['album']['name']
			valid_filename = mkvalid_filename.sub('', filename)
			with open('{}{}{}___{}.xspf'.format(args.file, os.sep, valid_filename, album['album']['id']), 'w', encoding='utf-8') as f: # Avoid conflicts using id
				try:
					x = xspf.Xspf(
						date=album['album']['release_date'],
						creator=artist,
						title=album['album']['name']
					)
					for track in album['album']['tracks']['items']:
						x.add_track(
							title=track['name'],
							album=album['album']['name'],
							creator=', '.join([artist['name'] for artist in track['artists']]),
							duration=str(track['duration_ms']),
							trackNum=str(track['track_number']),
						)
					f.write(x.toXml().decode('utf-8'))
				except Exception as e:
					log('Failed in playlist {} ({}) : {}'.format(album['album']['id'], filename, e))
	else:
		with open(args.file, 'w', encoding='utf-8') as f:
			# JSON file.
			if args.format == 'json':
				json.dump(data, f, indent=args.indent)
			
			# Tab-separated file.
			elif args.format == 'txt':
				for playlist in data['playlists']:
					f.write(playlist['name'] + "\n")
					for track in playlist['tracks']:
						f.write('{name}\t{artists}\t{album}\t{uri}\n'.format(
							uri=track['track']['uri'],
							name=track['track']['name'],
							artists=', '.join([artist['name'] for artist in track['track']['artists']]),
							album=track['track']['album']['name']
						))
					f.write('\n')
			
			# Markdown
			elif args.format == 'md':
				f.write("# Spotify Playlists Backup " + time.strftime("%d %b %Y") + "\n")
				for playlist in data['playlists']:
					f.write("## " + playlist["name"] + "\n")
					for track in playlist['tracks']:
						f.write("* {name}\t{artists}\t{album}\t`{uri}`\n".format(
							uri=track["track"]["uri"],
							name=track["track"]["name"],
							artists=", ".join([artist["name"] for artist in track["track"]["artists"]]),
							album=track["track"]["album"]["name"]
						))
					f.write("\n")
		log('Wrote file: ' + args.file)

if __name__ == '__main__':
	main()
