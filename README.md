spotify-backup
==============

A Python 3* script that exports all of your Spotify playlists, useful for paranoid Spotify users like me, afraid that one day Spotify will go under and take all of our playlists with it!

To run the script, [save it from here](https://raw.githubusercontent.com/bitsofpancake/spotify-backup/master/spotify-backup.py) and double-click it. It'll ask you for a filename and then pop open a web page so you can authorize access to the Spotify API. Then the script will load your playlists and save a tab-separated file with your playlists that you can open in Excel. You can even copy-paste the rows from Excel into a Spotify playlist.

You can also run the script from the command line:

    python spotify-backup.py playlists.txt

Adding `--format=json` will give you a JSON dump with everything that the script gets from the Spotify API. If for some reason the browser-based authorization flow doesn't work, you can also [generate an OAuth token](https://developer.spotify.com/web-api/console/get-playlists/) on the developer site (with the `playlist-read-private` permission) and pass it with the `--token` option.

Collaborative playlists and playlist folders don't show up in the API, sadly.

*The [last version compatible with Python 2.7](https://raw.githubusercontent.com/bitsofpancake/spotify-backup/1f7e76a230e10910aa2cfa5d83ced4c271377af4/spotify-backup.py) probably still works.
