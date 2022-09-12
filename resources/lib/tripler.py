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
        xbmc.log("TripleR plugin called: " + str(sys.argv), xbmc.LOGINFO)
        if len(segments[0]) < 1:
            return self.main_menu()
        elif 'settings' in segments:
            Addon().openSettings()
        else:
            path = '/'.join(segments) + str(sys.argv[2])
            parsed = self.parse_programs(**Scraper.call(path), args=args, segments=segments)
            if parsed:
                return parsed

    def main_menu(self):
        items = [
            self.livestream_item(),
            {'label': self.plugin.get_string(30032), 'path': f'{self.url}/programs'},
            {'label': self.plugin.get_string(30033), 'path': f'{self.url}/broadcasts'},
            {'label': self.plugin.get_string(30034), 'path': f'{self.url}/segments'},
            {'label': self.plugin.get_string(30035), 'path': f'{self.url}/archives'},
            {'label': self.plugin.get_string(30036), 'path': f'{self.url}/featured_albums'},
            {'label': self.plugin.get_string(30037), 'path': f'{self.url}/soundscapes'},
            # {'label': self.plugin.get_string(30038), 'path': f'{self.url}/schedule'},
            {'label': self.plugin.get_string(30039), 'path': f'{self.url}/events'},
            # {'label': self.plugin.get_string(30010), 'path': f'{self.url}/settings'},
        ]
        listitems = [ListItem.from_dict(**item) for item in items]
        return listitems

    def livestream_item(self):
        item = {
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
        }
        return item


    def parse_programs(self, data, args, segments, links=None):
        items = []

        for menuitem in data:
            if menuitem is None:
                continue

            textbody = menuitem.get('textbody', '')
            if menuitem.get('subtitle'):
                textbody = '\n'.join((self.plugin.get_string(30007) % (menuitem['subtitle']), textbody))
            if menuitem.get('venue'):
                textbody = '\n'.join((menuitem['venue'], textbody))

            if menuitem.get('plugin'):
                title = '{} ({})'.format(menuitem.get('title'), menuitem.get('plugin'))
                textbody = '{}\nPlay with {}'.format(textbody, menuitem.get('plugin'))
            else:
                title = menuitem.get('title')

            if menuitem.get('aired'):
                aired = self.plugin.get_string(30006) % (menuitem['aired'])
            else:
                aired = menuitem.get('date', '')

            if menuitem.get('url'):
                pathurl = menuitem.get('url')
                is_playable = not pathurl.startswith('plugin://')
                mediatype = 'song'
                info_type = 'video'
            else:
                pathid = ('/' if menuitem.get('id') else '') + menuitem.get('id')
                pathurl = '{}/{}{}'.format(self.url, '/'.join(segments), pathid)
                is_playable = False
                mediatype = ''
                info_type = 'video'

            date, year = menuitem.get('date', ''), menuitem.get('year', '')
            if date:
                date = time.strftime('%d.%m.%Y', time.strptime(date, '%Y-%m-%d'))
                year = date[0]

            item = {
                'label': title,
                'label2': aired,
                'info_type': info_type,
                'info': {
                    'count': menuitem.get('id', ''),
                    'title': title,
                    'plot': textbody,
                    'date': date,
                    'year': year,
                    'premiered': aired,
                    'aired': aired,
                    'duration': menuitem.get('duration', ''),
                },
                'properties': {
                    'StationName': self.plugin.get_string(30000),
                    'fanart_image': self.fanart
                },
                'path': pathurl,
                'thumbnail': menuitem.get('thumbnail', ''),
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
    if result:
        return result
