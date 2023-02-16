import argparse
import json
import logging
import pathlib

from . import api


logging.basicConfig(
    format="[%(asctime)s] %(message)s",
    datefmt="%I:%M:%S",
    level=logging.DEBUG
)


SCOPES = {
    "playlists": ["playlist-read-private", "playlist-read-collaborative"],
    "liked": ["user-library-read"]
}


def _artists(artists) -> str:
    return ", ".join(artist["name"] for artist in artists)


def backup(
    dump: str,
    filepath: pathlib.Path,
    format_: str,
    token: str = None
) -> None:
    if token:
        spotify = api.SpotifyAPI(token)
    else:
        scopes = set(
            scope for k, v in SCOPES.items() if k in dump for scope in v
        )
        spotify = api.SpotifyAPI.authorize(scopes)
    playlists = []
    liked_songs = []
    liked_albums = []
    if "liked" in dump:
        logging.info("Getting liked songs and albums...")
        liked_songs.extend(spotify.songs())
        liked_albums.extend(spotify.albums())
    if "playlists" in dump:
        logging.info("Getting playlists...")
        for playlist in spotify.playlists():
            logging.info(
                "Getting playlist: {0[name]} ({0[tracks][total]} "
                "songs)".format(playlist)
            )
            playlist["tracks"] = list(spotify.playlist_tracks(playlist))
            playlists.append(playlist)
        logging.info(f"Got {len(playlists)} playlists")
    playlists.insert(0, {"name": "Liked Songs", "tracks": liked_songs})
    logging.info('Writing file...')
    with open(filepath, "w", encoding="utf-8") as file:
        if format_ == "json":
            json.dump(
                {"playlists": playlists, "albums": liked_albums},
                file,
                indent=4
            )
        elif format_ == "txt":
            file.write("Playlists:\n\n")
            for playlist in playlists:
                file.write("{[name]}\n".format(playlist))
                for item in playlist["tracks"]:
                    track = item["track"]
                    if track is None:
                        continue
                    file.write(
                        "{0[name]}\t{artists}\t{0[album][name]}\t{0[uri]}\t"
                        "{0[album][release_date]}\n"
                        .format(track, artists=_artists(track["artists"]))
                    )
                file.write("\n")
            if liked_albums:
                file.write("Liked Albums:\n\n")
                for item in liked_albums:
                    album = item["album"]
                    file.write(
                        "{0[name]}\t{artists}\t-\t{0[uri]}\t{0[release_date]}"
                        "\n"
                        .format(album, artists=_artists(album["artists"]))
                    )
    logging.info(f"Wrote file: {filepath}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=
            "Exports your Spotify playlists. By default, opens a browser "
            "window to authorize the Spotify Web API, but you can also "
            "manually specify an OAuth token with the --token option."
    )
    parser.add_argument(
        "--token",
        help=
            "use a Spotify OAuth token (requires the 'playlist-read-private' "
            "permission)"
    )
    parser.add_argument(
        "--dump",
        default="playlists",
        choices=["liked,playlists", "playlists,liked", "playlists", "liked"],
        help=
            "dump playlists ('playlists') or liked songs and albums "
            "('liked'), or both (comma-separated) (default: playlists)",
        metavar="DUMP"
    )
    parser.add_argument(
        "--format",
        default="txt",
        choices=["json", "txt"],
        help="output format (default: txt)"
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="output filename"
    )
    args = parser.parse_args()
    while not args.file:
        args.file = input("Enter a file name (e.g. playlists.txt): ")
        args.format = args.file.split(".")[-1]
    backup(args.dump, args.file, args.format, args.token)
    return 0
