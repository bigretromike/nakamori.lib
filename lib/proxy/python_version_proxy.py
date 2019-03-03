import gzip
import sys
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

    def get_data(self, url, accept_type, referer, timeout, apikey):
        req = Request(self.encode(url))
        req.add_header('Accept', 'application/' + accept_type)
        req.add_header('apikey', apikey)

        if referer is not None:
            referer = quote(self.encode(referer)).replace('%3A', ':')
            if len(referer) > 1:
                req.add_header('Referer', referer)
        if '127.0.0.1' not in url and 'localhost' not in url:
            req.add_header('Accept-encoding', 'gzip')
        data = None
        response = urlopen(req, timeout=int(timeout))
        if response.info().get('Content-Encoding') == 'gzip':
            try:
                buf = BytesIO(response.read())
                f = gzip.GzipFile(fileobj=buf)
                data = f.read()
            except Exception as ex:
                pass
        else:
            data = response.read()
        response.close()
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
        if data_in is not None:
            req = Request(self.encode(url), self.encode(data_in), {'Content-Type': 'application/json'})
            req.add_header('apikey', plugin_addon.getSetting('apikey'))
            req.add_header('Accept', 'application/json')
            data_out = None
            try:
                response = urlopen(req, timeout=int(plugin_addon.getSetting('timeout')))
                data_out = response.read()
                response.close()
            except Exception as ex:
                pass  # nt.error('Connection Failed in post_data', str(ex))
            return data_out
        else:
            pass  # nt.error('post_data body is None')
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
        return quote(url)

    def quote_plus(self, url):
        return quote_plus(url)

    def unquote(self, url):
        return unquote_plus(url)

    @abstractmethod
    def isnumeric(self, value):
        pass


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
            return ''\


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
            pass  # nt.error('Unicode Error', error_type='Unicode Error')
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
