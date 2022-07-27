#!/usr/bin/env python
"""
# Example Usages:

scraper.py programs
scraper.py programs/breakfasters
scraper.py programs/breakfasters/broadcasts?page=1
scraper.py programs/breakfasters/broadcasts?page=2
scraper.py programs/breakfasters/podcasts?page=1
scraper.py programs/breakfasters/segments?page=1
scraper.py programs/maps
scraper.py programs/maps/broadcasts?page=1
scraper.py programs/maps/segments?page=1
scraper.py segments?page=1
scraper.py broadcasts?page=1
scraper.py archives?page=1
scraper.py albumoftheweek?page=1
scraper.py albumoftheweek/naima-bock-giant-palm
"""

import urllib, bs4, time, json, re, sys

from urllib import request


URL_BASE = 'https://www.rrr.org.au'

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'


def get(resource_path):
    return urlopen(Scraper.url_for(resource_path))

def urlopen(url):
    sys.stderr.write(f"[34m# Fetching: [34;1m'{url}'[0m\n")
    return request.urlopen(request.Request(url, headers={'User-Agent': USER_AGENT}))

### Scrapers ##############################################

class UnmatchedResourcePath(BaseException):
    '''
    '''

class Scraper:
    @classmethod
    def call(cls, resource_path):
        scraper = cls.factory(resource_path)
      # sys.stderr.write(f"[32m# Using : [32;1m'{scraper}'[0m\n")
        return scraper.generate()

    @classmethod
    def url_for(cls, resource_path):
        return (cls.factory(resource_path)).url()

    @classmethod
    def factory(cls, resource_path):
        try:
            return next(scraper for scraper in cls.__subclasses__() if scraper.match(resource_path))(resource_path)
        except StopIteration:
            raise UnmatchedResourcePath(f"No match for '{resource_path}'")

    @classmethod
    def match(cls, resource_path):
        if cls.RE.match(resource_path):
            return cls(resource_path)

    def __init__(self, resource_path):
        self.resource_path = resource_path
        m = self.__class__.RE.match(self.resource_path)
        if m:
            self.groupdict = m.groupdict()

    def soup(self):
        return bs4.BeautifulSoup(get(self.resource_path), 'html.parser')

    def url(self):
        return f'{URL_BASE}/{self.url_path()}'

    def url_path(self):
        template = self.__class__.URL_PATH

        if self.groupdict.get('query_params'):
            template += '?{query_params}'

        return template.format_map(self.groupdict)



class Programs(Scraper):
    RE = re.compile(r'^programs$')
    URL_PATH = 'explore/programs'

    def generate(self):
        return {
            'result': [
                {
                    'id':        card.find('a'  , class_='card__anchor').attrs['href'].split('/')[-1],
                    'title':     card.find('h1' , class_='card__title' ).find('a').text,
                    'thumbnail': card.find('img'                       ).attrs.get('data-src'),
                    'textbody':  card.find('p'                         ).text
                }
                for card in self.soup().findAll('div', class_='card clearfix')
            ],
            'menu': True
        }


class Program(Scraper):
    RE = re.compile(r'^programs/(?P<program_id>[^/]+)$')
    URL_PATH = 'explore/programs/{program_id}'

    def generate(self):
        soup = self.soup()
        programtitle = soup.find(class_='page-banner__heading')
        if programtitle:
            title = programtitle.text

        programimage = soup.find(class_='card__background-image').attrs.get('style')
        if programimage:
            programimagesrc = re.search(r"https://[^']+", programimage)
            if programimagesrc:
                thumbnail = programimagesrc[0]
            else:
                thumbnail = ''
        else:
            thumbnail = ''

        textbody = '\n'.join((
            soup.find(class_='page-banner__summary').text,
            soup.find(class_='page-banner__time').text
        ))

        collections = [
            {
                'id':   anchor.text.lower(),
                'title': ' - '.join((title, anchor.text)),
                'thumbnail': thumbnail,
                'textbody':  textbody,
            }
            for anchor in soup.find_all('a', class_='program-nav__anchor')
        ]
        if soup.find('h1', string='Recent highlights'):
            collections.append(
                {
                    'id':    'segments',
                    'title': ' - '.join((title, 'Segments')),
                    'thumbnail': thumbnail,
                    'textbody':  textbody,
                }
            )
        return {
            'result': collections,
            'menu': True
        }


class AudioItemGenerator:
    def generate(self):
        return {
            'result': [
                item for item in [
                    AudioItem.factory(div)
                    for div in self.soup().findAll(class_='card__text')
                ]
            ],
            'menu': False
        }

