from bs4 import BeautifulSoup
import time, sys, os
from xbmcswift2 import Plugin, ListItem, xbmcgui
from xbmcaddon import Addon
import xbmc

from resources.lib.scraper import Scraper

IS_PY3 = sys.version_info[0] > 2
if IS_PY3:
    from urllib.parse import parse_qs
else:
    from urlparse import parse_qs

class TripleR():
    def __init__(self):
        self.plugin = Plugin()
        self.url = 'plugin://plugin.audio.tripler'
        respath = os.path.join(Addon().getAddonInfo('path'), 'resources')
        self.icon = os.path.join(respath, 'icon.png')
        self.fanart = os.path.join(respath, 'fanart.png')
        self.nextpage = self.plugin.get_string(30004)
        self.lastpage = self.plugin.get_string(30005)

    def run(self):
        self.plugin.run()

    def parse(self):
        args = parse_qs(sys.argv[2][1:])
        segments = sys.argv[0].split('/')[3:]
        xbmc.log("TripleR plugin called: " + str(sys.argv), xbmc.LOGDEBUG)
        if len(segments[0]) < 1:
            return self.main_menu()
        elif 'settings' in segments:
            Addon().openSettings()
            return None
        else:
            path = '/'.join(segments) + str(sys.argv[2])
            return self.parse_programs(**Scraper.call(path), args=args, segments=segments)

    def main_menu(self):
        items = [
            {
                'label': self.plugin.get_string(30001),
                'path': "https://ondemand.rrr.org.au/stream/ws-hq.m3u",
                'thumbnail': self.icon,
                'properties': {
                    'StationName': self.plugin.get_string(30000),
                    'fanart_image': self.fanart
                },
                'info': {
                    'mediatype': 'music'
                },
                'is_playable': True
            },
            {'label': self.plugin.get_string(30032), 'path': f'{self.url}/programs'},
            {'label': self.plugin.get_string(30033), 'path': f'{self.url}/segments'},
            {'label': self.plugin.get_string(30034), 'path': f'{self.url}/broadcasts'},
            {'label': self.plugin.get_string(30035), 'path': f'{self.url}/archives'},
            {'label': self.plugin.get_string(30036), 'path': f'{self.url}/albumoftheweek'},
            {'label': self.plugin.get_string(30037), 'path': f'{self.url}/soundscapes'},
            # {'label': self.plugin.get_string(30038), 'path': f'{self.url}/schedule'},
            {'label': self.plugin.get_string(30039), 'path': f'{self.url}/events'},
            {'label': self.plugin.get_string(30010), 'path': f'{self.url}/settings'},
        ]
        listitems = [ListItem.from_dict(**item) for item in items]
        return listitems

    def parse_programs(self, data, args, segments, links=None):
        items = []

        for menuitem in data:
            if menuitem is None:
                continue

            if 'subtitle' in menuitem.keys():
                textbody = '\n'.join((self.plugin.get_string(30007), '%s')) % (menuitem['subtitle'], menuitem['textbody'])
            else:
                textbody = menuitem['textbody'] if 'textbody' in menuitem.keys() else ''

            if 'venue' in menuitem.keys():
                textbody = '\n'.join((menuitem['venue'], textbody))
            if 'aired' in menuitem.keys():
                aired = self.plugin.get_string(30006) % (menuitem['aired'])
            else:
                aired = ''

            if 'url' in menuitem.keys():
                pathurl = menuitem['url']
                is_playable = not pathurl.startswith('plugin://')
                mediatype = 'song'
            else:
                pathurl = '{}/{}/{}'.format(self.url, '/'.join(segments), menuitem['id'])
                is_playable = False
                mediatype = ''

            item = {
                'label': menuitem['title'],
                'label2': aired,
                'info_type': 'video',
                'info': {
                    'count': menuitem['id'],
                    'title': menuitem['title'],
                    'plot': textbody,
                    'date': menuitem['date'] if 'date' in menuitem.keys() else '',
                    'year': menuitem['year'] if 'year' in menuitem.keys() else '',
                    'premiered': aired,
                    'aired': aired,
                    'duration': menuitem['duration'] if 'duration' in menuitem.keys() else '',
                },
                'properties': {
                    'StationName': self.plugin.get_string(30000),
                    'fanart_image': self.fanart
                },
                'path': pathurl,
                'thumbnail': menuitem['thumbnail'] if 'thumbnail' in menuitem.keys() else '',
                'is_playable': is_playable
            }
            if mediatype:
                item['info']['mediatype'] = mediatype
            xbmc.log("menuitem: " + str(pathurl), xbmc.LOGDEBUG)
            listitem = ListItem.from_dict(**item)
            items.append(listitem)

        if links and links.get('next'):
            if len(items) > 0:
                if links.get('next'):
                    items.append(
                        {
                            'label': self.nextpage,
                            'path': '{}/{}'.format(self.url, links['next'])
                        }
                    )
                if links.get('last'):
                    items.append(
                        {
                            'label': self.lastpage,
                            'path': '{}/{}'.format(self.url, links['last'])
                        }
                    )

        return items

instance = TripleR()

@instance.plugin.route('/.*')
def router():
    result = instance.parse()
    return result
