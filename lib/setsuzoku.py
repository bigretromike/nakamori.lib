#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
from datetime import datetime
import random
from proxy.kodi_version_proxy import kodi_proxy

try:
    from urllib import urlencode
    from urllib2 import urlopen
except: # For Python 3
    from urllib.parse import urlencode
    from urllib.request import urlopen


_enable_logging = xbmcaddon.Addon('plugin.video.nakamori').getSetting('feedback')


class Category(object):
    PLUGIN = 'plugin'
    SCRIPT = 'script'
    PLAYER = 'player'
    SERVICE = 'service'
    SETTINGS = 'settings'
    EIGAKAN = 'eigakan'
    MAINTENANCE = 'maintenance'
    SHOKO = 'shoko'
    SYSTEM = 'system'
    CALENDAR = 'calendar'


class Action(object):
    MENU = 'menu'
    MONITOR = 'monitor'
    LIBRARY = 'library'
    DEVICEID = 'deviceid'
    CALENDAR = 'calendar'
    SETTINGS = 'settings'
    PROFILE = 'profile'
    IMAGE = 'image'
    LISTITEM = 'listitem'
    CONNECTION = 'connection'
    LOGIN = 'login'
    FILE = 'file'
    EPISODE = 'episode'
    TRANSCODE = 'transcode'
    SERIES = 'series'
    GROUP = 'group'
    VERSION = 'version'
    OS = 'os'
    KODI = 'kodi'
    TYPE1 = 'type1'
    TYPE2 = 'type2'


class Event(object):
    FAVORITE = 'favorite'
    UNSORT = 'unsort'
    MAIN = 'main'
    RECENTLY = 'recently'
    STARTUP = 'startup'
    CALL = 'call'
    SEARCH = 'search'
    INIT = 'init'
    CREATE = 'create'
    SEND = 'send'
    CLEAN = 'clean'
    WIZARD = 'wizard'
    INFORMATION = 'information'
    OPEN = 'open'
    CHECK = 'check'
    RESCAN = 'rescan'
    REHASH = 'rehash'
    PROBE = 'probe'
    START = 'start'
    STOP = 'stop'
    SUCCESS = 'success'
    FAIL = 'fail'
    ADD = 'add'
    WATCHED = 'watched'
    SYNC = 'sync'
    EXTERNAL = 'external'
    BOOKMARK = 'bookmark'
    TVSHOW = 'tvshow'
    MOVIE = 'movie'
    SETTINGS = 'settings'


def log_call(category, action, event, value=1):
    # RESPECT USER WILL
    if _enable_logging:
        from nakamori_utils.kodi_utils import get_device_id
        # https://developer.matomo.org/api-reference/tracking-api
        deviceid = get_device_id()
        x = {
            'idsite': '6',
            'rec': '1',
            'action_name': 'nakamori/feedback',
            '_id': deviceid, # 16hex
            'rand': random.randint(1,999), # should be unique each run
            'apiv': '1',
            'e_c': str(category), # category
            'e_a': str(action), # action_name
            'e_n': str(event), # event name
            'e_v': value, # value = int
            'bots': 1,
            'send_image': 0,
            'h': datetime.now().time().hour,
            'm': datetime.now().time().minute,
            's': datetime.now().time().second,
            'lang': xbmc.getLanguage(xbmc.ISO_639_2, True),
            'ua': kodi_proxy.user_agent(),
            'cookie': 0,
        }
        params = urlencode(x)
        url = "https://neko.monogatari.pl/piwik.php?%s" % params

        try:
            urlopen(url)
        except:
            pass
