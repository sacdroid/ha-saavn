# ha-saavn
Play Saavn music on HomeAssistent enabled media players like chromecast, receiver or tv.

This component allows you to play playlist albums from Jio Saavn on [HomeAssistent](https://www.home-assistant.io/) enabled media players like google casts(chromecast etc), receivers. 
Currently GoogleHome/JioSaavn does not support streaming saavn music [outside of the USA](https://support.google.com/googlenest/thread/1313827?hl=en). Also it does not look it works in [India](https://support.google.com/googlenest/thread/14799752?hl=en)

#### Manual Installation (Currently only manual installation is supported. HACS installation support will be added soon) 
Inside your Home Assistant `custom_components` directory, create another named `saavn`  

Copy following files to `custom_components/saavn` in your homeassistent installation:  

[`custom_components/saavn/__init__.py`](https://github.com/sacdroid/ha-saavn//blob/master/custom_components/saavn/__init__.py)  

[`custom_components/saavn/manifest.json`](https://github.com/sacdroid/ha-saavn//blob/master/custom_components/saavn/manifest.json)  

[`custom_components/saavn/media_player.py`](https://github.com/sacdroid/ha-saavn//blob/master/custom_components/saavn/media_player.py) 

[`custom_components/saavn/saavn.py`](https://github.com/sacdroid/ha-saavn//blob/master/custom_components/saavn/saavn.py) 

### Enable saavn integration through configuration.yaml
To enable this component in your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
saavn:
```

You can then use media_player.saavn in your automation. 

Example Script

```yaml
playsaavn:
  sequence:
    - service: media_player.select_source
      data:
        entity_id: media_player.saavn
        source: office_speaker
    - delay: '00:00:10'        
    - service: media_player.play_media
      data:
       entity_id: media_player.saavn
       media_content_type: playlist
       media_content_id: 107724265
```
Note that you need to first select the media device on which you want to play music. This can be HA groups as well. Also you need to find your favorite album or playlist id from [here](https://www.jiosaavn.com/api.php?__call=content.getHomepageData).
