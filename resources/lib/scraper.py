#!/usr/bin/env python
import bs4, time, json, re, sys, datetime

IS_PY3 = sys.version_info[0] > 2
if IS_PY3:
    from urllib.request import Request, urlopen
    from urllib.parse import parse_qs, urlencode
else:
    from urllib2 import Request, urlopen
    from urllib2 import urlencode
    from urlparse import parse_qs


DATE_FORMAT = '%Y-%m-%d'

URL_BASE = 'https://www.rrr.org.au'

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'

stderr = False


def get(resource_path):
    return urlopen_ua(Scraper.url_for(resource_path))

def urlopen_ua(url):
    if stderr:
        sys.stderr.write(f"[34m# Fetching: [34;1m'{url}'[0m\n")
    return urlopen(Request(url, headers={'User-Agent': USER_AGENT}))

def get_json(url):
    return urlopen_ua(url).read().decode()

def get_json_obj(url):
    return json.loads(get_json(url))


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

    def pagination(self, pagekey='page', selfval=1, nextval=None, lastval=None):
        resource_path = self.resource_path.split('?')
        if len(resource_path) > 1:
            resource_params = parse_qs(resource_path[-1])
            if not resource_params.get(pagekey):
                resource_params[pagekey] = selfval
            else:
                resource_params[pagekey] = resource_params[pagekey][0]
        else:
            resource_params = {pagekey: selfval}

        template = resource_path[0] + '?{}'
        links = {}

        links['self'] = template.format(urlencode(resource_params))

        if nextval:
            resource_params[pagekey] = nextval
        else:
            resource_params[pagekey] = int(resource_params[pagekey]) + 1
        links['next'] = template.format(urlencode(resource_params))

        links_last = None
        if lastval:
            resource_params[pagekey] = lastval
            links['last'] = template.format(urlencode(resource_params))

        return links



class Programs(Scraper):
    RE = re.compile(r'^programs$')
    URL_PATH = 'explore/programs'

    def generate(self):
        return {
            'data': [
                {
                    'id':        card.find('a'  , class_='card__anchor').attrs['href'].split('/')[-1],
                    'title':     card.find('h1' , class_='card__title' ).find('a').text,
                    'thumbnail': card.find('img'                       ).attrs.get('data-src'),
                    'textbody':  card.find('p'                         ).text
                }
                for card in self.soup().findAll('div', class_='card clearfix')
            ],
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
            'data': collections,
        }


class AudioItemGenerator:
    def generate(self):
        return {
            'data': [
                item for item in [
                    AudioItem.factory(div)
                    for div in self.soup().findAll(class_='card__text')
                ]
            ],
            'links': self.pagination()
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
            'data': AudioItem.factory(item)
        }


class ExternalMedia:
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

    RE_MEDIA_URLS = {
        'Bandcamp':         {
            're':     RE_BANDCAMP_ALBUM_ID,
            'base':   BANDCAMP_PLUGIN_BASE_URL,
            'format': BANDCAMP_PLUGIN_FORMAT,
        },
        'SoundCloud':       {
            're':     RE_SOUNDCLOUD_PLAYLIST_ID,
            'base':   SOUNDCLOUD_PLUGIN_BASE_URL,
            'format': SOUNDCLOUD_PLUGIN_FORMAT,
        },
        'YouTube': {
            're':     RE_YOUTUBE_VIDEO_ID,
            'base':   YOUTUBE_PLUGIN_BASE_URL,
            'format': YOUTUBE_VIDEO_PLUGIN_FORMAT,
        },
        'YouTube Playlist': {
            're':     RE_YOUTUBE_PLAYLIST_ID,
            'base':   YOUTUBE_PLUGIN_BASE_URL,
            'format': YOUTUBE_PLAYLIST_PLUGIN_FORMAT,
        }
    }

    def media_items(self, iframes, fetch_album_art=False):
        pagesoup = self.soup()
        matches = []

        for iframe in iframes:
            if not iframe.get('src'):
                continue
            url, thumbnail = None, None
            for plugin, info in self.RE_MEDIA_URLS.items():
                plugin_match = re.match(info.get('re'), iframe.get('src'))
                if plugin_match:
                    media_id = plugin_match.groupdict().get('media_id')
                    if media_id:
                        url = info.get('format').format(info.get('base'), media_id)
                        if fetch_album_art:
                            if plugin == 'Bandcamp':
                                thumbnail = self.bandcamp_album_art(media_id)
                        break

            matches.append(
                {
                    'url':       url if media_id else '',
                    'src':       iframe.get('src'),
                    'attrs':     iframe.get('attrs'),
                    'plugin':    plugin if plugin_match else None,
                    'thumbnail': thumbnail,
                }
            )

        return matches

    def bandcamp_album_art(self, album_id):
        api_url = self.BANDCAMP_ALBUM_ART_URL.format(album_id)
        art_id = get_json_obj(api_url).get('art_id')
        if art_id:
            return f'https://f4.bcbits.com/img/a{art_id}_2.jpg'

        return None


