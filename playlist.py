from .mood import interpret_mood


def _tokens(value):
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def _matches_any(preferences, value):
    value = str(value or "").lower()
    return any(preference in value for preference in preferences)


def build_playlist(mood, genres, artists, songs, tracks, limit=10):
    profile = interpret_mood(mood, genres, artists)
    direction_tags = profile.preference_tags or profile.mood_tags
    genre_preferences, artist_preferences = _tokens(genres), _tokens(artists)
    song_preferences = _tokens(songs)
    unique, ranked = {}, []
    for track in tracks:
        key = track.get("id") or f"{track.get('title','').lower()}::{track.get('artist','').lower()}"
        if key in unique:
            existing = unique[key]
            contexts = set(existing.get("search_context", []))
            contexts.update(track.get("search_context", []))
            existing["search_context"] = sorted(contexts)
            continue
        unique[key] = {**track, "search_context": list(track.get("search_context", []))}
    for track in unique.values():
        haystack = " ".join(str(track.get(k, "")).lower() for k in ("title", "artist", "album", "genre", "search_context"))
        genre_text = " ".join(str(track.get(k, "")).lower() for k in ("genre", "search_context"))
        artist_text = str(track.get("artist", "")).lower()
        if genre_preferences and not _matches_any(genre_preferences, genre_text):
            continue
        if artist_preferences and not _matches_any(artist_preferences, artist_text):
            continue
        score = 0
        reasons = []
        if any(pref in haystack for pref in genre_preferences):
            score += 5; reasons.append("matches your genre preference")
        if any(pref in haystack for pref in artist_preferences):
            score += 6; reasons.append("features an artist you named")
        if any(pref in haystack for pref in song_preferences):
            score += 4; reasons.append("connects to a reference song")
        elif "reference song" in haystack and song_preferences:
            score += 3; reasons.append("was found through your reference-song search")
        preference_match = any(pref in haystack for pref in genre_preferences | artist_preferences)
        search_match = any(context in haystack for context in ("genre", "artist"))
        if profile.preference_tags and (preference_match or search_match):
            score += 4
            reasons.append("matches the mood inferred from your artists and genres")
        if direction_tags & {"happy", "energetic"} and any(word in haystack for word in ("dance", "pop", "electronic", "alternative")):
            score += 2; reasons.append("fits the upbeat direction")
        if direction_tags & {"calm", "sad", "romantic", "nostalgic", "reflective"} and any(word in haystack for word in ("soul", "acoustic", "alternative", "electronic")):
            score += 2; reasons.append("fits the reflective direction")
        if not reasons:
            reasons.append(f"supports a {', '.join(sorted(profile.tags))} mood")
        ranked.append((score, track, "; ".join(reasons)))
    ranked.sort(key=lambda row: (-row[0], row[1].get("title", "").lower()))
    return {
        "profile": {
            "tags": sorted(profile.tags),
            "preference_tags": sorted(profile.preference_tags),
            "mood_tags": sorted(profile.mood_tags),
            "polarity": profile.polarity,
        },
        "tracks": [{**track, "reason": reason} for _, track, reason in ranked[:limit]],
    }
