# -*- coding: utf-8 -*-
import sys

from nakamori_utils.kodi_utils import refresh

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

import xbmcgui
import xbmcplugin
import traceback
import json
import collections

from nakamori_utils.globalvars import *

# TODO refactor version info out into proxies
# __ is public, _ is protected
from proxy.python_version_proxy import python_proxy as pyproxy

global addonversion
global addonid
global addonname
global icon
global localize

# noinspection PyRedeclaration
addonversion = plugin_addon.getAddonInfo('version')
# noinspection PyRedeclaration
addonid = plugin_addon.getAddonInfo('id')
# noinspection PyRedeclaration
addonname = plugin_addon.getAddonInfo('name')
# noinspection PyRedeclaration
icon = plugin_addon.getAddonInfo('icon')
# noinspection PyRedeclaration
localize = script_addon.getLocalizedString

pDialog = ''


def trakt_scrobble(ep_id, status, progress, movie, notification):
    note_text = ''
    if status == 1:
        # start
        progress = 0
        note_text = 'Starting Scrobble'
    elif status == 2:
        # pause
        note_text = 'Paused Scrobble'
    elif status == 3:
        # finish
        progress = 100
        note_text = 'Stopping Scrobble'

    if notification:
        xbmc.executebuiltin('XBMC.Notification(%s, %s %s, 7500, %s)' % ('Trakt.tv', note_text, '',
                                                                        plugin_addon.getAddonInfo('icon')))

    pyproxy.get_json(server + '/api/ep/scrobble?id=' + str(ep_id) + '&ismovie=' + str(movie) +
             '&status=' + str(status) + '&progress=' + str(progress))


def sync_offset(file_id, current_time):
    """
    sync offset of played file
    :param file_id: id
    :param current_time: current time in seconds
    """

    offset_url = server + '/api/file/offset'
    offset_body = '"id":' + str(file_id) + ',"offset":' + str(int(current_time * 1000))
    try:
        pyproxy.post_json(offset_url, offset_body)
    except:
        error('error Scrobbling', '', True)


def mark_watch_status(params):
    """
    Marks an episode, series, or group as either watched (offset = 0) or unwatched
    :params: must contain either an episode, series, or group id, and a watched value to mark
    """
    episode_id = params.get('ep_id', '')
    anime_id = params.get('serie_id', '')
    group_id = params.get('group_id', '')
    file_id = params.get('file_id', 0)
    watched = bool(params['watched'])
    key = server + '/api'

    if watched is True:
        watched_msg = 'watched'
        if episode_id != '':
            key += '/ep/watch'
        elif anime_id != '':
            key += '/serie/watch'
        elif group_id != '':
            key += '/group/watch'
    else:
        watched_msg = 'unwatched'
        if episode_id != '':
            key += '/ep/unwatch'
        elif anime_id != '':
            key += '/serie/unwatch'
        elif group_id != '':
            key += '/group/unwatch'

    if file_id != 0:
        sync_offset(file_id, 0)

    if plugin_addon.getSetting('spamLog') == 'true':
        xbmc.log('file_d: ' + str(file_id), xbmc.LOGWARNING)
        xbmc.log('epid: ' + str(episode_id), xbmc.LOGWARNING)
        xbmc.log('anime_id: ' + str(anime_id), xbmc.LOGWARNING)
        xbmc.log('group_id: ' + str(group_id), xbmc.LOGWARNING)
        xbmc.log('key: ' + key, xbmc.LOGWARNING)

    # sync mark flags
    sync = plugin_addon.getSetting('syncwatched')
    if sync == 'true':
        if episode_id != '':
            body = '?id=' + episode_id
            pyproxy.get_json(key + body)
        elif anime_id != '':
            body = '?id=' + anime_id
            pyproxy.get_json(key + body)
        elif group_id != '':
            body = '?id=' + group_id
            pyproxy.get_json(key + body)
    else:
        xbmc.executebuiltin('XBMC.Action(ToggleWatched)')

    box = plugin_addon.getSetting('watchedbox')
    if box == 'true':
        xbmc.executebuiltin('XBMC.Notification(%s, %s %s, 2000, %s)' % (plugin_addon.getLocalizedString(30200),
                                                                        plugin_addon.getLocalizedString(30201),
                                                                        watched_msg,
                                                                        plugin_addon.getAddonInfo('icon')))
    refresh()


def error(msg, error_type='Error', silent=False):
    """
    Log and notify the user of an error
    Args:
        msg: the message to print to log and user notification
        error_type: Type of Error
        silent: disable visual notification
    """
    xbmc.log('Nakamori ' + str(addonversion) + ' id: ' + str(addonid), xbmc.LOGERROR)
    xbmc.log('---' + msg + '---', xbmc.LOGERROR)
    key = sys.argv[0]
    if len(sys.argv) > 2 and sys.argv[2] != '':
        key += sys.argv[2]
    xbmc.log('On url: ' + unquote(key), xbmc.LOGERROR)
    try:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        if exc_type is not None and exc_obj is not None and exc_tb is not None:
            xbmc.log(str(exc_type) + ' at line ' + str(exc_tb.tb_lineno) + ' in file ' + str(
                os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]), xbmc.LOGERROR)
            traceback.print_exc()
    except Exception as e:
        xbmc.log('There was an error catching the error. WTF.', xbmc.LOGERROR)
        xbmc.log('The error message: ' + str(e), xbmc.LOGERROR)
        traceback.print_exc()
    if not silent:
        xbmc.executebuiltin('XBMC.Notification(%s, %s %s, 2000, %s)' % (error_type, ' ', msg,
                                                                        plugin_addon.getAddonInfo('icon')))


