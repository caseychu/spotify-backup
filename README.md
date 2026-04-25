spotify-backup
==============

A Python script that exports all of your Spotify playlists, useful for paranoid Spotify users like me, afraid that one day Spotify will go under and take all of our playlists with it!

To run the script, [save it from here](https://raw.githubusercontent.com/caseychu/spotify-backup/master/spotify-backup.py) and double-click it. It'll ask you for a filename and then pop open a web page so you can authorize access to the Spotify API. Then the script will load your playlists and save a tab-separated file with your playlists that you can open in Excel. You can even copy-paste the rows from Excel into a Spotify playlist.

You can run the script from the command line:

    python3 spotify-backup.py playlists.txt

The browser authorization flow uses Spotify's Authorization Code with PKCE flow.
If the bundled Spotify app client ID is rejected for your account, create your own
Spotify app, add `http://127.0.0.1:43019/redirect` as a redirect URI, and run:

    SPOTIFY_CLIENT_ID=your_client_id python3 spotify-backup.py playlists.txt

or:

    python3 spotify-backup.py playlists.txt --client-id=your_client_id

or, to get a merged JSON export, use:

    python3 spotify-backup.py playlists.json --format=json

To merge your Liked Songs and playlists into one JSON export, use:

    python3 spotify-backup.py playlist.json --dump=liked,playlists --format=json

JSON exports are written as a single `Spotify Backup` playlist using your Spotify
user ID. Tracks from all selected playlists are merged before writing this
simplified shape:

    {
      "name": "Spotify Backup",
      "id": "your_spotify_user_id",
      "tracks": [
        {
          "artist": "Artist Name",
          "name": "Track Name",
          "album": "Album Name",
          "thumbnail": "https://i.scdn.co/image/...",
          "duration": "3:24",
          "stream": null
        }
      ]
    }

By default, it includes your playlists. To include your Liked Songs, you can use:

    python3 spotify-backup.py playlists.txt --dump=liked,playlists

All exports remove duplicate tracks by Spotify URI before writing the output, so
the same track will not appear twice in either TXT or JSON files. Liked Albums are
also deduplicated by Spotify album URI when included in TXT output.


If for some reason the browser-based authorization flow doesn't work, you can also [generate an OAuth token](https://developer.spotify.com/web-api/console/get-playlists/) on the developer site (with the `playlist-read-private` permission) and pass it with the `--token` option.

Collaborative playlists and playlist folders don't show up in the API, sadly.
