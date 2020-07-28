"""Support for interacting with Saavn Connect."""
import datetime as dt
import logging
from typing import Any, Dict, List, Optional

from aiohttp import ClientError
from .saavn import Saavn
from yarl import URL

from homeassistant.core import callback
from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_PLAYLIST,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_SEEK,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_SHUFFLE_SET,
    SUPPORT_VOLUME_SET,
    SUPPORT_STOP,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_STEP,
    SUPPORT_TURN_ON,
    SUPPORT_TURN_OFF,
)

from homeassistant.components.media_player import (
    MediaPlayerDevice,
    PLATFORM_SCHEMA,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    SERVICE_PLAY_MEDIA,
    SERVICE_MEDIA_PAUSE,
    SERVICE_VOLUME_UP,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_SET,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as DOMAIN_MP,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ID,
    CONF_NAME,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_OFF,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session
from homeassistant.helpers.entity import Entity
from homeassistant.util.dt import utc_from_timestamp
from homeassistant.helpers.event import async_track_state_change

from .const import DATA_SAAVN_CLIENT, DOMAIN, MEDIA_TYPE_ALBUM

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:music-circle"

SUPPORT_SAAVN = (
    SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
    | SUPPORT_PLAY
    | SUPPORT_PLAY_MEDIA
    | SUPPORT_PAUSE
    | SUPPORT_STOP
    | SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_STEP
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_NEXT_TRACK
    | SUPPORT_SHUFFLE_SET
    | SUPPORT_SELECT_SOURCE
    | SUPPORT_SEEK
)



async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Saavn"""
    saavn = SaavnMediaPlayer(
        hass,
        Saavn(),
        'saavn',
        '',
    )
    async_add_entities([saavn], True)


def saavn_exception_handler(func):
    """Decorate Saavn calls to handle Saavn exception.

    A decorator that wraps the passed in function, catches Saavn errors,
    aiohttp exceptions and handles the availability of the media player.
    """

    def wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
            self.player_available = True
            return result
        except (ClientError):
            self.player_available = False

    return wrapper


class SaavnMediaPlayer(MediaPlayerEntity):
    """Representation of a Saavn controller."""

    def __init__(
        self,
        hass,
        saavn: Saavn,
        user_id: str,
        name: str,
    ):
        """Initialize."""
        self._id = user_id
        self._name = name
        self._saavn = saavn
        self.hass = hass

        self._currently_playing: Optional[dict] = {}
        self._devices: Optional[List[dict]] = []
        self._current_device = None
        self._current_playlist = None
        self._is_on = False
        self._next_track_no = 0
        self._total_tracks = None
        self._tracks = None
        self._playlist: Optional[dict] = None
        self._track = {}
        self.player_available = False
        self._unsub_source_listener = None

    @property
    def name(self) -> str:
        """Return the name."""
        return self._name

    @property
    def icon(self) -> str:
        """Return the icon."""
        return ICON

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.player_available

    @property
    def unique_id(self) -> str:
        """Return the unique ID."""
        return self._id

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self._id)},
            "manufacturer": "Samarth",
            "model": f"Saavn".rstrip(),
            "name": self._name,
        }

    @property
    def state(self) -> Optional[str]:
        """Return the playback state."""
        if self._current_device is None or self.hass.states.get(self._current_device).state == 'off' or not self._is_on:
            return STATE_OFF
        elif self._current_device is None or self.hass.states.get(self._current_device).state == 'idle':
            return STATE_IDLE            
        elif self.hass.states.get(self._current_device).state == 'playing':
            return STATE_PLAYING    
        else: return STATE_PAUSED

    @property
    def volume_level(self) -> Optional[float]:
        """Return the device volume."""
        return self._current_device_attribute('volume_level')

    @property
    def media_content_id(self) -> Optional[str]:
        """Return the media URL."""
        return self._current_device_attribute('media_content_id')

    @property
    def media_content_type(self) -> Optional[str]:
        """Return the media type."""
        return MEDIA_TYPE_MUSIC

    @property
    def media_duration(self) -> Optional[int]:
        """Duration of current playing media in seconds."""
        return self._current_device_attribute('media_duration')


    @property
    def media_position(self) -> Optional[str]:
        """Position of current playing media in seconds."""
        return self._current_device_attribute('media_position')

    @property
    def media_position_updated_at(self) -> Optional[dt.datetime]:
        """When was the position of the current playing media valid."""
        return self._current_device_attribute('media_position_updated_at')

    @property
    def media_image_url(self) -> Optional[str]:
        """Return the media image URL."""
        if self._current_device is None:
           return None
        return self._track.get('image', '')

    @property
    def media_image_remotely_accessible(self) -> bool:
        """If the image url is remotely accessible."""
        return True

    @property
    def media_title(self) -> Optional[str]:
        """Return the media title."""
        item = self._currently_playing.get("item") or {}
        return item.get("name")

    @property
    def media_artist(self) -> Optional[str]:
        """Return the media artist."""
        return self._track.get('primary_artists', '')

    @property
    def media_album_name(self) -> Optional[str]:
        """Return the media album."""
        return self._track.get('album', '')

    @property
    def media_track(self) -> Optional[int]:
        """Track number of current playing media, music track only."""
        return self._track.get('music_id', '')

    @property
    def media_playlist(self):
        """Title of Playlist currently playing."""
        if self._playlist is None:
            return None
        return self._playlist["name"]

    @property
    def source(self) -> Optional[str]:
        """Return the current playback device."""
        return self._current_device_attribute('friendly_name')

    def _current_device_attribute(self, name) -> Optional[str]:
        """Return the current playback device."""
        if self._current_device is None or name not in self.hass.states.get(self._current_device).attributes:
           return None
        return self.hass.states.get(self._current_device).attributes[name]

    @property
    def source_list(self) -> Optional[List[str]]:
        """Return a list of source devices."""
        if not self._devices:
            return None
        return [self.hass.states.get(device).attributes['friendly_name'] for device in self._devices]

    @property
    def shuffle(self) -> bool:
        """Shuffling state."""
        return True

    @property
    def supported_features(self) -> int:
        """Return the media player features that are supported."""
        return SUPPORT_SAAVN
    
    async def async_turn_on(self):
        """Turn on the media player."""
        if(self._current_device is None):
            raise Exception("Select a source device!")
        if self._unsub_source_listener:
            self._unsub_source_listener() 
            self._unsub_source_listener = None           
        self._is_on = True            
        await self.async_media_play()
    
    async def async_turn_off(self):
        """Turn off media player."""
        self._is_on = False        
        if self._unsub_source_listener:
            self._unsub_source_listener()
            self._unsub_source_listener = None 
        data = {ATTR_ENTITY_ID: self._current_device}
        await self.hass.services.async_call(DOMAIN_MP, 'turn_off', data)

    async def async_set_volume_level(self, volume: int) -> None:
        """Set the volume level."""
        data = {ATTR_ENTITY_ID: self._current_device, 'volume_level': volume}
        self.hass.async_add_job(
             self.hass.services.async_call(DOMAIN_MP, 'volume_set', data)
        )
        self.schedule_update_ha_state()

        #self._spotify.volume(int(volume * 100))

    async def async_media_play(self):
        """Start or resume playback."""
        if 1 != 1:
            self._next_track_no = random.randrange(self._total_tracks) - 1
        else:
            self._next_track_no = self._next_track_no + 1
            if self._next_track_no >= self._total_tracks:
                self._next_track_no = 0         ## Restart curent playlist (Loop)
                #random.shuffle(self._tracks)    ## (re)Shuffle on Loop
        self._track = self._tracks[self._next_track_no]
        if self._track is None:
            self._turn_off_media_player()
            return
        _url = self._track['media_url']
        
        self._is_on = True
        data = {
            ATTR_MEDIA_CONTENT_ID: _url,
            ATTR_MEDIA_CONTENT_TYPE: "audio/mp3",
            ATTR_ENTITY_ID: self._current_device
            }
        self.hass.async_add_job(
             self.hass.services.async_call(DOMAIN_MP, SERVICE_PLAY_MEDIA, data)  
        )
        @callback
        def state_listener(entity_id, old_state, new_state):
            if self._is_on:
              self.hass.async_add_job(self.async_media_next_track())
              
        if( self._unsub_source_listener is None):
            self._unsub_source_listener = async_track_state_change(self.hass, self._current_device, state_listener, 'playing', 'idle')     
        self.schedule_update_ha_state()

    async def async_media_pause(self) -> None:
        """Pause playback."""
        data = {ATTR_ENTITY_ID: self._current_device}
        self.hass.async_add_job(
             self.hass.services.async_call(DOMAIN_MP, 'media_pause', data)
        )
        self.schedule_update_ha_state()

    async def async_media_stop(self, **kwargs):
        """Send stop command."""
        data = {ATTR_ENTITY_ID: self._entity_ids}
        self.hass.async_add_job(
             self.hass.services.async_call(DOMAIN_MP, 'media_stop', data)
        )    
        self.schedule_update_ha_state() 

    async def async_media_previous_track(self) -> None:
        """Skip to previous track."""
        self._next_track_no = max(self._next_track_no - 2, -1)
        await self.async_media_play()

    async def async_media_next_track(self) -> None:
        """Skip to next track."""
        await self.async_media_play()

    async def async_media_seek(self, position):
        """Send seek command."""
        #self._spotify.seek_track(int(position * 1000))

    async def async_play_media(self, media_type: str, media_id: str, **kwargs) -> None:
        """Play media."""
        await self._load(media_type, media_id)

    async def async_select_source(self, source: str) -> None:
        """Select playback device."""
        for device in self._devices:
            if self.hass.states.get(device).attributes['friendly_name'] == source:
                self._current_device = device
                return            
        return

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Enable/Disable shuffle mode."""
        #self._spotify.shuffle(shuffle)

    @saavn_exception_handler
    def update(self) -> None:
        """Update state and attributes."""
        if not self.enabled:
            return
        self._update_devices()


    def _update_devices(self, now=None):
        self._devices = self.hass.states.entity_ids(DOMAIN_MP)        

    async def _load(self, media_type, playlist):
        """ Load selected playlist to the track_queue """
        if self._current_device is None or playlist is None:
            return
        if media_type == MEDIA_TYPE_PLAYLIST:
            self._current_playlist = await self.hass.async_add_executor_job(self._saavn.get_playlist, playlist)
        elif media_type == MEDIA_TYPE_ALBUM:
            self._current_playlist = await self.hass.async_add_executor_job(self._saavn.get_album, playlist)      
        else:
            _LOGGER.error("Media type %s is not supported", media_type)
            return
        self._tracks = None
        self._tracks = self._current_playlist['songs']
        self._total_tracks = len(self._tracks)
        self.hass.async_add_job(
             self.async_media_play()
        )         


