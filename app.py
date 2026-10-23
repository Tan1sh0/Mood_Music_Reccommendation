from flask import Flask, jsonify, render_template, request

from mood_music.spotify import SpotifyClient, SpotifyError
from mood_music.playlist import build_playlist


def create_app(config=None):
    app = Flask(__name__)
    if config:
        app.config.update(config)
    client = SpotifyClient.from_environment()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/playlist")
    def playlist():
        mood = request.args.get("mood", "").strip()
        if not mood:
            return jsonify({"error": "Tell us how you want to feel first."}), 400
        try:
            tracks = client.search_tracks(
                mood,
                request.args.get("genres", ""),
                request.args.get("artists", ""),
                request.args.get("songs", ""),
            )
            return jsonify({"mode": client.mode, **build_playlist(
                mood, request.args.get("genres", ""), request.args.get("artists", ""),
                request.args.get("songs", ""), tracks)})
        except SpotifyError as error:
            return jsonify({"error": str(error), "mode": client.mode}), error.status_code

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
