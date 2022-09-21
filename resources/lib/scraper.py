#!/usr/bin/env python
import bs4, time, json, re, os, sys, datetime
# from marshmallow_jsonapi import Schema, fields


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


class Resource:
    def __init__(self, itemobj):
        self._itemobj = itemobj

    def id(self):
        return self.path.split('/')[-1]

    @property
    def path(self):
        return Scraper.resource_path_for(self._itemobj.find('a').attrs['href'])

    RE_CAMEL = re.compile(r'(?<!^)(?=[A-Z])')
    @property
    def type(self):
        return self.RE_CAMEL.sub('_', self.__class__.__name__).lower()

    @property
    def links(self):
        return {
            'self': self.path
        }

    def attributes(self):
        return {}

    def links(self):
        return {
            'self': self.path
        }

    def relationships(self):
        return None

    def included(self):
        return None

    def to_dict(self):
        d = {
            'id':         self.id(),
            'type':       self.type,
            'attributes': {
                'title': self.title,
                **self.attributes(),
            },
            'links'     : self.links(),
        }

        r = self.relationships()
        if r:
            d = {
                **d,
                'relationships': r,
            }

        i = self.included()
        if i:
            d = {
                **d,
                'included': i,
            }
        return d



### Scrapers ##############################################

class UnmatchedResourcePath(BaseException):
    '''
    '''

class Scraper:
    @classmethod
    def call(cls, resource_path):
        scraper = cls.find_by_resource_path(resource_path)
      # sys.stderr.write(f"[32m# Using : [32;1m'{scraper}'[0m\n")
        return scraper.generate()

    @classmethod
    def url_for(cls, resource_path):
        return (cls.find_by_resource_path(resource_path)).url()

    @classmethod
    def resource_path_for(cls, website_path):
        scraper = cls.find_by_website_path(website_path)
        m = scraper.match_website_path(website_path)
        if m:
            return scraper.RESOURCE_PATH_PATTERN.format_map(m.groupdict())


    @classmethod
    def find_by_resource_path(cls, resource_path):
        try:
            return next(scraper for scraper in cls.__subclasses__() if scraper.matching_resource_path(resource_path))(resource_path)
        except StopIteration:
            raise UnmatchedResourcePath(f"No match for '{resource_path}'")

    @classmethod
    def find_by_website_path(cls, website_path):
        return next(scraper for scraper in cls.__subclasses__() if scraper.match_website_path(website_path))

    @classmethod
    def regex_from(cls, pattern):
        return re.compile(
          '^' +
          re.sub('{([A-z]+)}', '(?P<\\1>[^/]+?)', pattern) +
          '(?:[?](?P<query_params>.+))?' +
          '$'
        )

    @classmethod
    def resource_path_regex(cls):
        return cls.regex_from(cls.RESOURCE_PATH_PATTERN)

    @classmethod
    def match_resource_path(cls, path):
        return cls.regex_from(cls.RESOURCE_PATH_PATTERN).match(path)

    @classmethod
    def match_website_path(cls, path):
        return cls.regex_from(cls.WEBSITE_PATH_PATTERN).match(path)

    @classmethod
    def matching_resource_path(cls, resource_path):
        if cls.match_resource_path(resource_path):
            return cls(resource_path)


    def __init__(self, resource_path):
        self.resource_path = resource_path
        m = self.__class__.resource_path_regex().match(self.resource_path)
        if m:
            self.groupdict = m.groupdict()

    def soup(self):
        return bs4.BeautifulSoup(get(self.resource_path), 'html.parser')

    def url(self):
        return f'{URL_BASE}{self.website_path()}'

    def website_path(self):
        template = self.__class__.WEBSITE_PATH_PATTERN

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
    RESOURCE_PATH_PATTERN = '/programs'
    WEBSITE_PATH_PATTERN = '/explore/programs'

    def generate(self):
        return {
            'data': [
                {
                    'resource_path': Scraper.resource_path_for(card.find('a'  , class_='card__anchor').attrs['href']),
                    'type':          'program',
                    'title':         card.find('h1' , class_='card__title' ).find('a').text,
                    'thumbnail':     card.find('img'                       ).attrs.get('data-src'),
                    'textbody':      card.find('p'                         ).text
                }
                for card in self.soup().findAll('div', class_='card clearfix')
            ],
        }


