"""Tests for Plex player playback methods/services."""
from http import HTTPStatus
from unittest.mock import Mock, patch

import pytest

from homeassistant.components.media_player.const import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as MP_DOMAIN,
    MEDIA_TYPE_MOVIE,
    SERVICE_PLAY_MEDIA,
)
from homeassistant.components.plex.const import CONF_SERVER_IDENTIFIER, PLEX_URI_SCHEME
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import HomeAssistantError

from .const import DEFAULT_DATA, PLEX_DIRECT_URL


class MockPlexMedia:
    """Minimal mock of plexapi media object."""

    key = "key"
    viewOffset = 333
    _server = Mock(_baseurl=PLEX_DIRECT_URL)

    def __init__(self, title, mediatype):
        """Initialize the instance."""
        self.listType = mediatype
        self.title = title
        self.type = mediatype

    def section(self):
        """Return the LibrarySection."""
        return MockPlexLibrarySection()


class MockPlexLibrarySection:
    """Minimal mock of plexapi LibrarySection."""

    uuid = "00000000-0000-0000-0000-000000000000"


async def test_media_player_playback(
    hass,
    setup_plex_server,
    requests_mock,
    playqueue_created,
    player_plexweb_resources,
):
    """Test playing media on a Plex media_player."""
    requests_mock.get("http://1.2.3.5:32400/resources", text=player_plexweb_resources)

    await setup_plex_server()

    media_player = "media_player.plex_plex_web_chrome"
    requests_mock.post("/playqueues", text=playqueue_created)
    playmedia_mock = requests_mock.get(
        "/player/playback/playMedia", status_code=HTTPStatus.OK
    )

    # Test media lookup failure
    payload = '{"library_name": "Movies", "title": "Movie 1" }'
    with patch("plexapi.library.LibrarySection.search", return_value=None):
        with pytest.raises(HomeAssistantError) as excinfo:
            assert await hass.services.async_call(
                MP_DOMAIN,
                SERVICE_PLAY_MEDIA,
                {
                    ATTR_ENTITY_ID: media_player,
                    ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_MOVIE,
                    ATTR_MEDIA_CONTENT_ID: payload,
                },
                True,
            )
            assert not playmedia_mock.called
    assert f"No {MEDIA_TYPE_MOVIE} results in 'Movies' for" in str(excinfo.value)

    movie1 = MockPlexMedia("Movie", "movie")
    movie2 = MockPlexMedia("Movie II", "movie")
    movie3 = MockPlexMedia("Movie III", "movie")

    # Test movie success
    movies = [movie1]
    with patch("plexapi.library.LibrarySection.search", return_value=movies):
        assert await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: media_player,
                ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_MOVIE,
                ATTR_MEDIA_CONTENT_ID: '{"library_name": "Movies", "title": "Movie 1" }',
            },
            True,
        )
        assert playmedia_mock.called

    # Test movie success with resume
    playmedia_mock.reset()
    with patch("plexapi.library.LibrarySection.search", return_value=movies):
        assert await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: media_player,
                ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_MOVIE,
                ATTR_MEDIA_CONTENT_ID: '{"library_name": "Movies", "title": "Movie 1", "resume": true}',
            },
            True,
        )
        assert playmedia_mock.called
        assert playmedia_mock.last_request.qs["offset"][0] == str(movie1.viewOffset)

    # Test movie success with media browser URL
    playmedia_mock.reset()
    assert await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            ATTR_ENTITY_ID: media_player,
            ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_MOVIE,
            ATTR_MEDIA_CONTENT_ID: PLEX_URI_SCHEME
            + f"{DEFAULT_DATA[CONF_SERVER_IDENTIFIER]}/1",
        },
        True,
    )
    assert playmedia_mock.called

    # Test movie success with legacy media browser URL
    playmedia_mock.reset()
    assert await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            ATTR_ENTITY_ID: media_player,
            ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_MOVIE,
            ATTR_MEDIA_CONTENT_ID: PLEX_URI_SCHEME + "1",
        },
        True,
    )
    assert playmedia_mock.called

    # Test multiple choices with exact match
    playmedia_mock.reset()
    movies = [movie1, movie2]
    with patch("plexapi.library.LibrarySection.search", return_value=movies):
        assert await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: media_player,
                ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_MOVIE,
                ATTR_MEDIA_CONTENT_ID: '{"library_name": "Movies", "title": "Movie" }',
            },
            True,
        )
        assert playmedia_mock.called

    # Test multiple choices without exact match
    playmedia_mock.reset()
    movies = [movie2, movie3]
    with pytest.raises(HomeAssistantError) as excinfo:
        payload = '{"library_name": "Movies", "title": "Movie" }'
        with patch("plexapi.library.LibrarySection.search", return_value=movies):
            assert await hass.services.async_call(
                MP_DOMAIN,
                SERVICE_PLAY_MEDIA,
                {
                    ATTR_ENTITY_ID: media_player,
                    ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_MOVIE,
                    ATTR_MEDIA_CONTENT_ID: payload,
                },
                True,
            )
            assert not playmedia_mock.called
    assert "Multiple matches, make content_id more specific" in str(excinfo.value)

    # Test multiple choices with allow_multiple
    movies = [movie1, movie2, movie3]
    with patch("plexapi.library.LibrarySection.search", return_value=movies), patch(
        "homeassistant.components.plex.server.PlexServer.create_playqueue"
    ) as mock_create_playqueue:
        assert await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: media_player,
                ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_MOVIE,
                ATTR_MEDIA_CONTENT_ID: '{"library_name": "Movies", "title": "Movie", "allow_multiple": true }',
            },
            True,
        )
        assert mock_create_playqueue.call_args.args == (movies,)
        assert playmedia_mock.called

    # Test radio station
    playmedia_mock.reset()
    radio_id = "/library/sections/3/stations/1"
    assert await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            ATTR_ENTITY_ID: media_player,
            ATTR_MEDIA_CONTENT_TYPE: "station",
            ATTR_MEDIA_CONTENT_ID: PLEX_URI_SCHEME
            + f"{DEFAULT_DATA[CONF_SERVER_IDENTIFIER]}/{radio_id}",
        },
        True,
    )
    assert playmedia_mock.called
