import gzip
import json
import sys
import time
from io import BytesIO
from abc import abstractmethod

from nakamori_utils.globalvars import plugin_addon

from socket import timeout
import xbmc

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
        self.api_key = ''

    def set_temporary_apikey(self, apikey):
        self.api_key = apikey

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
        try:
            import error_handler as eh
            headers = {
                'Accept': 'application/json',
                'apikey': apikey,
            }

            if referer is not None:
                referer = quote(self.encode(referer)).replace('%3A', ':')
                if len(referer) > 1:
                    headers['Referer'] = referer

            if '127.0.0.1' not in url and 'localhost' not in url:
                headers['Accept-Encoding'] = 'gzip'
            if '/Stream/' in url:
                headers['api-version'] = '1.0'

            # self.encode(url) # py3 fix
            req = Request(url, headers=headers)
            data = None

            eh.spam('Getting Data ---')
            eh.spam('URL: ', url)
            eh.spam('Headers:', headers)
            response = urlopen(req, timeout=int(timeout))

            if response.info().get('Content-Encoding') == 'gzip':
                eh.spam('Got gzipped response. Decompressing')
                try:
                    buf = BytesIO(response.read())
                    f = gzip.GzipFile(fileobj=buf)
                    data = f.read()
                except Exception as e:
                    eh.spam('Failed to decompress.', e.message)
            else:
                data = response.read()
            response.close()

            eh.spam('Response Body:', data)
            eh.spam('Checking Response for a text error.\n')

            if data is not None and data != '':
                self.parse_possible_error(req, data)

            return data
        except Exception as ex:
            xbmc.log(' === get_data error === %s' % ex, xbmc.LOGNOTICE)

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

    def post_json(self, url_in, body, custom_timeout=int(plugin_addon.getSetting('timeout'))):
        """
        Push data to server using 'POST' method
        :param url_in:
        :param body:
        :param custom_timeout: if not given timeout from plugin setting will be used
        :return:
        """
        if len(body) > 3:
            proper_body = '{' + body + '}'
            return self.post_data(url=url_in, data_in=proper_body, custom_timeout=custom_timeout)
        else:
            return None

    def post_data(self, url, data_in, custom_timeout=int(plugin_addon.getSetting('timeout'))):
        """
        Send a message to the server and wait for a response
        Args:
            url: the URL to send the data to
            data_in: the message to send (in json)
            custom_timeout: if not given timeout from plugin setting will be used

        Returns: The response from the server
        """
        import error_handler as eh
        from error_handler import ErrorPriority
        if data_in is None:
            data_in = b''

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        apikey = plugin_addon.getSetting('apikey')
        if apikey is not None and apikey != '':
            headers['apikey'] = apikey

        eh.spam('POSTing Data ---')
        eh.spam('URL:', url)
        eh.spam('Headers:', headers)
        eh.spam('POST Body:', data_in)

        try:
            # self.encode(url) # py3 fix
            req = Request(url, self.encode(data_in), headers)
            data_out = None

            response = urlopen(req, timeout=custom_timeout)
            data_out = response.read()
            response.close()
            eh.spam('Response Body:', data_out)
            eh.spam('Checking Response for a text error.\n')
            if data_out is not None and data_out != '':
                self.parse_possible_error(req, data_out)
        except timeout:
            # if using very short time out to not wait for response it will throw time out err,
            # but we check if that was intended by checking custom_timeout
            # if it wasn't intended we handle it the old way
            if custom_timeout == int(plugin_addon.getSetting('timeout')):
                eh.exception(ErrorPriority.HIGH)
        except http_error as err:
            raise err
        except Exception as ex:
            xbmc.log('==== post_data error ==== %s ' % ex, xbmc.LOGNOTICE)
            eh.exception(ErrorPriority.HIGH)

        return data_out

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

    def get_json(self, url_in, direct=False, force_cache=False, cache_time=0):
        """
        use 'get' to return json body as string
        :param url_in:
        :param direct: force to bypass cache
        :param force_cache: force to use cache even if disabled
        :param cache_time: ignore setting to set custom cache expiration time, mainly to expire data quicker to refresh watch flags
        :return:
        """

        import error_handler as eh
        from error_handler import ErrorPriority
        try:
            timeout = plugin_addon.getSetting('timeout')
            if self.api_key is None or self.api_key == '':
                apikey = plugin_addon.getSetting('apikey')
            else:
                apikey = self.api_key
            # if cache is disabled, overwrite argument and force it to direct
            if plugin_addon.getSetting('enableCache') != 'true':
                direct = True
            if direct and not force_cache:
                body = self.get_data(url_in, None, timeout, apikey)
            else:
                import cache
                eh.spam('Getting a Cached Response ---')
                eh.spam('URL:', url_in)
                db_row = cache.get_data_from_cache(url_in)
                if db_row is not None:
                    valid_until = cache_time if cache_time > 0 else int(plugin_addon.getSetting('expireCache'))
                    expire_second = time.time() - float(db_row[1])
                    if expire_second > valid_until:
                        # expire, get new date
                        eh.spam('The cached data is stale.')
                        body = self.get_data(url_in, None, timeout, apikey)
                        cache.remove_cache(url_in)
                        cache.add_cache(url_in, body)
                    else:
                        body = db_row[0]
                else:
                    eh.spam('No cached data was found for the URL.')
                    body = self.get_data(url_in, None, timeout, apikey)
                    cache.add_cache(url_in, body)
        except http_error as err:
            raise err
        except Exception as ex:
            xbmc.log(' ========= ERROR JSON ============  %s' % ex, xbmc.LOGNOTICE)
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
                    error_msg = 'The connection was refused as unauthorized'

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

    @abstractmethod
    def is_unicode_or_string(self, value):
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
            return ''

    def isnumeric(self, value):
        return unicode(value).isnumeric()

    def is_unicode_or_string(self, value):
        return isinstance(value, (str, unicode))


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

    def is_unicode_or_string(self, value):
        return isinstance(value, str)


python_proxy = Python2Proxy() if sys.version_info[0] < 3 else Python3Proxy()
http_error = HTTPError
