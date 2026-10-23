# MoodMix

MoodMix is a small Flask web app that turns a mood prompt and optional genres, artists, or reference songs into an ordered Spotify catalog playlist.

## Run locally

1. Create an environment and install dependencies with py -m pip install -r requirements.txt.
2. Copy .env.example to .env or set the variables in your shell.
3. Start the server with py app.py.

Open http://127.0.0.1:5000. Without Spotify credentials, the app clearly shows Demo mode and uses bundled sample tracks. Live catalog access requires SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and optionally SPOTIFY_MARKET. Secrets are used only on the server for Spotify's Client Credentials flow.

## Tests

Run py -m pytest -q. Tests use mocked catalog responses and never require live credentials.

This version intentionally does not implement Spotify user sign-in, personal recommendations, Recommendations or Audio Features endpoints, playlist saving, or full playback.

Spotify Development Mode currently requires the app owner to have Premium and limits access to five authorized users.
