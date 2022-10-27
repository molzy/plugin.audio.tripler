from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import time, sys, os, json
from xbmcswift2 import Plugin, ListItem, xbmcgui
from xbmcaddon import Addon
import xbmcgui
import xbmc

from resources.lib.scraper import Scraper
from resources.lib.website import TripleRWebsite
from resources.lib.media   import Media

from urllib.parse import parse_qs, urlencode, unquote_plus

class TripleR():
    def __init__(self):
        self.plugin     = Plugin()
        self.id         = 'plugin.audio.tripler'
        self.url        = f'plugin://{self.id}'
        self.addon      = Addon()
        self.dialog     = xbmcgui.Dialog()
        self._respath   = os.path.join(self.addon.getAddonInfo('path'), 'resources')
        self.icon       = os.path.join(self._respath, 'icon.png')
        self.fanart     = os.path.join(self._respath, 'fanart.png')
        self.website    = TripleRWebsite(os.path.join(self._respath, 'cookies.lwp'))
        self._signed_in = -1
        self.supported_plugins = Media.RE_MEDIA_URLS.keys()

        self.nextpage   = self.plugin.get_string(30004)
        self.lastpage   = self.plugin.get_string(30005)

    def _notify(self, title, message):
        xbmc.log(f'{title} - {message}', xbmc.LOGDEBUG)
        self.dialog.notification(title, message, icon=self.icon)

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

        if 'search' in segments and not args.get('q'):
            search = self.search(tracks=('tracks' in segments))
            if search:
                args['q'] = search

        path = '/{}{}{}'.format('/'.join(segments), '?' if args else '', urlencode(args, doseq=True))

        if len(segments[0]) < 1:
            return self.main_menu()
        elif 'subscribe' in segments:
            self._notify(self.plugin.get_string(30084), self.plugin.get_string(30083))
        elif 'settings' in segments:
            self.login()
            Addon().openSettings()
        elif 'sign-in' in segments:
            if self.sign_in():
                xbmc.executebuiltin("Container.Refresh")
        elif 'sign-out' in segments:
            self.sign_out()
            xbmc.executebuiltin("Container.Refresh")
        elif 'entries' in segments:
            if self.addon.getSettingBool('authenticated'):
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
            {'label': self.plugin.get_string(30032), 'path': f'{self.url}/programs', 'icon': 'DefaultPartyMode.png'},
            {'label': self.plugin.get_string(30033), 'path': f'{self.url}/schedule', 'icon': 'DefaultYear.png'},
            {'label': self.plugin.get_string(30034), 'path': f'{self.url}/broadcasts', 'icon': 'DefaultPlaylist.png'},
            {'label': self.plugin.get_string(30035), 'path': f'{self.url}/segments', 'icon': 'DefaultPlaylist.png'},
            {'label': self.plugin.get_string(30036), 'path': f'{self.url}/archives', 'icon': 'DefaultPlaylist.png'},
            {'label': self.plugin.get_string(30037), 'path': f'{self.url}/featured_albums', 'icon': 'DefaultMusicAlbums.png'},
            {'label': self.plugin.get_string(30038), 'path': f'{self.url}/soundscapes', 'icon': 'DefaultSets.png'},
            {'label': self.plugin.get_string(30039), 'path': f'{self.url}/events', 'icon': 'DefaultPVRGuide.png'},
            {'label': self.plugin.get_string(30040), 'path': f'{self.url}/giveaways', 'icon': 'DefaultAddonsRecentlyUpdated.png'},
            {'label': self.plugin.get_string(30041), 'path': f'{self.url}/search', 'icon': 'DefaultMusicSearch.png'},
        ]
        if self.login():
            emailaddress = self.addon.getSetting('emailaddress')
            fullname = self.addon.getSetting('fullname')
            name = fullname if fullname else emailaddress
            items.append(
                {
                    'label':     f'{self.plugin.get_string(30014)} ({name})',
                    'path':      f'{self.url}/sign-out',
                    'thumbnail':  'DefaultUser.png',
                }
            )
        else:
            items.append(
                {
                    'label':      self.plugin.get_string(30013),
                    'path':      f'{self.url}/sign-in',
                    'thumbnail':  'DefaultUser.png',
                }
            )
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
        picked_date_str = self.dialog.input(dialog_title, defaultt=str(self_date_str), type=xbmcgui.INPUT_DATE)

        if picked_date_str:
            date_str    = '-'.join([i.zfill(2) for i in picked_date_str.replace(' ', '').split('/')[::-1]])
            current     = datetime(*(time.strptime(date_str, '%Y-%m-%d')[0:6]), tzinfo=timezone.utc)
            daydelta    = datetime.now(timezone.utc) - current + timedelta(hours=10 - 6)
            if daydelta.days != 0:
                return date_str

        return None

    def context_item(self, label, path):
        return (self.plugin.get_string(label), f'Container.Update({self.url}{path})')

    def parse_programs(self, data, args, segments, links=None):
        items = []

        for menuitem in data:
            if menuitem is None:
                continue
            m_id, m_type = menuitem.get('id', ''), menuitem.get('type', '')
            m_links      = menuitem.get('links', {})
            m_self       = m_links.get('self', '/')
            m_sub        = m_links.get('subscribe')
            m_playlist   = m_links.get('playlist')
            attributes   = menuitem.get('attributes', {})
            if attributes is None:
                continue

            textbody        = attributes.get('textbody', '')
            thumbnail       = attributes.get('thumbnail', '')
            fanart          = attributes.get('background', self.fanart)

            if attributes.get('subtitle'):
                textbody    = '\n'.join((self.plugin.get_string(30007) % (attributes['subtitle']), textbody))
            if attributes.get('venue'):
                textbody    = '\n'.join((attributes['venue'], textbody))

            if m_type in self.supported_plugins:
                title       = attributes.get('title', '')
                name        = Media.RE_MEDIA_URLS[m_type].get('name')
                title       = f'{title} ({name})'
                artist      = attributes.get('artist')
                if artist:
                    title   = f'{artist} - {title}'
                textbody    = f'{textbody}\nPlay with {name}'
                pathurl     = Media.parse_media_id(m_type, m_id)
                if len(thumbnail) < 1:
                    thumbnail   = 'DefaultMusicSongs.png'
                if m_type in ['bandcamp_track', 'youtube']:
                    is_playable = True
                else:
                    is_playable = False
            else:
                title       = attributes.get('title', '')
                artist      = attributes.get('artist')
                if artist:
                    title   = f'{artist} - {title}'
                pathurl     = attributes.get('url')
                is_playable = True

            if m_type == 'program_broadcast_track':
                thumbnail   = 'DefaultMusicSongs.png'
                pathurl     = m_links.get('broadcast_track')
                is_playable = False

            if m_sub:
                if not self.login() or not self.subscribed():
                    icon        =  'OverlayLocked.png'
                    title       = f'Subscribe To Listen - {title}'
                    textbody    = f'{self.plugin.get_string(30084)}\n{textbody}'
                    pathurl     = f'{self.url}{m_sub}'
                    is_playable = False
                else:
                    title       = f'Subscribers Only - {title}'


            if m_type == 'giveaway' and 'entries' in m_self.split('/'):
                title      += ' ({})'.format(self.plugin.get_string(30069))
                textbody    = '\n'.join((self.plugin.get_string(30070), textbody))

            if attributes.get('start') and attributes.get('end'):
                datestart   = datetime.fromisoformat(attributes['start'])
                dateend     = datetime.fromisoformat(attributes['end'])
                start       = datetime.strftime(datestart, '%H:%M')
                end         = datetime.strftime(dateend,   '%H:%M')
                textbody    = f'{start} - {end}\n{textbody}'
                title       = ' - '.join((start, end, title))


            if attributes.get('aired'):
                aired       = self.plugin.get_string(30006) % (attributes['aired'])
            else:
                aired       = attributes.get('date', '')

            if pathurl:
                mediatype   = 'song'
                info_type   = 'video'
            else:
                pathurl     = f'{self.url}{m_self}'
                is_playable = False
                mediatype   = ''
                info_type   = 'video'

            date, year = attributes.get('date', ''), attributes.get('year', '')
            if date:
                date = time.strftime('%d.%m.%Y', time.strptime(date, '%Y-%m-%d'))
                year = date[0]
            else:
                date = time.strftime('%d.%m.%Y', time.localtime())

            icon = thumbnail

            item = {
                'label':     title,
                'label2':    aired,
                'info_type': info_type,
                'info': {
                    'count':     m_id,
                    'title':     title,
                    'plot':      textbody,
                    'date':      date,
                    'year':      year,
                    'premiered': aired,
                    'aired':     aired,
                    'duration':  attributes.get('duration', ''),
                },
                'properties': {
                    'StationName':  self.plugin.get_string(30000),
                    'fanart_image': fanart
                },
                'path':        pathurl,
                'thumbnail':   thumbnail,
                'icon':        icon,
                'is_playable': is_playable
            }
            if mediatype:
                item['info']['mediatype'] = mediatype

            context_menu = []

            if m_playlist:
                context_menu.append(self.context_item(30101, m_playlist))

            if 'broadcast_track' in m_links:
                context_menu.append(self.context_item(30102, m_links.get('broadcast_track')))

            if 'broadcast_artist' in m_links:
                context_menu.append(self.context_item(30103, m_links.get('broadcast_artist')))

            if context_menu:
                item['context_menu'] = context_menu
                item['replace_context_menu'] = True

            listitem = ListItem.from_dict(**item)
            items.append(listitem)

        if 'schedule' in segments:
            self_date = links.get('self', '?date=').split('?date=')[-1]
            items.insert(0,
                {
                    'label': self.plugin.get_string(30065) % (self_date),
                    'path':  f'{self.url}/schedule?picker={self_date}',
                    'icon':   'DefaultPVRGuide.png'
                }
            )
        elif 'giveaways' in segments:
            if not self.login() or not self.subscribed():
                items.insert(0, self._sub_item(self.plugin.get_string(30082)))
        elif links and links.get('next'):
            if len(items) > 0:
                if links.get('next'):
                    items.append(
                        {
                            'label': self.nextpage,
                            'path':  f'{self.url}{links["next"]}',
                            'icon':   'DefaultMusicSearch.png'
                        }
                    )
                if links.get('last'):
                    items.append(
                        {
                            'label':  self.lastpage,
                            'path':  f'{self.url}{links["last"]}',
                            'icon':   'DefaultMusicVideoTitle.pngg'
                        }
                    )

        if 'archives' in segments:
            if not self.login() or not self.subscribed():
                items.insert(0, self._sub_item(self.plugin.get_string(30083)))
        elif 'search' in segments and 'tracks' not in segments:
            link = links.get('self').split('?page=')[0]
            items.insert(0,
                {
                    'label': self.plugin.get_string(30066),
                    'path':  f'{self.url}/tracks{link}',
                    'icon':   'DefaultMusicSearch.png'
                }
            )

        return items

    def search(self, tracks=False):
        prompt = self.plugin.get_string(30068 if tracks else 30067)
        return self.dialog.input(prompt, type=xbmcgui.INPUT_ALPHANUM)

    def sign_in(self):
        emailaddress = self.dialog.input(self.plugin.get_string(30015), type=xbmcgui.INPUT_ALPHANUM)
        if emailaddress == '':
            return False
        password = self.dialog.input(self.plugin.get_string(30016), type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if password == '':
            return False
        return self.login(prompt=True, emailaddress=emailaddress, password=password)

    def login(self, prompt=False, emailaddress=None, password=None):
        if self._signed_in != -1:
            return self._signed_in
        if self.addon.getSettingBool('authenticated') and self.website.logged_in():
            return True

        emailSetting = self.addon.getSetting('emailaddress')
        if emailaddress is None:
            emailaddress = emailSetting

        logged_in = self.website.login(emailaddress, password)

        if logged_in:
            if prompt:
                self._notify(self.plugin.get_string(30077) % (emailaddress), self.plugin.get_string(30078))
            if not self.addon.getSettingBool('authenticated'):
                self.addon.setSetting('subscribed-check', '0')
                self.subscribed()
                self.addon.setSettingBool('authenticated', True)

            if emailSetting == '':
                self.addon.setSetting('emailaddress', emailaddress)
            for cookie in logged_in:
                if cookie.name == 'account':
                    fullname = json.loads(unquote_plus(cookie.value)).get('name')
                    if fullname:
                        self.addon.setSetting('fullname', fullname)
            self._signed_in = logged_in
        else:
            if prompt:
                self._notify(self.plugin.get_string(30085), self.plugin.get_string(30086) % (emailaddress))
            self.addon.setSettingBool('authenticated', False)
            self.addon.setSetting('emailaddress', '')
            self.addon.setSetting('fullname', '')

        return logged_in

    def sign_out(self, emailaddress=None):
        if emailaddress is None:
            emailaddress = self.addon.getSetting('emailaddress')
        if self.website.logout():
            self.addon.setSettingBool('authenticated', False)
            self.addon.setSetting('subscribed-check', '0')
            self._signed_in = -1
            if emailaddress:
                self._notify(self.plugin.get_string(30079) % (emailaddress), self.plugin.get_string(30078))
            self.addon.setSetting('emailaddress', '')
            self.addon.setSetting('fullname', '')
            return True
        else:
            if emailaddress:
                self._notify(self.plugin.get_string(30087), self.plugin.get_string(30088) % (emailaddress))
            return False

    def subscribed(self):
        if not self.addon.getSettingBool('authenticated'):
            return False
        check          = int(self.addon.getSetting('subscribed-check'))
        now            = int(time.time())
        if now - check < (15*60):
            setting    = self.addon.getSettingInt('subscribed')
            subscribed = (setting == 1)
        else:
            subscribed = self.website.subscribed()
            self.addon.setSettingInt('subscribed', 1 if subscribed else 0)
            self.addon.setSetting('subscribed-check', str(now))
        return subscribed

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
