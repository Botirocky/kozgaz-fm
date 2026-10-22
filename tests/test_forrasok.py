__lazy_modules__ = ["pytest", "kozgaz_fm.spotify", "kozgaz_fm.youtube"]

import pytest

from kozgaz_fm.spotify import spotify_uri
from kozgaz_fm.youtube import cim_ertelmezes


@pytest.mark.parametrize(("cim", "vart"), [
    ("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=abc", "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"),
    ("https://open.spotify.com/intl-hu/album/4aawyAB9vmqN3uQ7FjRGTy", "spotify:album:4aawyAB9vmqN3uQ7FjRGTy"),
    ("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "spotify:track:6rqhFgbbKwnb9MLmUQDhG6"),
    ("https://example.com/playlist/123", None),
    ("", None),
])
def test_spotify_uri(cim, vart):
    assert spotify_uri(cim) == vart


def test_youtube_cim():
    assert cim_ertelmezes("youtu.be/abc") == "https://youtu.be/abc"
    assert cim_ertelmezes(" https://www.youtube.com/playlist?list=X ") == "https://www.youtube.com/playlist?list=X"
    assert cim_ertelmezes("slágerek 2025") == "ytsearch25:slágerek 2025"