def valid_user():
    """
    Logs into the server and stores the apikey, then checks if the userid is valid
    :return: bool True if all completes successfully
    """

    if plugin_addon.getSetting('apikey') != '' and plugin_addon.getSetting('login') == '':
        return True, plugin_addon.getSetting('apikey')
    else:
        xbmc.log('-- apikey empty --', xbmc.LOGWARNING)
        try:
            if plugin_addon.getSetting('login') != '' and plugin_addon.getSetting('device') != '':
                _server = 'http://' + plugin_addon.getSetting('ipaddress') + ':' + plugin_addon.getSetting('port')
                body = '{"user":"' + plugin_addon.getSetting('login') + '",' + \
                       '"device":"' + plugin_addon.getSetting('device') + '",' + \
                       '"pass":"' + plugin_addon.getSetting('password') + '"}'
                post_body = pyproxy.post_data(_server + '/api/auth', body)
                auth = json.loads(post_body)
                if 'apikey' in auth:
                    apikey_found_in_auth = str(auth['apikey'])
                    plugin_addon.setSetting(id='login', value='')
                    plugin_addon.setSetting(id='password', value='')
                    plugin_addon.setSetting(id='apikey', value=apikey_found_in_auth)
                    xbmc.log('-- save apikey: %s' % apikey_found_in_auth, xbmc.LOGWARNING)
                    return True, apikey_found_in_auth
                else:
                    raise Exception('Error Getting apikey')
            else:
                xbmc.log('-- Login and Device Empty --', xbmc.LOGERROR)
                return False, ''
        except Exception as exc:
            error('Error in Valid_User', str(exc))
            return False, ''


def dump_dictionary(details, name):
    if plugin_addon.getSetting('spamLog') == 'true':
        if details is not None:
            xbmc.log('---- ' + name + ' ----', xbmc.LOGWARNING)

            for i in details:
                if isinstance(details, dict):
                    a = details.get(pyproxy.decode(i))
                    if a is None:
                        temp_log = '\'unset\''
                    elif isinstance(a, collections.Iterable):
                        # easier for recursion and pretty
                        temp_log = json.dumps(a, sort_keys=True, indent=4, separators=(',', ': '))
                    else:
                        temp_log = str(a)
                    xbmc.log('-' + str(i) + '- ' + temp_log, xbmc.LOGWARNING)
                elif isinstance(details, collections.Iterable):
                    temp_log = json.dumps(i, sort_keys=True, indent=4, separators=(',', ': '))
                    xbmc.log('-' + temp_log, xbmc.LOGWARNING)


def post_dict(url, body):
    try:
        json_body = json.dumps(body)
        pyproxy.post_data(url, json_body)
    except:
        error('Failed to send data')


def add_dir(name, url, mode, iconimage='DefaultTVShows.png', plot='', poster='DefaultVideo.png', filename='none',
            offset=''):
    # u=sys.argv[0]+"?url="+url+"&mode="+str(mode)+"&name="+quote_plus(name)+"&poster_file="+quote_plus(poster)+"&filename="+quote_plus(filename)
    u = sys.argv[0]
    if mode is not '':
        u = pyproxy.set_parameter(u, 'mode', str(mode))
    if name is not '':
        u = pyproxy.set_parameter(u, 'name', name)
    u = pyproxy.set_parameter(u, 'poster_file', poster)
    u = pyproxy.set_parameter(u, 'filename', filename)
    if offset is not '':
        u = pyproxy.set_parameter(u, 'offset', offset)
    if url is not '':
        u = pyproxy.set_parameter(u, 'url', url)

    liz = xbmcgui.ListItem(name, iconImage='DefaultVideo.png', thumbnailImage=iconimage)
    liz.setInfo(type='Video', infoLabels={'Title': name, 'Plot': plot})
    liz.setProperty('Poster_Image', iconimage)
    if mode is not '':
        if mode == 7:
            ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=False)
        else:
            ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    else:
        # should this even possible ? as failsafe I leave it.
        ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    return ok


def show_information():
    """
    Open information, read news tag from addon.xml so the most important things are shown
    :return:
    """
    file_flag = 'news.log'
    if os.path.exists(os.path.join(plugin_home, file_flag)):
        os.remove(os.path.join(plugin_home, file_flag))
        xbmc.executebuiltin('RunScript(script.module.nakamori,?info=information)', True)


def calendar():
    """
    Open calendar
    :return:
    """
    xbmc.executebuiltin('RunScript(script.module.nakamori,?info=calendar)', True)


def wizard():
    """
    Run wizard if there weren't any before
    :return: nothing, set ip/port user/password in settings
    """
    if plugin_addon.getSetting('wizard') == '0':
        xbmc.executebuiltin('RunScript(script.module.nakamori,?info=wizard)', True)


# not sure if needed


def add_default_parameters(url, obj_id, level):
    key = pyproxy.set_parameter(url, 'id', obj_id)
    key = pyproxy.set_parameter(key, 'level', level)
    key = pyproxy.set_parameter(key, 'tagfilter', tag_setting_flags)
    if plugin_addon.getSetting('request_nocast') == 'true':
        key = pyproxy.set_parameter(key, 'nocast', 1)
    return key
