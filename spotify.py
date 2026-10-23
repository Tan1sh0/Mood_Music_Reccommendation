import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .data import DEMO_TRACKS


class SpotifyError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


def _http_error_detail(error):
    try:
        payload = json.loads(error.read().decode("utf-8"))
        if isinstance(payload, dict):
            detail = payload.get("error_description") or payload.get("error") or payload.get("message")
            if detail:
                return str(detail)[:180]
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    return ""


def normalize_track(item, search_context=None):
    item = item or {}
    album = item.get("album") or {}
    artists = item.get("artists") or []
    images = album.get("images") or []
    external_urls = item.get("external_urls") or {}
    return {
        "id": str(item.get("id") or external_urls.get("spotify") or item.get("name") or "unknown"),
        "title": item.get("name") or "Untitled track",
        "artist": ", ".join(a.get("name", "Unknown artist") for a in artists if isinstance(a, dict)) or "Unknown artist",
        "album": album.get("name") or "Unknown album",
        "genre": "Unknown genre",
        "artwork_url": images[0].get("url", "") if images and isinstance(images[0], dict) else "",
        "url": external_urls.get("spotify") or "",
        "search_context": list(search_context or []),
    }


class SpotifyClient:
    def __init__(self, market="US", client_id=None, client_secret=None, token=None,
                 http_get=None, token_request=None):
        self.market = market or "US"
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token
        self.http_get = http_get or self._http_get
        self.token_request = token_request or self._token_request
        self.mode = "live" if token or (client_id and client_secret) else "demo"

    @classmethod
    def from_environment(cls):
        return cls(
            market=os.getenv("SPOTIFY_MARKET", "US"),
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        )

    def search_tracks(self, mood, genres="", artists="", songs=""):
        if self.mode == "demo":
            return DEMO_TRACKS
        queries = [(mood.strip(), "mood")] if mood.strip() else []
        queries += [(f"genre:{genre.strip()}", "genre") for genre in genres.split(",") if genre.strip()]
        queries += [(f"artist:{artist.strip()}", "artist") for artist in artists.split(",") if artist.strip()]
        queries += [(song.strip(), "reference song") for song in songs.split(",") if song.strip()]
        tracks = []
        for query, context in queries:
            try:
                payload = self.http_get(query)
            except HTTPError as error:
                detail = _http_error_detail(error)
                suffix = f" Details: {detail}" if detail else ""
                if error.code == 401:
                    raise SpotifyError(f"Spotify authorization expired or was rejected.{suffix}", 502)
                if error.code == 403:
                    raise SpotifyError(
                        f"Spotify denied catalog search (HTTP 403). Check Development Mode access and Premium requirements.{suffix}",
                        403,
                    )
                if error.code == 400:
                    raise SpotifyError(f"Spotify rejected the catalog search request (HTTP 400).{suffix}", 400)
                if error.code == 429:
                    raise SpotifyError(f"Spotify is rate limiting requests. Please try again shortly.{suffix}", 429)
                raise SpotifyError(f"Spotify could not complete catalog search (HTTP {error.code}).{suffix}", 502)
            if not isinstance(payload, dict):
                raise SpotifyError("Spotify returned an invalid search response.", 502)
            tracks_payload = payload.get("tracks") or {}
            if not isinstance(tracks_payload, dict):
                raise SpotifyError("Spotify returned an invalid search response.", 502)
            for item in (tracks_payload.get("items") or []):
                tracks.append(normalize_track(item, [context, query]))
        return tracks

    def _token_request(self, body, headers):
        request = Request(
            "https://accounts.spotify.com/api/token",
            data=body.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get_access_token(self):
        if self.token:
            return self.token
        if not self.client_id or not self.client_secret:
            raise SpotifyError("Spotify credentials are not configured.", 503)
        credentials = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        auth = base64.b64encode(credentials).decode("ascii")
        try:
            payload = self.token_request(
                "grant_type=client_credentials",
                {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
            )
            token = payload.get("access_token")
            if not token:
                raise SpotifyError("Spotify authentication returned no access token.", 502)
            self.token = token
            return token
        except HTTPError as error:
            detail = _http_error_detail(error)
            suffix = f" Details: {detail}" if detail else ""
            if error.code in (400, 401):
                raise SpotifyError(f"Spotify authentication failed. Check the client ID and secret.{suffix}", 502)
            raise SpotifyError(f"Spotify authentication is temporarily unavailable.{suffix}", 502)
        except (URLError, json.JSONDecodeError, KeyError, TypeError, AttributeError):
            raise SpotifyError("Spotify authentication is temporarily unavailable.", 502)

    def _http_get(self, query):
        params = urlencode({"q": query, "type": "track", "limit": 10, "market": self.market})
        request = Request(
            f"https://api.spotify.com/v1/search?{params}",
            headers={"Authorization": f"Bearer {self._get_access_token()}"},
        )
        try:
            with urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = _http_error_detail(error)
            suffix = f" Details: {detail}" if detail else ""
            if error.code == 401:
                self.token = None
                raise SpotifyError(f"Spotify authorization expired or was rejected.{suffix}", 502)
            if error.code == 403:
                raise SpotifyError(
                    f"Spotify denied catalog search (HTTP 403). Check Development Mode access and Premium requirements.{suffix}",
                    403,
                )
            if error.code == 400:
                raise SpotifyError(f"Spotify rejected the catalog search request (HTTP 400).{suffix}", 400)
            if error.code == 429:
                raise SpotifyError(f"Spotify is rate limiting requests. Please try again shortly.{suffix}", 429)
            raise SpotifyError(f"Spotify could not complete catalog search (HTTP {error.code}).{suffix}", 502)
        except (URLError, json.JSONDecodeError, KeyError, TypeError):
            raise SpotifyError("Spotify returned an invalid response.", 502)
