spotify-backup
==============

A Python script that exports all of your Spotify playlists. (Useful for paranoid Spotify users like me who are afraid that one day Spotify will go under and take all of our playlists with it!) [Save the script](https://raw.githubusercontent.com/bitsofpancake/spotify-backup/master/spotify-backup.py) and run it like so:

    python spotify-backup.py playlists.txt

This'll pop open a web browser letting you authorize the script to access the Spotify API. Then it'll download your playlists and save a tab-separated file `playlists.txt` with your playlists that you can open in Excel. (As a bonus, you can copy-paste the rows into a Spotify playlist!)

Adding `--format=json` will give you a JSON dump with everything that the script gets from the Spotify API. If for some reason the browser-based authorization flow doesn't work, you can also [generate an OAuth token](https://developer.spotify.com/web-api/console/get-playlists/) on the developer site (with the `playlist-read-private` permission) and pass it with the `--token` option.
