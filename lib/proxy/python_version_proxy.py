import gzip
import json
import sys
import time
from io import BytesIO
from abc import abstractmethod

from nakamori_utils.globalvars import plugin_addon
from proxy import kodi_version_proxy

try:
    from urllib.parse import urlparse, quote, unquote_plus, quote_plus, urlencode
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urllib import quote, unquote_plus, quote_plus, urlencode
    from urlparse import urlparse
    from urllib2 import urlopen, Request, HTTPError, URLError


class BasePythonProxy:
    def __init__(self):
        pass

    @abstractmethod
    def encode(self, value):
        """
        Encodes a string/unicode
        :param value: str or unicode to encode
        :return: encoded str
        """
        pass

    @abstractmethod
    def decode(self, value):
        """
        Decodes a string
        :param value: str
        :return: decoded str or unicode
        """
        pass

    def get_data(self, url, referer, timeout, apikey):
        import error_handler as eh
        req = Request(self.encode(url))
        req.add_header('Accept', 'application/json')
        req.add_header('apikey', apikey)

        if referer is not None:
            referer = quote(self.encode(referer)).replace('%3A', ':')
            if len(referer) > 1:
                req.add_header('Referer', referer)
        if '127.0.0.1' not in url and 'localhost' not in url:
            req.add_header('Accept-encoding', 'gzip')
        data = None

        eh.spam('Getting data...')
        eh.spam('Url: ', url)
        eh.spam('Headers:')
        eh.spam(req.headers)
        response = urlopen(req, timeout=int(timeout))
        if response.info().get('Content-Encoding') == 'gzip':
            try:
                buf = BytesIO(response.read())
                f = gzip.GzipFile(fileobj=buf)
                data = f.read()
            except:
                pass
        else:
            data = response.read()
        response.close()

        eh.spam(data)

        if data is not None and data != '':
            self.parse_possible_error(req, data)

        return data

    def head(self, url_in):
        try:
            urlopen(url_in)
            return True
        except HTTPError:
            # error('HTTPError', e.code)
            return False
        except:
            # error('Exceptions', str(e.args))
            return False

    def set_parameter(self, url, parameter, value):
        """
        Process a URL to add parameters to the query string
        :param url:
        :param parameter: what to set
        :param value: what to set it to. Do not urlencode it
        :return: the url
        :rtype: basestring
        """
        if value is None or value == '':
            if '?' not in url:
                return url
            array1 = url.split('?')
            if (parameter + '=') not in array1[1]:
                return url
            url = array1[0] + '?'
            array2 = array1[1].split('&')
            for key in array2:
                array3 = key.split('=')
                if array3[0] == parameter:
                    continue
                url += array3[0] + '=' + array3[1] + '&'
            return url[:-1]
        value = quote_plus(self.encode(str(value)))
        if '?' not in url:
            return url + '?' + parameter + '=' + value

        array1 = url.split('?')
        if (parameter + '=') not in array1[1]:
            return url + '&' + parameter + '=' + value

        url = array1[0] + '?'
        array2 = array1[1].split('&')
        for key in array2:
            array3 = key.split('=')
            if array3[0] == parameter:
                array3[1] = value
            url += array3[0] + '=' + array3[1] + '&'
        return url[:-1]

    def post_json(self, url_in, body):
        """
        Push data to server using 'POST' method
        :param url_in:
        :param body:
        :return:
        """
        if len(body) > 3:
            proper_body = '{' + body + '}'
            return self.post_data(url_in, proper_body)
        else:
            return None

    def post_data(self, url, data_in):
        """
        Send a message to the server and wait for a response
        Args:
            url: the URL to send the data to
            data_in: the message to send (in json)

        Returns: The response from the server
        """
        import error_handler as eh
        from error_handler import ErrorPriority
        if data_in is not None:
            eh.spam(data_in)
            req = Request(self.encode(url), self.encode(data_in), {'Content-Type': 'application/json'})
            req.add_header('apikey', plugin_addon.getSetting('apikey'))
            req.add_header('Accept', 'application/json')
            data_out = None
            try:
                response = urlopen(req, timeout=int(plugin_addon.getSetting('timeout')))
                data_out = response.read()
                response.close()
                eh.spam(data_out)
            except:
                eh.exception(ErrorPriority.HIGH)
            return data_out
        else:
            eh.error('Tried to POST data with no body')
            return None

    def post(self, url, data, headers=None):
        if headers is None:
            headers = {}
        postdata = urlencode(data)
        req = Request(url, postdata, headers)
        req.add_header('User-Agent', kodi_version_proxy.kodi_proxy.user_agent())
        response = urlopen(req)
        data = response.read()
        response.close()
        return data

    def parse_parameters(self, input_string):
        """Parses a parameter string starting at the first ? found in inputString

        Argument:
        input_string: the string to be parsed, sys.argv[2] by default

        Returns a dictionary with parameter names as keys and parameter values as values
        """
        parameters = {}
        p1 = input_string.find('?')
        if p1 >= 0:
            split_parameters = input_string[p1 + 1:].split('&')
            for name_value_pair in split_parameters:
                # xbmc.log("parseParameter detected Value: " + str(name_value_pair))
                if (len(name_value_pair) > 0) & ('=' in name_value_pair):
                    pair = name_value_pair.split('=')
                    key = pair[0]
                    value = self.decode(unquote_plus(pair[1]))
                    parameters[key] = value
        return parameters

    def quote(self, url):
        return quote(url, '')

    def quote_plus(self, url):
        return quote_plus(url, '')

    def unquote(self, url):
        return unquote_plus(url)

    @abstractmethod
    def isnumeric(self, value):
        pass

    def get_json(self, url_in, direct=False):
        """
        use 'get' to return json body as string
        :param url_in:
        :param direct: force to bypass cache
        :return:
        """
        import error_handler as eh
        from error_handler import ErrorPriority
        try:
            timeout = plugin_addon.getSetting('timeout')
            apikey = plugin_addon.getSetting('apikey')
            if 'file?id' in url_in or plugin_addon.getSetting('enableCache') != 'true':
                direct = True
            if direct:
                body = self.get_data(url_in, None, timeout, apikey)
            else:
                import cache
                db_row = cache.check_in_database(url_in)
                if db_row is None:
                    db_row = 0
                if db_row > 0:
                    expire_second = time.time() - float(db_row)
                    if expire_second > int(plugin_addon.getSetting('expireCache')):
                        # expire, get new date
                        body = self.get_data(url_in, None, timeout, apikey)
                        cache.remove_cache(url_in)
                        cache.add_cache(url_in, body)
                    else:
                        body = cache.get_data_from_cache(url_in)
                else:
                    body = self.get_data(url_in, None, timeout, apikey)
                    cache.add_cache(url_in, body)
        except http_error as err:
            body = err.code
            return body
        except:
            eh.exception(ErrorPriority.HIGH)
            body = None
        return body

    def parse_possible_error(self, request, data):
        """

        :param request:
        :type request: Request
        :param data:
        :type data: srt
        :return:
        """
        stream = json.loads(data)
        if 'StatusCode' in stream:
            code = stream.get('StatusCode')
            if code != '200':
                error_msg = code
                if code == '500':
                    error_msg = 'Server Error'
                elif code == '404':
                    error_msg = 'Invalid URL: Endpoint not Found in Server'
                elif code == '503':
                    error_msg = 'Service Unavailable: Check netsh http'
                elif code == '401' or code == '403':
                    error_msg = 'The was refused as unauthorized'

                code = self.safe_int(code)
                raise HTTPError(request.get_full_url(), code, error_msg, request.headers, None)

    def safe_int(self, obj):
        """
        safe convert type to int to avoid NoneType
        :param obj:
        :return: int
        """
        try:
            if obj is None:
                return 0
            if isinstance(obj, int):
                return obj

            return int(obj)
        except:
            return 0


