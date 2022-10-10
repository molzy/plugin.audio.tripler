from resources.lib.scraper import USER_AGENT

from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.parse import urlencode

import http.cookiejar
import os, time, hashlib

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

    def _mtime(self, path):
        try:
            return os.path.getmtime(path)
        except:
            return None

    def _mtimecj(self):
        mtime = self._mtime(self._cookiepath)
        if mtime:
            if (time.time() - mtime) < (24*60*60):
                return True
            else:
                self._delcj()

        return None

    def _hash(self, username, password):
        return hashlib.sha256(bytes(f'{username} - {password}', 'ascii')).hexdigest()[-32:]

    def _cmphash(self, username, password):
        cache = self._cookiepath + '.hash'
        hashvalue = self._hash(username, password)
        if os.path.isfile(cache):
            try:
                hashcache = open(cache, 'r').read()
                return hashvalue == hashcache
            except:
                pass
        return False

    def _writehash(self, username, password):
        cache = self._cookiepath + '.hash'
        hashvalue = self._hash(username, password)
        try:
            open(cache, 'w').write(hashvalue)
            return True
        except:
            return False

    def _delhash(self):
        try:
            os.remove(self._cookiepath + '.hash')
        except:
            pass

    def request(self, url, data):
        if data:
            req = Request(url, data.encode())
        else:
            req = Request(url)
        req.add_header('User-Agent', USER_AGENT)

        opener = build_opener(HTTPCookieProcessor(self.cj))

        response = opener.open(req)
        source = response.read().decode()
        response.close()

        return source

    def login(self, username, password):
        if self._cmphash(username, password):
            if self._mtimecj():
                return True
        else:
            self._delhash()

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
                self._writehash(username, password)
                return self.cj
        else:
            return False

    def _check_login(self, source, username):
        if username.lower() in source.lower():
            return True
        else:
            return False

    def subscribed(self):
        cache = self._cookiepath + '.sub'
        mtime = self._mtime(cache)
        if mtime:
            if (time.time() - mtime) < (15*60):
                return bool(open(cache, 'r').read())
            else:
                os.remove(cache)

        check_url = 'https://www.rrr.org.au/account/check-active.json'
        source = self.request(check_url, None)
        result = self._check_subscription(source)
        open(cache, 'w').write(str(result))
        return result

    def _check_subscription(self, source):
        if '"active":' in source and 'true' in source:
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
