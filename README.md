# spotify-backup

A Python script that exports all of your Spotify playlists, useful for paranoid Spotify users like me, afraid that one day Spotify will go under and take all of our playlists with it!

## Usage

To run the script, [save it from here](https://github.com/ejwick/spotify-export/archive/refs/heads/master.zip), extract the repo and run the module:

```
python -m spotify-backup
```

It'll ask you for a filename and then pop open a web page so you can authorize access to the Spotify API. Then the script will load your playlists and save a tab-separated file with your playlists that you can open in Excel. You can even copy-paste the rows from Excel into a Spotify playlist.

To get a JSON dump, use the `--format` option:

```
python -m spotify-backup --format=json playlists.json
```

By default, it includes your playlists. To include your liked songs and albums, use the `--dump` option:

```
python -m spotify-backup --dump=liked,playlists backup.txt
```

## Passing an OAuth token

If for some reason the browser-based authorization flow doesn't work, you can also [generate an OAuth token](https://developer.spotify.com/web-api/console/get-playlists/) on the developer site and pass it with the `--token` option. The token will need these scopes:

- For playlists: `playlist-read-private` and `playlist-read-collaborative`
- For liked songs and albums: `user-library-read`

## Installation

You can install `spotify-export` so it can be ran directly instead of as a Python module.

Run this from the root folder:

```
pip install .
```

Now you can run `spotify-backup` like this:

```
spotify-backup
```