class Program(Scraper):
    RESOURCE_PATH_PATTERN = '/programs/{program_id}'
    WEBSITE_PATH_PATTERN = '/explore/programs/{program_id}'

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

        # Aarrgh the website dragons strike again!
        def map_path(path):
            m = re.match('^/explore/(?P<collection>[^/]+?)/(?P<program>[^/]+?)#episode-selector', path)
            if m:
                d = m.groupdict()
                if   d['collection'] == 'programs':
                    return f"/explore/{d['collection']}/{d['program']}/episodes/page"
                elif d['collection'] == 'podcasts':
                    return f"/explore/{d['collection']}/{d['program']}/episodes"

        collections = [
            {
                'resource_path': Scraper.resource_path_for(map_path(anchor.attrs['href'])),
                'type': 'collection',
                'title': ' - '.join((title, anchor.text)),
                'thumbnail': thumbnail,
                'textbody':  textbody,
            }
            for anchor in soup.find_all('a', class_='program-nav__anchor')
        ]
        highlights = soup.find('a', string=re.compile('highlights'))
        if highlights:
            collections.append(
                {
                    'resource_path': Scraper.resource_path_for(highlights.attrs['href']),
                    'type': 'collection',
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
    RESOURCE_PATH_PATTERN = '/programs/{program_id}/broadcasts'
    WEBSITE_PATH_PATTERN = '/explore/programs/{program_id}/episodes/page'


class ProgramPodcasts(Scraper, AudioItemGenerator):
    RESOURCE_PATH_PATTERN = '/programs/{program_id}/podcasts'
    WEBSITE_PATH_PATTERN = '/explore/podcasts/{program_id}/episodes'


class ProgramSegments(Scraper, AudioItemGenerator):
    RESOURCE_PATH_PATTERN = '/programs/{program_id}/segments'
    WEBSITE_PATH_PATTERN = '/explore/programs/{program_id}/highlights'


class OnDemandSegments(Scraper, AudioItemGenerator):
    RESOURCE_PATH_PATTERN = '/segments'
    WEBSITE_PATH_PATTERN = '/on-demand/segments'


class OnDemandBroadcasts(Scraper, AudioItemGenerator):
    RESOURCE_PATH_PATTERN = '/broadcasts'
    WEBSITE_PATH_PATTERN = '/on-demand/episodes'


class Archives(Scraper, AudioItemGenerator):
    RESOURCE_PATH_PATTERN = '/archives'
    WEBSITE_PATH_PATTERN = '/on-demand/archives'


class ArchiveItem(Scraper):
    RESOURCE_PATH_PATTERN = '/archives/{item}'
    WEBSITE_PATH_PATTERN = '/on-demand/archives/{item}'

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
    RESOURCE_PATH_PATTERN = '/featured_albums/{album_id}'
    WEBSITE_PATH_PATTERN = '/explore/album-of-the-week/{album_id}'

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
                'resource_path': self.resource_path,
                'type':        'featured_album',
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
    RESOURCE_PATH_PATTERN = '/featured_albums'
    WEBSITE_PATH_PATTERN = '/explore/album-of-the-week'

    def generate(self):
        return {
            'data': [
                {
                    'resource_path': Scraper.resource_path_for(card.find('a'  , class_='card__anchor').attrs['href']),
                    'type':          'featured_album',
                    'title':         card.find('h1' , class_='card__title' ).find('a').text,
                    'subtitle':      card.find(       class_='card__meta'  ).text,
                    'thumbnail':     card.find('img'                       ).attrs.get('data-src'),
                    'textbody':      card.find('p'                         ).text
                }
                for card in self.soup().findAll('div', class_='card clearfix')
            ],
            'links': self.pagination()
        }


class NewsItems(Scraper):
    RESOURCE_PATH_PATTERN = '/news_items'
    WEBSITE_PATH_PATTERN = '/explore/news-articles'

    def generate(self):
        return {
            'data': [
                News(item).to_dict()
                for item in self.soup().findAll(class_='list-view__item')
            ],
            'links': self.pagination(),
        }


class NewsItem(Scraper):
    RESOURCE_PATH_PATTERN = '/news_items/{item}'
    WEBSITE_PATH_PATTERN = '/explore/news-articles/{item}'


class ProgramBroadcastItem(Scraper):
    RESOURCE_PATH_PATTERN = '/programs/{program_id}/broadcasts/{item}'
    WEBSITE_PATH_PATTERN = '/explore/programs/{program_id}/episodes/{item}'

    def generate(self):
        return {'data': []}


class ProgramPodcastItem(Scraper):
    RESOURCE_PATH_PATTERN = '/programs/{program_id}/podcasts/{item}'
    WEBSITE_PATH_PATTERN = '/explore/podcasts/{program_id}/episodes/{item}'

    def generate(self):
        return {'data': []}


class ProgramSegmentItem(Scraper):
    RESOURCE_PATH_PATTERN = '/segments/{item}'
    WEBSITE_PATH_PATTERN = '/on-demand/segments/{item}'

    def generate(self):
        return {'data': []}


class Schedule(Scraper):
    RESOURCE_PATH_PATTERN = '/schedule'
    WEBSITE_PATH_PATTERN = '/explore/schedule'

    def generate(self):
        soup = self.soup()
        date = soup.find(class_='calendar__hidden-input').attrs.get('value')
        prevdate, nextdate = [x.find('a').attrs.get('href').split('=')[-1] for x in soup.findAll(class_='page-nav__item')]
        return {
            'data': [
                ScheduleItem(item).to_dict()
                for item in self.soup().findAll(class_='list-view__item')
            ],
            'links': self.pagination(pagekey='date', selfval=date, nextval=prevdate),
        }


class Search(Scraper):
    RESOURCE_PATH_PATTERN = '/search'
    WEBSITE_PATH_PATTERN = '/search'

    def generate(self):
        return {
            'data': [
                SearchItem(item).to_dict()
                for item in self.soup().findAll(class_='search-result')
            ],
            'links': self.pagination(),
        }


class Soundscapes(Scraper):
    RESOURCE_PATH_PATTERN = '/soundscapes'
    WEBSITE_PATH_PATTERN = '/explore/soundscape'

    def generate(self):
        return {
            'data': [
                {
                    'resource_path': Scraper.resource_path_for(item.find('a').attrs.get('href')),
                    'type':          'soundscape',
                    'title':         item.find('span').text,
                    'subtitle':      item.find('span').text.split(' - ')[-1],
                    'textbody':      item.find('p').text,
                    'thumbnail':     item.find('img').attrs.get('data-src'),
                }
                for item in self.soup().findAll(class_='list-view__item')
            ],
            'links': self.pagination()
        }


class Soundscape(Scraper, ExternalMedia):
    RESOURCE_PATH_PATTERN = '/soundscapes/{item}'
    WEBSITE_PATH_PATTERN = '/explore/soundscape/{item}'

    def generate(self):
        pagesoup = self.soup()

        iframes = []
        section = pagesoup.find('section', class_='copy')
        for heading in section.findAll(['h2', 'p'], recursive=False):
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


class Topic(Resource):
    @property
    def title(self):
        return self._itemobj.find('a').text

    def attributes(self):
        return {
            'title': self.title
        }


class Topics(Scraper):
    RESOURCE_PATH_PATTERN = '/topics'
    WEBSITE_PATH_PATTERN = '/'

    def generate(self):
        return {
            'data': [
                Topic(item).to_dict()
                for item in self.soup().findAll(class_='topic-list__item')
            ],
            'links': {
                'self': self.__class__.RESOURCE_PATH_PATTERN
            },
        }


class TopicsItem(Scraper):
    RESOURCE_PATH_PATTERN = '/topics/{topic}'
    WEBSITE_PATH_PATTERN = '/topics/{topic}'

    def generate(self):
        return {
            'data': [
                SearchItem(item).to_dict()
                for item in self.soup().findAll(class_='search-result')
            ],
            'links': self.pagination(),
        }


class TracksSearch(Scraper):
    RESOURCE_PATH_PATTERN = '/tracks/search'
    WEBSITE_PATH_PATTERN = '/tracks/search'

    def generate(self):
        return {
            'data': [
                BroadcastTrack(item).to_dict()
                for item in self.soup().findAll(class_='search-result')
            ],
        }


class TracksItem(Scraper):
    RESOURCE_PATH_PATTERN = '/tracks/{track_id}'
    WEBSITE_PATH_PATTERN = '/tracks/{track_id}'

    def generate(self):
        return {'data': []}


class Track(Resource):
    def __init__(self, path, artist, title):
        self._path = path
        self.artist = artist
        self.title = title

    @property
    def path(self):
        return self._path

    def id(self):
        return self.path.split('/')[-1]

    def attributes(self):
        return {
            'title':  self.title,
            'artist': self.artist,
        }


class Events(Scraper):
    RESOURCE_PATH_PATTERN = '/events'
    WEBSITE_PATH_PATTERN = '/events'

    def generate(self):
        return {
            'data': [
                Event(item).to_dict()
                for item in self.soup().findAll('div', class_='card')
            ],
            'links': self.pagination()
        }


class EventItem(Scraper):
    RESOURCE_PATH_PATTERN = '/events/{item}'
    WEBSITE_PATH_PATTERN = '/events/{item}'

    def generate(self):
        item = self.soup().find(class_='event')
        venue = item.find(class_='event__venue-address-details')
        eventdetails = item.find(class_='event__details-copy').get_text(' ').strip()
        textbody = item.find(class_='copy').get_text('\n')

        flag_label = item.find(class_='flag-label')
        if flag_label:
            event_type = re.sub(' ', '-', flag_label.text).lower()
        else:
            event_type = None

        return {
            'data': [
                {
                    'resource_path':  self.resource_path,
                    'type':           event_type,
                    'title':          item.find(class_='event__title').text,
                    'venue':          venue.get_text(' ') if venue else '',
                    'textbody':       '\n'.join((eventdetails, textbody)),
                }
            ],
        }


class Giveaways(Scraper):
    RESOURCE_PATH_PATTERN = '/giveaways'
    WEBSITE_PATH_PATTERN = '/subscriber-giveaways'

    def generate(self):
        return {
            'data': [
                {
                    'resource_path': Scraper.resource_path_for(item.find('a').attrs.get('href')),
                    'type':          'giveaway',
                    'title':         item.find('span').text,
                    'textbody':      item.find('p').text,
                    'thumbnail':     item.find('img').attrs.get('data-src'),
                }
                for item in self.soup().findAll(class_='list-view__item')
            ],
        }


class Giveaway(Scraper):
    RESOURCE_PATH_PATTERN = '/giveaways/{giveaway}'
    WEBSITE_PATH_PATTERN = '/subscriber-giveaways/{giveaway}'

    def generate(self):
        item = self.soup().find(class_='subscriber_giveaway')
        banner = self.soup().find(class_='compact-banner')
        closes = banner.find(class_='compact-banner__date').text
        textbody = item.find(class_='subscriber-giveaway__copy').get_text(' ')

        return {
            'data': [
                {
                    'resource_path':  '/'.join((self.resource_path, 'entries')),
                    'type':           'giveaway',
                    'title':          banner.find(class_='compact-banner__heading').text,
                    'textbody':       f'{closes}\n\n{textbody}',
                    'thumbnail':      item.find(class_='summary-inset__artwork').attrs.get('src'),
                }
            ],
        }


class Video(Scraper):
    RESOURCE_PATH_PATTERN = '/videos/{item}'
    WEBSITE_PATH_PATTERN = '/explore/videos/{item}'

    def generate(self):
        return {'data': []}


class Videos(Scraper):
    RESOURCE_PATH_PATTERN = '/videos'
    WEBSITE_PATH_PATTERN = '/explore/videos'

    def generate(self):
        return {'data': []}



### Scrapers ##############################################

class News:
    def __init__(self, itemobj):
        self._itemobj = itemobj

    @property
    def resource_path(self):
        return Scraper.resource_path_for(self._itemobj.find(class_='list-view__anchor').attrs['href'])

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
    def resource_path(self):
        return Scraper.resource_path_for(self._itemobj.find('a', class_='card__anchor').attrs['href'])

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
            'resource_path': self.resource_path,
            'title':         self.title,
            'type':          self.event_type,
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
    def resource_path(self):
        return Scraper.resource_path_for(self._itemobj.find('a').attrs['href'])

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
        content['type'] = 'program' if content['type'] == 'programs' else None  # Eeek
        return content

    @property
    def audio_item(self):
        return self._audio_item or {}


    def to_dict(self):
        return {
                           **self.content,
                           **self.audio_item,
            'resource_path': self.resource_path,
            'start':         self.start,
            'end':           self.end,
            'textbody':      self.textbody,
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


class SearchItem(Resource):
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

    def attributes(self):
        return {
            **Resource.attributes(self),
            'textbody': self.textbody,
        }


class BroadcastTrack(Resource):
    def id(self):
        return f'{SearchItem.id(self)}.{self.track.id()}'

    @property
    def title(self):
        return self.track.title

    RE = re.compile(r'Played (?P<played_date>[^/]+) by (?P<played_by>.+)View all plays$')
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
    def broadcast(self):
        return Broadcast(Resource)

    @property
    def track(self):
        return Track(
            Scraper.resource_path_for(self._itemobj.find(class_='search-result__meta-links').find('a').attrs['href']),
            self._itemobj.find(class_='search-result__track-artist').text,
            self._itemobj.find(class_='search-result__track-title').text,
        )

    def attributes(self):
        return {
            'played_date':  self.played_date,
            'played_by':    self.played_by,
        }

    def relationships(self):
        return {
            'broadcast': {
                'links': {
                    'related': self.path
                },
                'data': {
                    'type': 'broadcast',
                    'id':  Resource.id(self),
                },
            },
            'track': {
                'links': {
                    'related': self.track.path,
                },
                'data': {
                    'type': self.track.type,
                    'id':   self.track.id(),
                },
            },
        }

    def included(self):
        return [
            self.broadcast.to_dict(),
            self.track.to_dict(),
        ]


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
                obj = Segment(item, itemobj, textbody)
            elif itemobj['type'] == 'broadcast_episode':
                obj = Broadcast(item, itemobj, textbody)
            elif itemobj['type'] == 'audio_archive_item':
                obj = Archive(item, itemobj, textbody)
            elif itemobj['type'] == 'podcast_episode':
                obj = Podcast(item, itemobj, textbody)
            else:
                obj = AudioItem(item, itemobj, textbody)
            return obj.to_dict()
        else:
            # Should we _also_ have a NonPlayable AudioItem ?
            return None


    def __init__(self, item, itemobj, textbody):
        self._item = item
        self._itemobj = itemobj
        self._itemdata = itemobj['data']
        self.textbody = textbody

    @property
    def resource_path(self):
        card_anchor = self._item.find(class_='card__anchor')
        if card_anchor:
            return Scraper.resource_path_for(card_anchor.attrs['href'])

    @property
    def type(self):
        return self.__class__.__name__.lower()

    @property
    def source_id(self):
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
            'source_id':     self.source_id,
            'resource_path': self.resource_path,
            'type':          self.type,
            'title':         self.title,
            'subtitle':      self.subtitle,
            'textbody':      self.textbody,
            'date':          self.date,
            'year':          self.year,
            'aired':         self.aired,
            'duration':      self.duration,
            'url':           self.url,
            'thumbnail':     self.thumbnail
        }


class Archive(AudioItem):
    ''

class Broadcast(AudioItem):
    ''

class Segment(AudioItem):
    ''

class Podcast(AudioItem):
    ''


if __name__ == "__main__":
    stderr = True
    print(json.dumps(Scraper.call(sys.argv[1])))
