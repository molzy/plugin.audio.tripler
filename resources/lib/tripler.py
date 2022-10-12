from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import time, sys, os
from xbmcswift2 import Plugin, ListItem, xbmcgui
from xbmcaddon import Addon
import xbmcgui
import xbmc

from resources.lib.scraper import Scraper
from resources.lib.website import TripleRWebsite
from resources.lib.media   import Media

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
        self.supported_plugins = Media.RE_MEDIA_URLS.keys()

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
        elif 'subscription_required' in segments:
            self._notify(self.plugin.get_string(30083), self.plugin.get_string(30082))
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

    def _sub_item(self, text):
        item = {
            'label': text,
            'path': f'{self.url}/settings',
            'thumbnail': os.path.join(self._respath, 'qr-subscribe.png'),
        }
        return item

    def select_date(self, self_date):
        self_date_str   = '/'.join([i for i in self_date.split('-')[::-1]])
        dialog_title    = self.plugin.get_string(30065) % (self.plugin.get_string(30033))
        picked_date_str = xbmcgui.Dialog().input(dialog_title, defaultt=str(self_date_str), type=xbmcgui.INPUT_DATE)

        if picked_date_str:
            date_str    = '-'.join([i.zfill(2) for i in picked_date_str.replace(' ', '').split('/')[::-1]])
            current     = datetime(*(time.strptime(date_str, '%Y-%m-%d')[0:6]), tzinfo=timezone.utc)
            daydelta    = datetime.now(timezone.utc) - current + timedelta(hours=10 - 6)
            if daydelta.days != 0:
                return date_str

        return None

    def parse_programs(self, data, args, segments, links=None):
        items = []

        for menuitem in data:
            m_id, m_type = menuitem.get('id', ''), menuitem.get('type', '')
            m_self       = menuitem.get('links', {}).get('self', '/')
            attributes   = menuitem.get('attributes', {})
            if attributes is None:
                continue

            textbody = attributes.get('textbody', '')
            if attributes.get('subtitle'):
                textbody    = '\n'.join((self.plugin.get_string(30007) % (attributes['subtitle']), textbody))
            if attributes.get('venue'):
                textbody    = '\n'.join((attributes['venue'], textbody))

            if m_type in self.supported_plugins:
                name        = Media.RE_MEDIA_URLS[m_type].get('name')
                title       = '{} ({})'.format(attributes.get('title', ''), name)
                textbody    = '{}\nPlay with {}'.format(textbody, name)
                pathurl     = Media.parse_media_id(m_type, m_id)
                is_playable = False
            else:
                title       = attributes.get('title', '')
                pathurl     = attributes.get('url')
                is_playable = True

            if attributes.get('subscription_required'):
                if not self.login() or not self.website.subscribed():
                    title   = f'{self.plugin.get_string(30083)} - {title}'
                    pathurl = '{}{}'.format(self.url, '/subscription_required')
                    is_playable = False

            if m_type == 'giveaway' and 'entries' in m_self.split('/'):
                title      += ' ({})'.format(self.plugin.get_string(30069))
                textbody    = '\n'.join((self.plugin.get_string(30070), textbody))

            if attributes.get('start') and attributes.get('end'):
                datestart   = datetime.fromisoformat(attributes['start'])
                dateend     = datetime.fromisoformat(attributes['end'])
                start       = datetime.strftime(datestart, '%H:%M')
                end         = datetime.strftime(dateend,   '%H:%M')
                textbody    = '\n'.join((f'{start} - {end}', textbody))
                title       = ' - '.join((start, end, title))


            if attributes.get('aired'):
                aired       = self.plugin.get_string(30006) % (attributes['aired'])
            else:
                aired       = attributes.get('date', '')

            thumbnail       = attributes.get('thumbnail', '')

            if pathurl:
                mediatype   = 'song'
                info_type   = 'video'
            else:
                pathurl     = '{}{}'.format(self.url, m_self)
                is_playable = False
                mediatype   = ''
                info_type   = 'video'

            date, year = attributes.get('date', ''), attributes.get('year', '')
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
                    'count': m_id,
                    'title': title,
                    'plot': textbody,
                    'date': date,
                    'year': year,
                    'premiered': aired,
                    'aired': aired,
                    'duration': attributes.get('duration', ''),
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

            xbmc.log("attributes: " + str(pathurl), xbmc.LOGDEBUG)

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
        elif 'giveaways' in segments and len(segments) < 2 and (not self.login() or not self.website.subscribed()):
            items.insert(0, self._sub_item(self.plugin.get_string(30081)))
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
        
        if 'archives' in segments and (not self.login() or not self.website.subscribed()):
            items.insert(0, self._sub_item(self.plugin.get_string(30082)))

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
