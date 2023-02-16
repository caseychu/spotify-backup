import collections.abc
import functools
import itertools
import json
import logging
import typing
import urllib.parse
import urllib.request
import urllib.response
import webbrowser

from . import authorization


def chain(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return itertools.chain.from_iterable(f(*args, **kwargs))
    return wrapper


class SpotifyAPI:
    _CLIENT_ID = "5c098bcc800e45d49e476265bc9b6934"
    _BASE_URL = "https://api.spotify.com/v1/"

    def __init__(self, token) -> None:
        self.token = token

    @classmethod
    def authorize(cls, scopes: collections.abc.Iterable[str]) -> typing.Self:
        logging.info("Authorizing...")
        server = authorization.Server()
        query = urllib.parse.urlencode(
            {
                "client_id": cls._CLIENT_ID,
                "response_type": "token",
                "redirect_uri": server.redirect_uri(),
                "state": server.state,
                "scope": " ".join(scopes)
            }
        )
        url = f"https://accounts.spotify.com/authorize?{query}"
        webbrowser.open(url)
        with server:
            while server.token is None:
                server.handle_request()
        return cls(server.token)

    def get(self, url, params=None) -> typing.Any:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        request = urllib.request.Request(
            urllib.parse.urljoin(self._BASE_URL, url) + query,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        print(request.full_url)
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    def getter(
        self, url
    ) -> collections.abc.Generator[typing.Any, str, None]:
        while url:
            yield self.get(url, {"limit": 50})
            url = yield

    @chain
    def items(self, url) -> collections.abc.Iterator[typing.Any]:
        getter = self.getter(url)
        for body in getter:
            yield body["items"]
            getter.send(body["next"])

    def playlists(self):
        return self.items("me/playlists")

    def playlist_tracks(self, playlist):
        return self.items(playlist["tracks"]["href"])

    def songs(self):
        return self.items("me/tracks")

    def albums(self):
        return self.items("me/albums")
