from resources.lib.scraper import USER_AGENT

from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.parse import urlencode

import http.cookiejar

class TripleRWebsite():
    def __init__(self, cookiepath):
        self._cookiepath = cookiepath
        self.cj = http.cookiejar.LWPCookieJar()

    def _loadcj(self):
        if os.path.isfile(self._cookiepath):
            cj.load(self._cookiepath)

    def _delcj(self):
        self.cj = http.cookiejar.LWPCookieJar()
        try:
            os.remove(self._cookiepath)
        except:
            pass

    def request(self, url, data):
        req = Request(url, data.encode())
        req.add_header('User-Agent', USER_AGENT)

        opener = build_opener(HTTPCookieProcessor(self.cj))

        response = opener.open(req)
        source = response.read().decode()
        response.close()

        return source

    def login(self, username, password):
        self._delcj()

        if username and password:
            login_url = 'https://www.rrr.org.au/sign-in'
            login_data = urlencode(
                {
                    'subscriber_account[email]': username,
                    'subscriber_account[password]': password,
                    '_csrf': ['', 'javascript-disabled'],
                }
            )

            source = self.request(login_url, login_data)

            if self._check_login(source, username):
                self.cj.save(self._cookiepath)
                return self.cj
        else:
            return False

    def _check_login(self, source, username):
        if username.lower() in source.lower():
            return True
        else:
            return False

    def enter(self, resource_path):
            entry_url = ''.join(('https://www.rrr.org.au/subscriber-', resource_path[1:]))
            entry_data = urlencode(
                {
                    'entry[null]': '',
                    '_csrf': ['', 'javascript-disabled'],
                }
            )

            return self.request(entry_url, entry_data)

