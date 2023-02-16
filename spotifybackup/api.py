import codecs
import json
import logging
import sys
import time
import urllib.parse
import urllib.request
import webbrowser

from . import authorization


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
        url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode({
            'response_type': 'token',
            'client_id': client_id,
            'scope': scope,
            'redirect_uri': 'http://127.0.0.1:{}/redirect'.format(SpotifyAPI._SERVER_PORT)
        })
        logging.info(f'Logging in (click if it doesn\'t open automatically): {url}')
        webbrowser.open(url)

        # Start a simple, local HTTP server to listen for the authorization token... (i.e. a hack).
        server = authorization.Server('127.0.0.1', SpotifyAPI._SERVER_PORT)
        try:
            while True:
                server.handle_request()
        except authorization.Authorization as auth:
            return SpotifyAPI(auth.access_token)

    # The port that the local server listens on. Don't change this,
    # as Spotify only will redirect to certain predefined URLs.
    _SERVER_PORT = 43019
