import re

class Media:
    RE_BANDCAMP_ALBUM_ID             = re.compile(r'https://bandcamp.com/EmbeddedPlayer/.*album=(?P<media_id>[^/]+)')
    RE_BANDCAMP_ALBUM_ART            = re.compile(r'"art_id":(\w+)')
    BANDCAMP_PLUGIN_BASE_URL         = 'plugin://plugin.audio.kxmxpxtx.bandcamp/?mode=list_songs'
    BANDCAMP_PLUGIN_FORMAT           = '{}&album_id={}&item_type=a'
    BANDCAMP_ALBUM_ART_URL           = 'https://bandcamp.com/api/mobile/24/tralbum_details?band_id=1&tralbum_type=a&tralbum_id={}'

    RE_SOUNDCLOUD_PLAYLIST_ID        = re.compile(r'.+soundcloud\.com/playlists/(?P<media_id>[^&]+)')
    SOUNDCLOUD_PLUGIN_BASE_URL       = 'plugin://plugin.audio.soundcloud/'
    SOUNDCLOUD_PLUGIN_FORMAT         = '{}?action=call&call=/playlists/{}'

    RE_YOUTUBE_VIDEO_ID              = re.compile(r'^(?:(?:https?:)?\/\/)?(?:(?:www|m)\.)?(?:youtube(?:-nocookie)?\.com|youtu.be)(?:\/(?:[\w\-]+\?v=|embed\/|v\/)?)(?P<media_id>[\w\-]+)(?!.*list)\S*$')
    YOUTUBE_PLUGIN_BASE_URL          = 'plugin://plugin.video.youtube/play/'
    YOUTUBE_VIDEO_PLUGIN_FORMAT      = '{}?video_id={}'

    RE_YOUTUBE_PLAYLIST_ID           = re.compile(r'^(?:(?:https?:)?\/\/)?(?:(?:www|m)\.)?(?:youtube(?:-nocookie)?\.com|youtu.be)\/.+\?.*list=(?P<media_id>[\w\-]+)')
    YOUTUBE_PLAYLIST_PLUGIN_FORMAT   = '{}?playlist_id={}&order=default&play=1'

    RE_INDIGITUBE_ALBUM_ID           = re.compile(r'https://www.indigitube.com.au/embed/album/(?P<media_id>[^"]+)')

    RE_MEDIA_URLS = {
        'bandcamp': {
            're':     RE_BANDCAMP_ALBUM_ID,
            'base':   BANDCAMP_PLUGIN_BASE_URL,
            'format': BANDCAMP_PLUGIN_FORMAT,
            'name':   'Bandcamp',
        },
        'soundcloud': {
            're':     RE_SOUNDCLOUD_PLAYLIST_ID,
            'base':   SOUNDCLOUD_PLUGIN_BASE_URL,
            'format': SOUNDCLOUD_PLUGIN_FORMAT,
            'name':   'SoundCloud',
        },
        'youtube': {
            're':     RE_YOUTUBE_VIDEO_ID,
            'base':   YOUTUBE_PLUGIN_BASE_URL,
            'format': YOUTUBE_VIDEO_PLUGIN_FORMAT,
            'name':   'YouTube',
        },
        'youtube_playlist': {
            're':     RE_YOUTUBE_PLAYLIST_ID,
            'base':   YOUTUBE_PLUGIN_BASE_URL,
            'format': YOUTUBE_PLAYLIST_PLUGIN_FORMAT,
            'name':   'YouTube',
        },
        'indigitube': {
            're':     RE_INDIGITUBE_ALBUM_ID,
            'base':   '',
            'format': '',
            'name':   'IndigiTube',
        },
    }

    @classmethod
    def parse_media_id(cls, plugin, media_id):
        info = cls.RE_MEDIA_URLS.get(plugin, {})
        return info.get('format').format(info.get('base'), media_id)

