spotify-backup
==============

A Python 3 script that exports all of your Spotify playlists, useful for paranoid Spotify users like me, afraid that one day Spotify will go under and take all of our playlists with it!

Run the script, and double-click it. It'll ask you for a filename and then pop open a web page so you can authorize access to the Spotify API. Then the script will load your datas.
You can have a tab-separated file with your playlists that you can open in Excel using `--format txt`, so you can even copy-paste the rows from Excel into a Spotify playlist.

You can also run the script from the command line:

    python spotify-backup.py data.json

If for some reason the browser-based authorization flow doesn't work, you can also [generate an OAuth token](https://developer.spotify.com/web-api/console/get-playlists/) on the developer site (with `user-follow-read user-library-read playlist-read-private playlist-read-collaborative` permission) and pass it with the `--token` option.
