from dataclasses import dataclass
import re


@dataclass(frozen=True)
class MoodProfile:
    mood: str
    tags: frozenset[str]
    polarity: str
    preference_tags: frozenset[str] = frozenset()
    mood_tags: frozenset[str] = frozenset()


MOOD_TAGS = {
    "happy": {"happy", "joyful", "fun", "upbeat", "dance", "celebrate", "party"},
    "calm": {"calm", "relaxed", "peaceful", "chill", "focus", "study", "soft"},
    "sad": {"sad", "melancholy", "heartbroken", "lonely", "blue", "cry"},
    "energetic": {"energetic", "workout", "hype", "power", "intense", "run"},
    "romantic": {"romantic", "love", "date", "intimate", "dreamy"},
    "nostalgic": {"nostalgic", "nostalgia", "retro", "throwback", "memories"},
}


GENRE_MOOD_TAGS = {
    "ambient": {"calm", "reflective"},
    "acoustic": {"calm", "romantic"},
    "blues": {"sad", "reflective"},
    "classical": {"calm", "reflective"},
    "country": {"nostalgic", "happy"},
    "dance": {"energetic", "happy"},
    "disco": {"energetic", "happy"},
    "edm": {"energetic", "happy"},
    "electronic": {"energetic", "nostalgic"},
    "folk": {"calm", "nostalgic"},
    "funk": {"happy", "energetic"},
    "hip hop": {"energetic", "confident"},
    "house": {"energetic", "happy"},
    "indie": {"reflective", "nostalgic"},
    "jazz": {"calm", "romantic"},
    "lo-fi": {"calm", "reflective"},
    "metal": {"energetic", "intense"},
    "pop": {"happy", "energetic"},
    "punk": {"energetic", "intense"},
    "rap": {"energetic", "confident"},
    "r&b": {"romantic", "reflective"},
    "reggae": {"happy", "calm"},
    "rock": {"energetic", "nostalgic"},
    "singer-songwriter": {"reflective", "romantic"},
    "soul": {"romantic", "reflective"},
}

ARTIST_MOOD_TAGS = {
    "adele": {"sad", "romantic"},
    "billie eilish": {"reflective", "sad"},
    "bob marley": {"happy", "calm"},
    "coldplay": {"nostalgic", "romantic"},
    "daft punk": {"energetic", "happy"},
    "drake": {"romantic", "confident"},
    "frank ocean": {"romantic", "reflective"},
    "kendrick lamar": {"energetic", "confident"},
    "lana del rey": {"romantic", "nostalgic"},
    "radiohead": {"reflective", "nostalgic"},
    "sza": {"romantic", "reflective"},
    "taylor swift": {"romantic", "nostalgic"},
    "the weeknd": {"romantic", "energetic"},
}


def _preference_tags(genres: str, artists: str) -> set[str]:
    text = f"{genres} {artists}".lower()
    tags = set()
    for hint, hint_tags in GENRE_MOOD_TAGS.items():
        if hint in text:
            tags.update(hint_tags)
    for artist, artist_tags in ARTIST_MOOD_TAGS.items():
        if artist in text:
            tags.update(artist_tags)
    return tags


def interpret_mood(prompt: str, genres: str = "", artists: str = "") -> MoodProfile:
    text = prompt.lower().strip()
    words = set(re.findall(r"[a-z]+", text))
    mood_tags = {tag for tag, keywords in MOOD_TAGS.items() if words & keywords}
    if not mood_tags:
        mood_tags = {"calm"} if any(w in text for w in ("unwind", "evening", "background")) else {"happy"}
    preference_tags = _preference_tags(genres, artists)
    tags = preference_tags | mood_tags
    polarity = "reflective" if tags & {"sad", "nostalgic", "calm", "reflective"} else "positive"
    return MoodProfile(
        prompt.strip(),
        frozenset(tags),
        polarity,
        frozenset(preference_tags),
        frozenset(mood_tags),
    )
