import re

class Media:
    RE_BANDCAMP_ALBUM_ID             = re.compile(r'https://bandcamp.com/EmbeddedPlayer/.*album=(?P<media_id>[^/]+)')
    RE_BANDCAMP_ALBUM_ART            = re.compile(r'"art_id":(\w+)')
    BANDCAMP_ALBUM_PLUGIN_BASE_URL   = 'plugin://plugin.audio.kxmxpxtx.bandcamp/?mode=list_songs'
    BANDCAMP_ALBUM_PLUGIN_FORMAT     = '{}&album_id={}&item_type=a'
    BANDCAMP_ALBUM_ART_URL           = 'https://bandcamp.com/api/mobile/24/tralbum_details?band_id=1&tralbum_type=a&tralbum_id={}'

    RE_BANDCAMP_TRACK_ID             = re.compile(r'(?P<media_id>https?://[^/\.]+\.bandcamp.com/track/[\w\-]+)')
    BANDCAMP_TRACK_PLUGIN_BASE_URL   = 'plugin://plugin.audio.kxmxpxtx.bandcamp/?mode=url'
    BANDCAMP_TRACK_PLUGIN_FORMAT     = '{}&url={}'
    RE_BANDCAMP_TRACK_ART            = re.compile(r'art_id&quot;:(?P<art_id>\d+),')
    RE_BANDCAMP_TRACK_BAND_ART       = re.compile(r'data-band="[^"]*image_id&quot;:(?P<band_art_id>\d+)}"')

    RE_SOUNDCLOUD_PLAYLIST_ID        = re.compile(r'.+soundcloud\.com/playlists/(?P<media_id>[^&]+)')
    SOUNDCLOUD_PLUGIN_BASE_URL       = 'plugin://plugin.audio.soundcloud/'
    SOUNDCLOUD_PLUGIN_FORMAT         = '{}?action=call&call=/playlists/{}'

    RE_YOUTUBE_VIDEO_ID              = re.compile(r'^(?:(?:https?:)?\/\/)?(?:(?:www|m)\.)?(?:youtube(?:-nocookie)?\.com|youtu.be)(?:\/(?:[\w\-]+\?v=|embed\/|v\/)?)(?P<media_id>[\w\-]+)(?!.*list)\S*$')
    YOUTUBE_PLUGIN_BASE_URL          = 'plugin://plugin.video.youtube/play/'
    YOUTUBE_VIDEO_PLUGIN_FORMAT      = '{}?video_id={}&play=1'
    YOUTUBE_VIDEO_ART_URL_FORMAT     = 'https://i.ytimg.com/vi/{}/hqdefault.jpg'

    RE_YOUTUBE_PLAYLIST_ID           = re.compile(r'^(?:(?:https?:)?\/\/)?(?:(?:www|m)\.)?(?:youtube(?:-nocookie)?\.com|youtu.be)\/.+\?.*list=(?P<media_id>[\w\-]+)')
    YOUTUBE_PLAYLIST_PLUGIN_FORMAT   = '{}?playlist_id={}&order=default&play=1'
    YOUTUBE_PLAYLIST_ART_URL         = 'https://youtube.com/oembed?url=https%3A//www.youtube.com/playlist%3Flist%3D{}&format=json'

    RE_INDIGITUBE_ALBUM_ID           = re.compile(r'https://www.indigitube.com.au/embed/album/(?P<media_id>[^"]+)')

    RE_MEDIA_URLS = {
        'bandcamp': {
            're':     RE_BANDCAMP_ALBUM_ID,
            'base':   BANDCAMP_ALBUM_PLUGIN_BASE_URL,
            'format': BANDCAMP_ALBUM_PLUGIN_FORMAT,
            'name':   'Bandcamp',
        },
        'bandcamp_track': {
            're':     RE_BANDCAMP_TRACK_ID,
            'base':   BANDCAMP_TRACK_PLUGIN_BASE_URL,
            'format': BANDCAMP_TRACK_PLUGIN_FORMAT,
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

