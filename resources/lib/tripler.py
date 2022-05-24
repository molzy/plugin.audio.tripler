from bs4 import BeautifulSoup
import json, time, sys

IS_PY3 = sys.version_info[0] > 2
if IS_PY3:
    from urllib.request import Request, urlopen
else:
    from urllib2 import Request, urlopen

def get_programs(plugin, collection, page):
    output_final = []

    url = "https://www.rrr.org.au/on-demand/{}?page={}".format(collection, page)
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    req = Request(url, headers={'User-Agent': ua})
    html = urlopen(req)
    soup = BeautifulSoup(html, 'html.parser')

    divs = soup.findAll(class_='card__text')

    for item in divs:
        cardbody = item.find(class_='card__body')
        if not cardbody:
            continue
        textbody = ' '.join(cardbody.strings)
        if len(item.contents) < 3:
            continue
        if 'data-view-playable' not in item.contents[-1].attrs:
            continue
        viewplayable = item.contents[-1].attrs['data-view-playable']
        mediaurl = ''
        try:
            itemobj = json.loads(viewplayable)['items'][0]
            itemdata = itemobj['data']
            if itemobj['type'] == 'clip':
                ts = itemdata['timestamp']
                l = int(itemdata['duration'])
                mediaurl = 'https://ondemand.rrr.org.au/getclip?bw=h&l={}&m=r&p=1&s={}'.format(l, ts)
            elif itemobj['type'] == 'broadcast_episode':
                ts = itemdata['timestamp']
                mediaurl = 'https://ondemand.rrr.org.au/getclip?bw=h&l=0&m=r&p=1&s={}'.format(ts)
            else:
                if 'audio_file' not in itemdata.keys():
                    continue
                mediaurl = itemdata['audio_file']['path']

            itemtime = time.strptime(itemdata['subtitle'], '%d %B %Y')
            itemtimestr = time.strftime('%Y-%m-%d', itemtime)
            output_final.append({
                'id': itemobj['source_id'],
                'title': itemdata['title'],
                'desc': '\n'.join((plugin.get_string(30007), '%s')) % (itemdata['subtitle'], textbody),
                'date': time.strftime('%d.%m.%Y', itemtime),
                'year': int(itemtimestr[0:4]),
                'aired': itemtimestr,
                'duration': int(itemdata['duration']) if 'duration' in itemdata.keys() else 0,
                'url': mediaurl,
                'art': itemdata['image']['path'] if 'image' in itemdata.keys() else ''
            })
        except:
            continue

    return output_final

    
