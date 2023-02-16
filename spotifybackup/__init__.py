import argparse
import json
import logging

from . import api


logging.basicConfig(level=20, datefmt='%I:%M:%S', format='[%(asctime)s] %(message)s')


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
        spotify = api.SpotifyAPI(args.token)
    else:
        spotify = api.SpotifyAPI.authorize(client_id='5c098bcc800e45d49e476265bc9b6934',
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
        liked_tracks = spotify.list('users/{user_id}/tracks'.format(user_id=me['id']), {'limit': 50})
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