class FeaturedAlbum(Scraper, ExternalMedia):
    RE = re.compile(r'^featured_albums/(?P<album_id>[^/]+)$')
    URL_PATH = 'explore/album-of-the-week/{album_id}'

    def generate(self):
        pagesoup = self.soup()

        iframes = [
            {
                'src': iframe.attrs.get('src'),
                'attrs': None
            }
            for iframe in pagesoup.findAll('iframe')
            if iframe.attrs.get('src')
        ]
        album_urls   = self.media_items(iframes)

        album_copy   = '\n'.join([p.text for p in pagesoup.find(class_='feature-album__copy').findAll("p", recursive=False)])
        album_image  = pagesoup.find(class_='audio-summary__album-artwork')
        album_info   = pagesoup.find(class_='album-banner__copy')
        album_title  = album_info.find(class_='album-banner__heading', recursive=False).text
        album_artist = album_info.find(class_='album-banner__artist',  recursive=False).text

        data = [
            {
                'id':        '',
                'title':     ' - '.join((album_artist, album_title)),
                'artist':    album_artist,
                'textbody':  album_copy,
            }
        ]

        if album_urls and album_urls[0].get('url'):
            url = album_urls[0].get('url')
            if url:
                data[0]['id']     = self.resource_path.split('/')[-1]
                data[0]['url']    = url
                data[0]['plugin'] = album_urls[0].get('plugin')
        if album_image:
            data[0]['thumbnail']  = album_image.attrs.get('src')

        return {
            'data': data,
        }