class ProgramBroadcasts(Scraper, AudioItemGenerator):
    RE = re.compile(r'^programs/(?P<program_id>[^/]+)/broadcasts(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'explore/programs/{program_id}/episodes/page'


class ProgramPodcasts(Scraper, AudioItemGenerator):
    RE = re.compile(r'^programs/(?P<program_id>[^/]+)/podcasts(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'explore/podcasts/{program_id}/episodes'


class ProgramSegments(Scraper, AudioItemGenerator):
    RE = re.compile(r'^programs/(?P<program_id>[^/]+)/segments(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'explore/programs/{program_id}/highlights'


class OnDemandSegments(Scraper, AudioItemGenerator):
    RE = re.compile(r'^segments(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'on-demand/segments'


class OnDemandBroadcasts(Scraper, AudioItemGenerator):
    RE = re.compile(r'^broadcasts(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'on-demand/episodes'


class Archives(Scraper, AudioItemGenerator):
    RE = re.compile(r'^archives(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'on-demand/archives'

class ArchiveItem(Scraper):
    RE = re.compile(r'^archives/(?P<item>.+)?$')
    URL_PATH = 'on-demand/archives/{item}'

    def generate(self):
        item = self.soup().find(class_='adaptive-banner__audio-component')
        return {
            'result': AudioItem.factory(item)
        }


class AlbumOfTheWeek(Scraper):
    RE = re.compile(r'^albumoftheweek/(?P<album_id>[^/]+)$')

    RE_BANDCAMP_ALBUM_ID      = re.compile(r'https://bandcamp.com/EmbeddedPlayer/.*album=(?P<album_id>[^/]+)')
    RE_SOUNDCLOUD_PLAYLIST_ID = re.compile(r'.+soundcloud\.com/playlists/(?P<playlist_id>[^&]+)')

    def generate(self):
        pagesoup = self.soup()

        # Determine bandcamp album ID if present
        iframesrcattr = ''.join([item["src"] for item in pagesoup.findAll('iframe') if "src" in item.attrs])
        iframeisbandcamp = re.match(self.RE_BANDCAMP_ALBUM_ID, iframesrcattr)
        iframeissoundcloud = re.match(self.RE_SOUNDCLOUD_PLAYLIST_ID, iframesrcattr)
        album_url = ''

        if iframeisbandcamp:
            iframesrcgroupdict = iframeisbandcamp.groupdict()
            album_id = iframesrcgroupdict['album_id'] if 'album_id' in iframesrcgroupdict.keys() else ''
            plugin = 'plugin://plugin.audio.kxmxpxtx.bandcamp/'
            album_url = '{}?mode=list_songs&album_id={}&item_type=a'.format(plugin, album_id)

        if iframeissoundcloud:
            iframesrcgroupdict = iframeissoundcloud.groupdict()
            playlist_id = iframesrcgroupdict['playlist_id'] if 'playlist_id' in iframesrcgroupdict.keys() else ''
            plugin = 'plugin://plugin.audio.soundcloud/'
            album_url = '{}play/?playlist_id={}'.format(plugin, playlist_id)

        album_copy   = '\n'.join([p.text for p in pagesoup.find(class_='feature-album__copy').findAll("p", recursive=False)])
        album_cover  = ''.join([item["src"] for item in pagesoup.findAll(class_='audio-summary__album-artwork') if "src" in item.attrs])
        album_info   = pagesoup.find(class_='album-banner__copy')
        album_title  = album_info.find(class_='album-banner__heading', recursive=False).text
        album_artist = album_info.find(class_='album-banner__artist',  recursive=False).text

        return {
            'result': [
                {
                    'id': self.resource_path.split('/')[-1],
                    'title': ' - '.join((album_artist, album_title)),
                    'artist': album_artist,
                    'textbody': album_copy,
                    'thumbnail': album_cover,
                    'url': album_url
                }
            ],
            'external': True
        }

    def url_path(self):
        return 'explore/album-of-the-week/{album_id}'.format_map(self.groupdict)


class AlbumOfTheWeeks(Scraper):
    RE = re.compile(r'^albumoftheweek(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'explore/album-of-the-week'

    def generate(self):
        return {
            'result': [
                {
                    'id':        card.find('a'  , class_='card__anchor').attrs['href'].split('/')[-1],
                    'title':     card.find('h1' , class_='card__title' ).find('a').text,
                    'subtitle':  card.find(       class_='card__meta'  ).text,
                    'thumbnail': card.find('img'                       ).attrs.get('data-src'),
                    'textbody':  card.find('p'                         ).text
                }
                for card in self.soup().findAll('div', class_='card clearfix')
            ],
            'menu': True,
            'pagination': True
        }


class ProgramBroadcastItem(Scraper):
    RE = re.compile(r'^programs/(?P<program_id>[^/]+)/broadcasts/(?P<item>.+)?$')
    URL_PATH = 'explore/programs/{program_id}/episodes/{item}'

    def generate(self):
        return {'result': []}


class ProgramPodcastItem(Scraper):
    RE = re.compile(r'^programs/(?P<program_id>[^/]+)/podcasts/(?P<item>.+)?$')
    URL_PATH = 'explore/podcasts/{program_id}/episodes/{item}'

    def generate(self):
        return {'result': []}


class ProgramSegmentItem(Scraper):
    RE = re.compile(r'^programs/(?P<program_id>[^/]+)/segments/(?P<item>.+)?$')
    URL_PATH = 'on-demand/segments/{item}'

    def generate(self):
        return {'result': []}


class Schedule(Scraper):
    RE = re.compile(r'^schedule(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'explore/schedule'

    def generate(self):
        return {
            'result': [
                ScheduleItem(item).to_dict()
                for item in self.soup().findAll(class_='list-view__item')
            ],
            'menu': True
        }


class Soundscapes(Scraper):
    RE = re.compile(r'^soundscapes(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'explore/soundscape'

    def generate(self):
        return {
            'result': [
                {
                    'id':        item.find('a').attrs.get('href').split('/')[-1],
                    'title':     item.find('span').text,
                    'subtitle':  item.find('span').text.split(' - ')[-1],
                    'textbody':  item.find('p').text,
                    'thumbnail': item.find('img').attrs.get('data-src'),
                }
                for item in self.soup().findAll(class_='list-view__item')
            ],
            'menu': True,
            'pagination': True
        }


class Soundscape(Scraper):
    RE = re.compile(r'^soundscapes/(?P<item>.+)?$')
    URL_PATH = 'explore/soundscape/{item}'

    def generate(self):
        return {'result': []}


class TracksItem(Scraper):
    RE = re.compile(r'^tracks/(?P<item>.+)$')
    URL_PATH = 'tracks/{item}'

    def generate(self):
        return {'result': []}


class Events(Scraper):
    RE = re.compile(r'^events(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'events'

    def generate(self):
        return {
            'result': [
                Event(item).to_dict()
                for item in self.soup().findAll('div', class_='card')
            ],
            'menu': True,
            'pagination': True
        }


class EventItem(Scraper):
    RE = re.compile(r'^events/(?P<item>.+)$')
    URL_PATH = 'events/{item}'

    def generate(self):
        item = self.soup().find(class_='event')
        venue = item.find(class_='event__venue-address-details')
        eventdetails = item.find(class_='event__details-copy').get_text(' ').strip()
        textbody = item.find(class_='copy').get_text('\n')
        return {
            'result': [
                {
                    'id':       '',
                    'title':    item.find(class_='event__title').text,
                    'venue':    venue.get_text(' ') if venue else '',
                    'textbody': '\n'.join((eventdetails, textbody)),
                }
            ],
            'menu': True
        }


class Video(Scraper):
    RE = re.compile(r'^videos/(?P<item>.+)$')
    URL_PATH = 'explore/videos/{item}'

    def generate(self):
        return {'result': []}


class Videos(Scraper):
    RE = re.compile(r'^videos(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'explore/videos'

    def generate(self):
        return {'result': []}



### Scrapers ##############################################


class Event:
    def __init__(self, itemobj):
        self._itemobj = itemobj

    @property
    def id(self):
        return self._itemobj.find('a', class_='card__anchor').attrs['href'].split('/')[-1]

    @property
    def _itemtitle(self):
        return self._itemobj.find(class_='card__title').find('a').text

    @property
    def title(self):
        return ' - '.join((self._itemtitle, self._itemdate, self.label))

    @property
    def label(self):
        return self._itemobj.find(class_='card__label').text

    @property
    def _itemtype(self):
        return self._itemobj.find(class_='card__meta').find('div').text

    @property
    def event_type(self):
        return re.sub(' ', '-', self._itemtype).lower()

    @property
    def thumbnail(self):
        img = self._itemobj.find('a', class_='card__anchor').find('img')
        if img:
            return img.attrs['data-src']

    @property
    def _itemdate(self):
        meta = self._itemobj.find('span', class_='card__meta')
        metadiv = meta.findAll('div')
        if len(metadiv) > 0:
            return metadiv[0].text
        else:
            return meta.text if meta else ''

    @property
    def _itemtime(self):
        itemdate = self._itemdate
        currentyear = time.strftime('%Y', time.localtime())
        if not re.match(r'\d', itemdate.split(' ')[-1][0]):
            itemdate = ' '.join((itemdate, currentyear))

        try:
            return time.strptime(itemdate, '%A, %d %B %Y')
        except:
            try:
                itemdate = itemdate.split(' – ')[-1]
                return time.strptime(itemdate, '%d %B %Y')
            except ValueError as e:
                raise e
                return None

    @property
    def date(self):
        if self._itemtime:
            return time.strftime('%d.%m.%Y', self._itemtime)
        else:
            return None

    @property
    def venue(self):
        meta = self._itemobj.find('span', class_='card__meta')
        metadiv = meta.findAll('div')
        if len(metadiv) > 1:
            return metadiv[1].text
        else:
            return ''

    @property
    def textbody(self):
        venue = self.venue
        return '\n'.join((self._itemtitle, 'Date: ' + self._itemdate, 'Venue:' if venue else '', self.venue, '', self._itemtype))

    def to_dict(self):
        result = {
            'id':         self.id,
            'title':      self.title,
            'event_type': self.event_type,
            'thumbnail':  self.thumbnail,
            'venue':      self.venue,
            'date':       self.date,
            'textbody':   self.textbody,
        }

        return result


class ScheduleItem:
    def __init__(self, itemobj):
        self._itemobj = itemobj
        self._audio_item = AudioItem.factory(itemobj)

    @property
    def href(self):
        return self._itemobj.find('a').attrs['href']

    @property
    def start(self):
        return self._itemobj.attrs['data-timeslot-start']

    @property
    def end(self):
        return self._itemobj.attrs['data-timeslot-end']

    @property
    def textbody(self):
        return self._itemobj.find('p').text

    @property
    def content(self):
        content = json.loads(self._itemobj.find(class_='hide-from-all').attrs['data-content'])
        content['title'] = content['name'] if 'name' in content.keys() else ''
        return content

    @property
    def audio_item(self):
        return self._audio_item or {}


    def to_dict(self):
        return {
                      **self.content,
                      **self.audio_item,
            'href':     self.href,
            'start':    self.start,
            'end':      self.end,
            'textbody': self.textbody,
        }


class AudioItem:

    @classmethod
    def factory(cls, item):
        cardbody = item.find(class_='card__body')
        if cardbody:
            textbody = cardbody.text
        else:
            cardbody = item.find(class_='card__meta')
            if cardbody:
                textbody = cardbody.text
            else:
                textbody = ''

        view_playable_div = item.find(lambda tag:tag.name == 'div' and 'data-view-playable' in tag.attrs)
        if view_playable_div:
            view_playable = view_playable_div.attrs['data-view-playable']
            itemobj = json.loads(view_playable)['items'][0]

            if   itemobj['type'] == 'clip':
                item = Segment(itemobj, textbody)
            elif itemobj['type'] == 'broadcast_episode':
                item = Broadcast(itemobj, textbody)
            elif itemobj['type'] == 'audio_archive_item':
                item = Archive(itemobj, textbody)
            else:
                item = AudioItem(itemobj, textbody)
            return item.to_dict()
        else:
            # Should we _also_ have a NonPlayable AudioItem ?
            return None


    def __init__(self, itemobj, textbody):
        self._itemobj = itemobj
        self._itemdata = itemobj['data']
        self.textbody = textbody

    @property
    def id(self):
        return self._itemobj['source_id']

    @property
    def title(self):
        return self._itemdata['title']

    @property
    def subtitle(self):
        return self._itemdata['subtitle']

    @property
    def _itemtime(self):
        return time.strptime(self._itemdata['subtitle'], '%d %B %Y')

    @property
    def _itemtimestr(self):
        return time.strftime('%Y-%m-%d', self._itemtime)

    @property
    def date(self):
        return time.strftime('%d.%m.%Y', self._itemtime)

    @property
    def year(self):
        return int(self._itemtimestr[0:4])

    @property
    def aired(self):
        return self._itemtimestr

    @property
    def duration(self):
        duration = self._itemobj.get('data', {}).get('duration', {})
        if not duration:
            audio_file = self._itemdata.get('audio_file')
            if audio_file:
                duration = audio_file['duration']
            else:
                duration = 0
        return round(duration)

    @property
    def thumbnail(self):
        return self._itemdata['image']['path'] if 'image' in self._itemdata.keys() else ''

    @property
    def url(self):
        audio_file = self._itemdata.get('audio_file')
        if audio_file:
            return audio_file['path']
        else:
            ts = self._itemdata['timestamp']
            l = self.duration
            return 'https://ondemand.rrr.org.au/getclip?bw=h&l={}&m=r&p=1&s={}'.format(l, ts)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'subtitle': self.subtitle,
            'textbody': self.textbody,
            'date': self.date,
            'year': self.year,
            'aired': self.aired,
            'duration': self.duration,
            'url': self.url,
            'thumbnail': self.thumbnail
        }


class Archive(AudioItem):
    ''

class Broadcast(AudioItem):
    ''

class Segment(AudioItem):
    ''


if __name__ == "__main__":
    print(json.dumps(Scraper.call(sys.argv[1])['result']))
