import json
from pyDes import *
import base64
import requests
import logging
from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)

class Saavn():

    def get_album(self, albumId):
        songs_json = []
        try:
            response = requests.get(
                '{0}?_format=json&__call=content.getAlbumDetails&albumid={1}'.format(BASE_URL, albumId), verify=False)
            if response.status_code == 200:
                songs_json = list(filter(lambda x: x.startswith(
                    "{"), response.text.splitlines()))[0]
                songs_json = json.loads(songs_json)
                songs_json['name'] = self._fix_title(songs_json['name'])
                songs_json['image'] = self._fix_image_url(songs_json['image'])
                for songs in songs_json['songs']:
                    try:
                        songs['media_url'] = self.generate_media_url(
                            songs['media_preview_url'])
                    except KeyError:
                        songs['media_url'] = self._decrypt_url(songs['encrypted_media_url'])
                    songs['image'] = self._fix_image_url(songs['image'])
                    songs['song'] = self._fix_title(songs['song'])
                    songs['album'] = self._fix_title(songs['album'])
                return songs_json
        except Exception as e:
            _LOGGER.exception("An unknown error occurred: %s", e)
            return None

    def get_playlist(self, listId):
        response = requests.get(
            '{0}?listid={1}&_format=json&__call=playlist.getDetails'.format(BASE_URL, listId), verify=False)
        if response.status_code == 200:
            response_text = (response.text.splitlines())
            songs_json = list(
                filter(lambda x: x.endswith("}"), response_text))[0]
            songs_json = json.loads(songs_json)
            songs_json['firstname'] = self._fix_title(songs_json['firstname'])
            songs_json['listname'] = self._fix_title(songs_json['listname'])
            songs_json['image'] = self._fix_image_url(songs_json['image'])
            for songs in songs_json['songs']:
                songs['image'] = self._fix_image_url(songs['image'])
                songs['song'] = self._fix_title(songs['song'])
                songs['album'] = self._fix_title(songs['album'])
                try:
                    songs['media_url'] = self._generate_media_url(
                        songs['media_preview_url'])
                except KeyError:
                    songs['media_url'] = self._decrypt_url(
                        songs['encrypted_media_url'])                      
            return songs_json
        return None
    
    def _generate_media_url(self, url):
        url = url.replace("preview", "h")
        url = url.replace("_96_p.mp4", "_320.mp3")
        return url

    def _decrypt_url(self, url):
        enc_url = base64.b64decode(url.strip())
        dec_url = des_cipher.decrypt(enc_url, padmode=PAD_PKCS5).decode('utf-8')
        dec_url = dec_url.replace("_96.mp4", "_320.mp3")
        return dec_url

    def _fix_title(self, title):
        title = title.replace('&quot;', '')
        return title

    def _fix_image_url(self, url):
        url = str(url)
        if 'http://' in url:
            url = url.replace("http://", "https://")
        url = url.replace('150x150', '500x500')
        return url
        
# this saavn encrypyion key is publically available on github and internet so nothing secret about it
des_cipher = des(b"38346591", ECB, b"\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)        