class FeaturedAlbums(Scraper):
    RE = re.compile(r'^featured_albums(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'explore/album-of-the-week'

    def generate(self):
        return {
            'data': [
                {
                    'id':        card.find('a'  , class_='card__anchor').attrs['href'].split('/')[-1],
                    'title':     card.find('h1' , class_='card__title' ).find('a').text,
                    'subtitle':  card.find(       class_='card__meta'  ).text,
                    'thumbnail': card.find('img'                       ).attrs.get('data-src'),
                    'textbody':  card.find('p'                         ).text
                }
                for card in self.soup().findAll('div', class_='card clearfix')
            ],
            'links': self.pagination()
        }


class NewsItems(Scraper):
    RE = re.compile(r'^news_items(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'explore/news-articles'

    def generate(self):
        return {
            'data': [
                News(item).to_dict()
                for item in self.soup().findAll(class_='list-view__item')
            ],
            'links': self.pagination(),
        }


class NewsItem(Scraper):
    RE = re.compile(r'^news_items/(?P<item>.+)?$')
    URL_PATH = 'explore/news-articles/{item}'


class ProgramBroadcastItem(Scraper):
    RE = re.compile(r'^programs/(?P<program_id>[^/]+)/broadcasts/(?P<item>.+)?$')
    URL_PATH = 'explore/programs/{program_id}/episodes/{item}'

    def generate(self):
        return {'data': []}


class ProgramPodcastItem(Scraper):
    RE = re.compile(r'^programs/(?P<program_id>[^/]+)/podcasts/(?P<item>.+)?$')
    URL_PATH = 'explore/podcasts/{program_id}/episodes/{item}'

    def generate(self):
        return {'data': []}


class ProgramSegmentItem(Scraper):
    RE = re.compile(r'^programs/(?P<program_id>[^/]+)/segments/(?P<item>.+)?$')
    URL_PATH = 'on-demand/segments/{item}'

    def generate(self):
        return {'data': []}


class Schedule(Scraper):
    RE = re.compile(r'^schedule(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'explore/schedule'

    def generate(self):
        soup = self.soup()
        return {
            'data': [
                ScheduleItem(item).to_dict()
                for item in self.soup().findAll(class_='list-view__item')
            ],
        }


class Search(Scraper):
    RE = re.compile(r'^search(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'search'

    def generate(self):
        return {
            'data': [
                SearchItem(item).to_dict()
                for item in self.soup().findAll(class_='search-result')
            ],
            'links': self.pagination(),
        }


class Soundscapes(Scraper):
    RE = re.compile(r'^soundscapes(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'explore/soundscape'

    def generate(self):
        return {
            'data': [
                {
                    'id':        item.find('a').attrs.get('href').split('/')[-1],
                    'title':     item.find('span').text,
                    'subtitle':  item.find('span').text.split(' - ')[-1],
                    'textbody':  item.find('p').text,
                    'thumbnail': item.find('img').attrs.get('data-src'),
                }
                for item in self.soup().findAll(class_='list-view__item')
            ],
            'links': self.pagination()
        }


class Soundscape(Scraper, ExternalMedia):
    RE = re.compile(r'^soundscapes/(?P<item>.+)?$')
    URL_PATH = 'explore/soundscape/{item}'

    def generate(self):
        pagesoup = self.soup()

        iframes = []
        section = pagesoup.find('section', class_='copy')
        for heading in section.findAll('h2', recursive=False) + section.findAll('p', recursive=False):
            iframe = heading.find_next_sibling()
            while iframe != None and iframe.find('iframe') == None:
                iframe = iframe.find_next_sibling()
            if iframe == None or len(heading.text) < 2:
                break

            aotw = len(heading.text.split('**')) > 1

            attrs = {
                'id':             ' '.join(heading.text.split('**')[0].split(' - ')),
                'title':          heading.text.split('**')[0],
                'artist':         heading.text.split(' - ')[0],
                'featured_album': heading.text.split('**')[1] if aotw else '',
            }
            media = {
                'src': iframe.find('iframe').attrs.get('src'),
                'attrs': attrs,
            }
            if aotw:
                iframes.insert(0, media)
            else:
                iframes.append(media)

        media_items = self.media_items(iframes, fetch_album_art=True)
        soundscape_date = pagesoup.find(class_='news-item__title').text.split(' - ')[-1]

        data = []
        for media in media_items:
            dataitem = {
                'subtitle':   soundscape_date,
                'artist':     media.get('attrs').get('artist'),
                'thumbnail':  media.get('thumbnail'),
            }

            if media.get('plugin'):
                dataitem['title']  = media.get('attrs').get('title')
                dataitem['id']     = re.sub(' ', '-', media.get('attrs').get('id')).lower()
                dataitem['url']    = media.get('url')
                dataitem['plugin'] = media.get('plugin')
            else:
                dataitem['title'] = media.get('attrs').get('title')
                dataitem['id']    = ''

            dataitem['textbody'] = '{}\n{}\n'.format(
                media.get('attrs').get('title'),
                media.get('attrs').get('featured_album')
            )

            data.append(dataitem)

        return {
            'data': data,
        }


class Topics(Scraper):
    RE = re.compile(r'^topics$')
    URL_PATH = ''

    def generate(self):
        return {
            'data': [
                {
                    'resource_path': item.find('a').attrs['href'],
                    'name':          item.find('a').text,
                }
                for item in self.soup().findAll(class_='topic-list__item')
            ]
        }


class TopicsItem(Scraper):
    RE = re.compile(r'^topics/(?P<topic>.+?)(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'topics/{topic}'

    def generate(self):
        return {
            'data': [
                SearchItem(item).to_dict()
                for item in self.soup().findAll(class_='search-result')
            ],
            'links': self.pagination(),
        }


class TracksItem(Scraper):
    RE = re.compile(r'^tracks/(?P<track_id>\d+)$')
    URL_PATH = 'tracks/{track_id}'

    def generate(self):
        return {'data': []}


class TracksSearch(Scraper):
    RE = re.compile(r'^tracks/search[?](?P<query_params>.+)$')
    URL_PATH = 'tracks/search'

    def generate(self):
        return {
            'data': [
                SearchTrackItem(item).to_dict()
                for item in self.soup().findAll(class_='search-result')
            ],
        }


class Events(Scraper):
    RE = re.compile(r'^events(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'events'

    def generate(self):
        return {
            'data': [
                Event(item).to_dict()
                for item in self.soup().findAll('div', class_='card')
            ],
            'links': self.pagination()
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
            'data': [
                {
                    'resource_path':  self.resource_path,
                    'title':          item.find(class_='event__title').text,
                    'venue':          venue.get_text(' ') if venue else '',
                    'textbody':       '\n'.join((eventdetails, textbody)),
                }
            ],
        }


class Video(Scraper):
    RE = re.compile(r'^videos/(?P<item>.+)$')
    URL_PATH = 'explore/videos/{item}'

    def generate(self):
        return {'data': []}


class Videos(Scraper):
    RE = re.compile(r'^videos(?:[?](?P<query_params>.+))?$')
    URL_PATH = 'explore/videos'

    def generate(self):
        return {'data': []}



### Scrapers ##############################################

class News:
    def __init__(self, itemobj):
        self._itemobj = itemobj

    @property
    def resource_path(self):
        return self._itemobj.find(class_='list-view__anchor').attrs['href']

    @property
    def title(self):
        return self._itemobj.find(class_='list-view__title').text

    @property
    def type(self):
        return 'news_item'

    @property
    def textbody(self):
        return self._itemobj.find(class_='list-view__summary').text

    def to_dict(self):
        return {
            'resource_path': self.resource_path,
            'title':         self.title,
            'type':          self.type,
            'textbody':      self.textbody,
        }


class Event:
    def __init__(self, itemobj):
        self._itemobj = itemobj

    @property
    def id(self):
        return self._itemobj.find('a', class_='card__anchor').attrs['href'].split('/')[-1]

    @property
    def resource_path(self):
        return self._itemobj.find('a', class_='card__anchor').attrs['href']

    @property
    def _itemtitle(self):
        return self._itemobj.find(class_='card__title').find('a').text

    @property
    def title(self):
        if self.label:
            return ' - '.join((self._itemtitle, self._itemdate, self.label))
        else:
            return ' - '.join((self._itemtitle, self._itemdate))

    @property
    def label(self):
        label = self._itemobj.find(class_='card__label')
        return label.text if label else ''

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
                return None

    @property
    def date(self):
        if self._itemtime:
            return time.strftime(DATE_FORMAT, self._itemtime)
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
        return {
            'id':            self.id,
            'resource_path': self.resource_path,
            'title':         self.title,
            'event_type':    self.event_type,
            'thumbnail':     self.thumbnail,
            'date':          self.date,
            'venue':         self.venue,
            'textbody':      self.textbody,
        }


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


class ItemType:
    def from_label(val):
        default = "_".join(val.lower().split())
        return {
            'album_of_the_week': 'featured_album',
            'audio_archive':     'archive',
            'broadcast_episode': 'broadcast',
            'news':              'news_item',
            'podcast_episode':   'podcast',
        }.get(default, default)


class SearchItem:
    def __init__(self, itemobj):
        self._itemobj = itemobj

    @property
    def href(self):
        return self._itemobj.find('a').attrs['href']

    @property
    def resource_path(self):
        # TODO: map hrefs back to resource_paths
        return self.href

    @property
    def type(self):
        return ItemType.from_label(self._itemobj.find(class_='flag-label').text)

    @property
    def title(self):
        return self._itemobj.find(class_='search-result__title').text

    @property
    def textbody(self):
        body = self._itemobj.find(class_='search-result__body')
        if body:
            return "\n\n".join([item.text for item in body.children])

    def to_dict(self):
        return {
            'resource_path': self.resource_path,
            'type':          self.type,
            'title':         self.title,
            'textbody':      self.textbody,
        }


class SearchTrackItem(SearchItem):
    RE = re.compile(r'Played (?P<played_date>[^/]+) by (?P<played_by>.+)View all plays$')

    def __init__(self, itemobj):
        self._itemobj = itemobj

    @property
    def title(self):
        return self._itemobj.find(class_='search-result__track-title').text

    @property
    def artist(self):
        return self._itemobj.find(class_='search-result__track-artist').text

    @property
    def played(self):
        return self.RE.match(self._itemobj.find(class_='search-result__meta-info').text)

    @property
    def played_date(self):
        return datetime.datetime.strptime(self.played['played_date'], '%A %d %b %Y').strftime('%Y-%m-%d')

    @property
    def played_by(self):
        return self.played['played_by']

    @property
    def play_link(self):
        return self._itemobj.find(class_='search-result__meta-info').find('a').attrs['href']

    @property
    def resource_path(self):
        return self.play_link

    @property
    def track_link(self):
        return self._itemobj.find(class_='search-result__meta-links').find('a').attrs['href']

    def to_dict(self):
        return {
            'title':         self.title,
            'artist':        self.artist,
            'played_date':   self.played_date,
            'played_by':     self.played_by,
            'resource_path': self.resource_path,
            'track_link':    self.track_link,
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
    def date(self):
        return time.strftime(DATE_FORMAT, self._itemtime)

    @property
    def year(self):
        return self._itemtime[0]

    @property
    def aired(self):
        return self.date

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
    stderr = True
    print(json.dumps(Scraper.call(sys.argv[1])))
