import argparse 
import urllib
import urllib2
import json
import time
import webbrowser
import sys
import BaseHTTPServer
import re
import codecs

class SpotifyAPI:
	def __init__(self, auth):
		self._auth = auth
	
	def get(self, url, params={}, tries=3):
		if not url.startswith('https://api.spotify.com/v1/'):
			url = 'https://api.spotify.com/v1/' + url
		if params:
			url += ('&' if '?' in url else '?') + urllib.urlencode(params)
		
		try:
			return json.load(urllib2.urlopen(urllib2.Request(url, None, {'Authorization': 'Bearer ' + self._auth})))
		except urllib2.HTTPError as err:
			log('Couldn\'t load URL: {} ({} {})'.format(url, err.code, err.reason))
			if tries <= 0:
				sys.exit(1)
			time.sleep(2)
			log('Trying again...')
			return self.get(url, tries=tries-1)

	def list(self, path, params={}):
		response = self.get(path, params)
		items = response['items']
		while response['next']:
			response = self.get(response['next'])
			items += response['items']
		return items
	
	_LISTEN_PORT_NUMBER = 43019
	
	@staticmethod
	def authorize(client_id, scope):
		webbrowser.open('https://accounts.spotify.com/authorize?' + urllib.urlencode({
			'response_type': 'token',
			'client_id': client_id,
			'scope': scope,
			'redirect_uri': 'http://127.0.0.1:{}/redirect'.format(SpotifyAPI._LISTEN_PORT_NUMBER)
		}))
		httpd = SpotifyAPI._AuthorizationListener('', SpotifyAPI._LISTEN_PORT_NUMBER)
		try:
			while True:
				httpd.handle_request()
		except SpotifyAPI._Authorization as auth:
			return SpotifyAPI(auth.access_token)
			
	class _AuthorizationListener(BaseHTTPServer.HTTPServer):
		def __init__(self, host, port):
			BaseHTTPServer.HTTPServer.__init__(self, (host, port), SpotifyAPI._AuthorizationHandler)
		def handle_error(self, request, client_address):
			raise

	class _AuthorizationHandler(BaseHTTPServer.BaseHTTPRequestHandler):
		def do_GET(self):
			if self.path.startswith('/redirect'):
				self.send_response(200)
				self.send_header('Content-Type', 'text/html')
				self.end_headers()
				self.wfile.write('<script>location.replace("token?" + location.hash.slice(1));</script>')
			elif self.path.startswith('/token?'):
				self.send_response(200)
				self.send_header('Content-Type', 'text/html')
				self.end_headers()
				self.wfile.write('<script>close()</script>Thanks! You may now close this window.')
				raise SpotifyAPI._Authorization(re.search('access_token=([^&]*)', self.path).group(1))
			else:
				self.send_error(404)
				
		def log_message(self, format, *args):
			pass
				
	class _Authorization(Exception):
		def __init__(self, access_token):
			self.access_token = access_token
		
def log(str):
	print u'[{}] {}'.format(time.strftime('%I:%M:%S'), str).encode(sys.stdout.encoding, errors='replace')

def main():
	parser = argparse.ArgumentParser(description='Exports your Spotify playlists. By default, opens a browser window to authorize the Spotify Web API, but you can manually specify an OAuth token with the --token option.')
	parser.add_argument('--token', metavar='OAUTH_TOKEN', help='use a Spotify OAuth token (requires the `playlist-read-private` permission)')
	parser.add_argument('--format', default='txt', choices=['json', 'txt'], help='output format (default: txt)')
	parser.add_argument('file', help='output filename')
	args = parser.parse_args()

	if args.token:
		spotify = SpotifyAPI(args.token)
	else:
		spotify = SpotifyAPI.authorize(client_id='5c098bcc800e45d49e476265bc9b6934', scope='playlist-read-private')

	me = spotify.get('me')
	log(u'Logged in as {display_name} ({id})'.format(**me))
	playlists = spotify.list('users/{user_id}/playlists'.format(user_id=me['id']), {'limit': 50})
	for playlist in playlists:
		log(u'Loading playlist: {name} ({tracks[total]} songs)'.format(**playlist))
		playlist['tracks'] = spotify.list(playlist['tracks']['href'], {'limit': 100})
		
	with codecs.open(args.file, 'w', 'utf-8') as f:
		if args.format == 'json':
			json.dump(playlists, f)
		elif args.format == 'txt':
			for playlist in playlists:
				f.write(playlist['name'] + '\r\n')
				for track in playlist['tracks']:
					f.write(u'{uri}\t{name}\t{artists}\t{album}\r\n'.format(
						uri=track['track']['uri'],
						name=track['track']['name'],
						artists=', '.join([artist['name'] for artist in track['track']['artists']]),
						album=track['track']['album']['name']
					))
				f.write('\r\n')
	log('Wrote file: ' + args.file)

if __name__ == '__main__':
	main()