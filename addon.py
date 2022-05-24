import os
from xbmcaddon import Addon
from xbmcswift2 import Plugin, ListItem, xbmcgui
import resources.lib.tripler as tripler

plugin = Plugin()
respath = os.path.join(Addon().getAddonInfo('path'), 'resources')
icon = os.path.join(respath, 'icon.png')
fanart = os.path.join(respath, 'fanart.png')

@plugin.route('/')
def main_menu():
    items = [
        {
            'label': plugin.get_string(30000), 
            'path': "https://ondemand.rrr.org.au/stream/ws-hq.m3u", 
            'thumbnail': icon, 
            'properties': {
                'StationName': 'Triple RRR',
                'fanart_image': fanart
            },
            'info': {
                'mediatype': 'music'
            },
            'is_playable': True
        },
        {'label': plugin.get_string(30001), 'path': plugin.url_for(segment_menu, page=1)},
        {'label': plugin.get_string(30002), 'path': plugin.url_for(program_menu, page=1)},
        {'label': plugin.get_string(30003), 'path': plugin.url_for(audio_archives, page=1)},
    ]
    listitems = [ListItem.from_dict(**item) for item in items]

    return listitems

def parse_programs(programs, page):
    items = []

    for program in programs:
        item = {
            'label': program['title'],
            'label2': 'aired {}'.format(program['aired']),
            'info_type': 'video',
            'info': {
                'count': program['id'],
                'title': program['title'],
                'plot': program['desc'],
                'date': program['date'],
                'year': program['year'],
                'premiered': program['aired'],
                'aired': program['aired'],
                'duration': program['duration'],
                'mediatype': 'song'
            },
            'properties': {
                'StationName': 'Triple RRR',
                'fanart_image': fanart
            },
            'path': program['url'],
            'thumbnail': program['art'],
            'is_playable': True
        }
        listitem = ListItem.from_dict(**item)
        items.append(listitem)

    return items

@plugin.route('/segment_menu/<page>')
def segment_menu(page):
    programs = tripler.get_programs("segments", page)
    items = parse_programs(programs, page)
    if len(items) > 0:
        items.append({'label': "> Next Page", 'path': plugin.url_for(segment_menu, page=int(page) + 1)})
    return items

@plugin.route('/program_menu/<page>')
def program_menu(page):
    programs = tripler.get_programs("episodes", page)
    items = parse_programs(programs, page)
    if len(items) > 0:
        items.append({'label': "> Next Page", 'path': plugin.url_for(program_menu, page=int(page) + 1)})
    return items

@plugin.route('/audio_archives/<page>')
def audio_archives(page):
    programs = tripler.get_programs("archives", page)
    items = parse_programs(programs, page)
    if len(items) > 0:
        items.append({'label': "> Next Page", 'path': plugin.url_for(audio_archives, page=int(page) + 1)})
    return items

if __name__ == '__main__':
    plugin.run()
