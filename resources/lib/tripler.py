from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time, sys, os
from xbmcswift2 import Plugin, ListItem, xbmcgui
from xbmcaddon import Addon
import xbmcgui
import xbmc

from resources.lib.scraper import Scraper
from resources.lib.website import TripleRWebsite

from urllib.parse import parse_qs, urlencode, quote, unquote

class TripleR():
    def __init__(self):
        self.plugin = Plugin()
        self.url = 'plugin://plugin.audio.tripler'
        self.addon = Addon()
        self._respath = os.path.join(self.addon.getAddonInfo('path'), 'resources')
        self.icon = os.path.join(self._respath, 'icon.png')
        self.fanart = os.path.join(self._respath, 'fanart.png')
        self.website = TripleRWebsite(os.path.join(self._respath, 'cookies.lwp'))

        self.nextpage = self.plugin.get_string(30004)
        self.lastpage = self.plugin.get_string(30005)

    def _notify(self, title, message):
        xbmc.log(f'{title} - {message}', xbmc.LOGDEBUG)
        xbmcgui.Dialog().notification(title, message, icon=self.icon)

    def run(self):
        self.plugin.run()

    def parse(self):
        args = parse_qs(sys.argv[2][1:])
        segments = sys.argv[0].split('/')[3:]
        xbmc.log("TripleR plugin called: " + str(sys.argv), xbmc.LOGINFO)

        if 'schedule' in segments and args.get('picker'):
            date = self.select_date(args.get('picker')[0])
            if date:
                args['date'] = date

        if args.get('picker'):
            del args['picker']

        path = '/{}{}{}'.format('/'.join(segments), '?' if args else '', urlencode(args, doseq=True))

        if len(segments[0]) < 1:
            return self.main_menu()
        elif 'settings' in segments:
            Addon().openSettings()
        elif 'entries' in segments:
            if self.addon.getSetting('use-account') == 'true':
                self.subscriber_giveaway(path=path)
            else:
                self._notify(self.plugin.get_string(30073), self.plugin.get_string(30076))
        else:
            parsed = self.parse_programs(**Scraper.call(path), args=args, segments=segments)
            if parsed:
                return parsed

    def main_menu(self):
        items = [
            self.livestream_item(),
            {'label': self.plugin.get_string(30032), 'path': f'{self.url}/programs'},
            {'label': self.plugin.get_string(30033), 'path': f'{self.url}/schedule'},
            {'label': self.plugin.get_string(30034), 'path': f'{self.url}/broadcasts'},
            {'label': self.plugin.get_string(30035), 'path': f'{self.url}/segments'},
            {'label': self.plugin.get_string(30036), 'path': f'{self.url}/archives'},
            {'label': self.plugin.get_string(30037), 'path': f'{self.url}/featured_albums'},
            {'label': self.plugin.get_string(30038), 'path': f'{self.url}/soundscapes'},
            {'label': self.plugin.get_string(30039), 'path': f'{self.url}/events'},
            {'label': self.plugin.get_string(30040), 'path': f'{self.url}/giveaways'},
            {'label': self.plugin.get_string(30009), 'path': f'{self.url}/settings'},
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

    def select_date(self, self_date):
        self_date_str   = '/'.join([i for i in self_date.split('-')[::-1]])
        dialog_title    = self.plugin.get_string(30065) % (self.plugin.get_string(30033))
        picked_date_str = xbmcgui.Dialog().input(dialog_title, defaultt=str(self_date_str), type=xbmcgui.INPUT_DATE)

        if picked_date_str:
            date_str    = '-'.join([i.zfill(2) for i in picked_date_str.replace(' ', '').split('/')[::-1]])
            current     = datetime(*(time.strptime(date_str, '%Y-%m-%d')[0:6]))
            daydelta    = current - datetime.utcnow() + timedelta(hours=10 + 6)
            if daydelta.days != -1:
                return date_str

        return None

    def parse_programs(self, data, args, segments, links=None):
        items = []

        for menuitem in data:
            if menuitem is None:
                continue
            if menuitem.get('auth'):
                if not self.login() or not self.website.subscribed():
                    continue

            textbody = menuitem.get('textbody', '')
            if menuitem.get('subtitle'):
                textbody  = '\n'.join((self.plugin.get_string(30007) % (menuitem['subtitle']), textbody))
            if menuitem.get('venue'):
                textbody  = '\n'.join((menuitem['venue'], textbody))

            if menuitem.get('plugin'):
                title     = '{} ({})'.format(menuitem.get('title'), menuitem.get('plugin'))
                textbody  = '{}\nPlay with {}'.format(textbody, menuitem.get('plugin'))
            else:
                title = menuitem.get('title')

            if menuitem.get('type') == 'giveaway' and 'entries' in menuitem.get('resource_path', '').split('/'):
                title += ' ({})'.format(self.plugin.get_string(30069))
                textbody  = '\n'.join((self.plugin.get_string(30070), textbody))

            if menuitem.get('start') and menuitem.get('end'):
                datestart = datetime.fromisoformat(menuitem['start'])
                dateend   = datetime.fromisoformat(menuitem['end'])
                start     = datetime.strftime(datestart, '%H:%M')
                end       = datetime.strftime(dateend,   '%H:%M')
                textbody  = '\n'.join((f'{start} - {end}', textbody))
                title     = ' - '.join((start, end, title))


            if menuitem.get('aired'):
                aired     = self.plugin.get_string(30006) % (menuitem['aired'])
            else:
                aired     = menuitem.get('date', '')

            thumbnail = menuitem.get('thumbnail', '')
            pathurl   = menuitem.get('url')

            if pathurl:
                is_playable = not pathurl.startswith('plugin://')
                mediatype = 'song'
                info_type = 'video'
            else:
                pathurl = '{}{}'.format(self.url, menuitem.get('resource_path', '/'))
                is_playable = False
                mediatype = ''
                info_type = 'video'

            date, year = menuitem.get('date', ''), menuitem.get('year', '')
            if date:
                date = time.strftime('%d.%m.%Y', time.strptime(date, '%Y-%m-%d'))
                year = date[0]
            else:
                date = time.strftime('%d.%m.%Y', time.localtime())

            item = {
                'label': title,
                'label2': aired,
                'info_type': info_type,
                'info': {
                    'count': menuitem.get('resource_path', ''),
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
                'thumbnail': thumbnail,
                'is_playable': is_playable
            }
            if mediatype:
                item['info']['mediatype'] = mediatype

            xbmc.log("menuitem: " + str(pathurl), xbmc.LOGDEBUG)

            listitem = ListItem.from_dict(**item)
            items.append(listitem)

        if 'schedule' in segments:
            self_date = links.get('self', '?date=').split('?date=')[-1]
            items.insert(0,
                {
                    'label': self.plugin.get_string(30065) % (self_date),
                    'path': f'{self.url}/schedule?picker={self_date}'
                }
            )
        elif 'giveaways' in segments and len(segments) < 2 and not self.login():
            items.insert(0,
                {
                    'label': self.plugin.get_string(30081),
                    'path': f'{self.url}/settings',
                    'thumbnail': os.path.join(self._respath, 'qr-subscribe.png'),
                }
            )
        elif links and links.get('next'):
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

    def login(self):
        if self.addon.getSetting('use-account') != 'true':
            return False

        username = self.addon.getSetting('username')
        password = self.addon.getSetting('password')
        hidesuccess = self.addon.getSetting('hide-login-msgs')

        logged_in = self.website.login(username, password)

        if logged_in:
            if hidesuccess == 'false':
                self._notify(self.plugin.get_string(30077) % (username), self.plugin.get_string(30078))
            self.account = logged_in
        else:
            self._notify(self.plugin.get_string(30079), self.plugin.get_string(30080) % (username))

        return logged_in

    def subscriber_giveaway(self, path):
        if self.login():
            source = self.website.enter(path)

            if 'Thank you! You have been entered' in source:
                self._notify(self.plugin.get_string(30071), self.plugin.get_string(30072))
            elif 'already entered this giveaway' in source:
                self._notify(self.plugin.get_string(30073), self.plugin.get_string(30074))
            else:
                self._notify(self.plugin.get_string(30073), self.plugin.get_string(30075))

        else:
            self._notify(self.plugin.get_string(30073), self.plugin.get_string(30076))

instance = TripleR()

@instance.plugin.route('/.*')
def router():
    result = instance.parse()
    if result:
        return result