class Python2Proxy(BasePythonProxy):
    def __init__(self):
        BasePythonProxy.__init__(self)

    def encode(self, i):
        try:
            if isinstance(i, str):
                return i
            elif isinstance(i, unicode):
                return i.encode('utf-8')
            else:
                return str(i)
        except:
            pass  # nt.error('Unicode Error', error_type='Unicode Error')
            return ''

    def decode(self, i):
        try:
            if isinstance(i, str):
                return i.decode('utf-8')
            elif isinstance(i, unicode):
                return i
            else:
                return unicode(i)
        except:
            # error('Unicode Error', error_type='Unicode Error')
            return ''

    def isnumeric(self, value):
        return unicode(value).isnumeric()


class Python3Proxy(BasePythonProxy):
    def __init__(self):
        BasePythonProxy.__init__(self)

    def encode(self, i):
        try:
            if isinstance(i, bytes):
                return i
            elif isinstance(i, str):
                return i.encode('utf-8')
            else:
                return str(i).encode('utf-8')
        except:
            # nt.error('Unicode Error', error_type='Unicode Error')
            return ''

    def decode(self, i):
        try:
            if isinstance(i, bytes):
                return i.decode('utf-8')
            elif isinstance(i, str):
                return i
            else:
                return str(i)
        except:
            # error('Unicode Error', error_type='Unicode Error')
            return ''

    def isnumeric(self, value):
        # noinspection PyUnresolvedReferences
        return str(value).isnumeric()


python_proxy = Python2Proxy() if sys.version_info[0] < 3 else Python3Proxy()
http_error = HTTPError
