from urllib.error import HTTPError

import pytest

from mood_music.mood import interpret_mood
from mood_music.playlist import build_playlist
from mood_music.spotify import SpotifyClient, SpotifyError, normalize_track


def spotify_payload():
    return {"tracks": {"items": [
        {"id": "1", "name": "Bright Dance", "artists": [{"name": "Preferred Artist"}],
         "album": {"name": "Bright", "images": [{"url": "cover-1"}]},
         "external_urls": {"spotify": "https://open.spotify.com/track/1"}},
        {"id": "2", "name": "Quiet Soul", "artists": [{"name": "Other Artist"}],
         "album": {"name": "Quiet", "images": []},
         "external_urls": {"spotify": "https://open.spotify.com/track/2"}},
        {"id": "1", "name": "Bright Dance", "artists": [{"name": "Preferred Artist"}],
         "album": {"name": "Bright", "images": []},
         "external_urls": {"spotify": "https://open.spotify.com/track/1"}},
    ]}}


def test_mood_interpretation_contrasts():
    assert "energetic" in interpret_mood("energetic workout").tags
    assert "calm" in interpret_mood("calm evening focus").tags
    assert interpret_mood("energetic workout").polarity != interpret_mood("calm evening focus").polarity


def test_artists_and_genres_are_primary_mood_signals():
    profile = interpret_mood("quiet background music", "metal", "Daft Punk")
    assert {"energetic", "happy"}.issubset(profile.preference_tags)
    assert profile.preference_tags
    assert profile.tags != profile.mood_tags


def test_spotify_normalization_handles_missing_metadata():
    result = normalize_track({"id": "x", "name": "Song", "artists": [], "album": {}})
    assert result["title"] == "Song"
    assert result["artist"] == "Unknown artist"
    assert result["album"] == "Unknown album"
    assert result["artwork_url"] == ""


def test_demo_mode_does_not_need_credentials():
    client = SpotifyClient()
    assert client.mode == "demo" and len(client.search_tracks("happy")) == 10


def test_mocked_spotify_preferences_rank_and_deduplicate():
    client = SpotifyClient(token="test", http_get=lambda _: spotify_payload())
    tracks = client.search_tracks("happy", "pop", "Preferred Artist", "Bright Dance")
    result = build_playlist("energetic workout", "pop", "Preferred Artist", "Bright Dance", tracks)
    assert [track["id"] for track in result["tracks"]] == ["1", "2"]
    assert "artist you named" in result["tracks"][0]["reason"]
    assert "matches the mood inferred from your artists and genres" in result["tracks"][0]["reason"]


def test_mocked_spotify_empty_results_are_supported():
    client = SpotifyClient(token="test", http_get=lambda _: {"tracks": {"items": []}})
    assert client.search_tracks("unknown") == []


def test_genre_and_artist_filters_are_strict_and_combined():
    tracks = [
        {"id": "match", "title": "Match", "artist": "Preferred Artist", "genre": "Pop"},
        {"id": "wrong-artist", "title": "Wrong Artist", "artist": "Other Artist", "genre": "Pop"},
        {"id": "wrong-genre", "title": "Wrong Genre", "artist": "Preferred Artist", "genre": "Rock"},
    ]
    result = build_playlist("happy", "pop", "Preferred Artist", "", tracks)
    assert [track["id"] for track in result["tracks"]] == ["match"]


def test_playlist_returns_ten_when_catalog_has_ten_or_more():
    tracks = [
        {"id": str(index), "title": f"Track {index}", "artist": "Artist", "album": "Album", "genre": "Pop"}
        for index in range(12)
    ]
    assert len(build_playlist("happy", "", "", "", tracks)["tracks"]) == 10


def test_client_credentials_flow_is_server_side():
    calls = []
    client = SpotifyClient(
        client_id="id",
        client_secret="secret",
        token_request=lambda body, headers: calls.append((body, headers)) or {"access_token": "issued"},
        http_get=lambda query: {"tracks": {"items": []}},
    )
    client._get_access_token()
    assert calls[0][0] == "grant_type=client_credentials"
    assert "secret" not in calls[0][1]["Authorization"]


def test_authentication_and_rate_limit_errors_are_mapped():
    def auth_error(_):
        raise HTTPError("https://api.spotify.com/v1/search", 401, "bad token", {}, None)

    def rate_error(_):
        raise HTTPError("https://api.spotify.com/v1/search", 429, "slow down", {}, None)

    with pytest.raises(SpotifyError, match="authorization"):
        SpotifyClient(token="test", http_get=auth_error).search_tracks("mood")
    with pytest.raises(SpotifyError, match="rate limiting"):
        SpotifyClient(token="test", http_get=rate_error).search_tracks("mood")
