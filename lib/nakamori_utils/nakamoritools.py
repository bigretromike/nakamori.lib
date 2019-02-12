# -*- coding: utf-8 -*-
import sys
from urllib import unquote

import xbmc
import xbmcgui
import xbmcplugin
import traceback
import os
import json
import time
import collections
import re

from distutils.version import LooseVersion
from nakamori_utils.globalvars import *

# TODO refactor version info out into proxies
# __ is public, _ is protected
from proxy.python_version_proxy import python_proxy as pyproxy

global addonversion
global addonid
global addonname
global icon
global localize
global home

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


def search_box():
    """
    Shows a keyboard, and returns the text entered
    :return: the text that was entered
    """
    keyb = xbmc.Keyboard('', script_addon.getLocalizedString(30026))
    keyb.doModal()
    search_text = ''

    if keyb.isConfirmed():
        search_text = keyb.getText()
    return search_text


def get_kodi_setting_bool(setting):
    try:
        parent_setting = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params":' +
            '{"setting": "' + setting + '"}, "id": 1}')
        # {"id":1,"jsonrpc":"2.0","result":{"value":false}} or true if ".." is displayed on list

        result = json.loads(parent_setting)
        if "result" in result:
            if "value" in result["result"]:
                return result["result"]["value"]
    except Exception as exc:
        error("jsonrpc_error: " + str(exc))
    return False


def get_kodi_setting_int(setting):
    try:
        parent_setting = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params":' +
            '{"setting": "' + setting + '"}, "id": 1}')
        # {"id":1,"jsonrpc":"2.0","result":{"value":false}} or true if ".." is displayed on list

        result = json.loads(parent_setting)
        if "result" in result:
            if "value" in result["result"]:
                return int(result["result"]["value"])
    except Exception as exc:
        error("jsonrpc_error: " + str(exc))
    return -1


def move_position_on_list(control_list, position=0, force=False):
    """
    Move to the position in a list - use episode number for position
    Args:
        control_list: the list control
        position: the index of the item not including settings
        force: bypass setting and set position directly
    """
    if not force:
        if position < 0:
            position = 0
        if plugin_addon.getSetting('show_continue') == 'true':
            position = int(position + 1)

        if get_kodi_setting_bool("filelists.showparentdiritems"):
            position = int(position + 1)

    try:
        control_list.selectItem(position)
    except:
        try:
            control_list.selectItem(position - 1)
        except Exception as e:
            error('Unable to reselect item', str(e))
            xbmc.log('control_list: ' + str(control_list.getId()), xbmc.LOGWARNING)
            xbmc.log('position: ' + str(position), xbmc.LOGWARNING)


def remove_anidb_links(data=""):
    """
    Remove anidb links from descriptions
    Args:
        data: the strong to remove links from

    Returns: new string without links

    """
    # search for string with 1 to 3 letters and 1 to 7 numbers
    p = re.compile('http://anidb.net/[a-z]{1,3}[0-9]{1,7}[ ]')
    data2 = p.sub('', data)
    # remove '[' and ']' that included link to anidb.net
    # was ('(\[|\])')
    p = re.compile('[[]]')
    return p.sub('', data2)


def safe_int(object_body):
    """
    safe convert type to int to avoid NoneType
    :param object_body:
    :return: int
    """
    try:
        if object_body is not None and object_body != '':
            return int(object_body)
        else:
            return 0
    except:
        return 0


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
        xbmc.executebuiltin("XBMC.Notification(%s, %s %s, 7500, %s)" % ('Trakt.tv', note_text, '',
                                                                        plugin_addon.getAddonInfo('icon')))

    get_json(server + "/api/ep/scrobble?id=" + str(ep_id) + "&ismovie=" + str(movie) +
             "&status=" + str(status) + "&progress=" + str(progress))


def sync_offset(file_id, current_time):
    """
    sync offset of played file
    :param file_id: id
    :param current_time: current time in seconds
    """

    offset_url = server + "/api/file/offset"
    offset_body = '"id":' + str(file_id) + ',"offset":' + str(current_time * 1000)
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
    key = server + "/api"

    if watched is True:
        watched_msg = "watched"
        if episode_id != '':
            key += "/ep/watch"
        elif anime_id != '':
            key += "/serie/watch"
        elif group_id != '':
            key += "/group/watch"
    else:
        watched_msg = "unwatched"
        if episode_id != '':
            key += "/ep/unwatch"
        elif anime_id != '':
            key += "/serie/unwatch"
        elif group_id != '':
            key += "/group/unwatch"

    if file_id != 0:
        sync_offset(file_id, 0)

    if plugin_addon.getSetting('spamLog') == 'true':
        xbmc.log('file_d: ' + str(file_id), xbmc.LOGWARNING)
        xbmc.log('epid: ' + str(episode_id), xbmc.LOGWARNING)
        xbmc.log('anime_id: ' + str(anime_id), xbmc.LOGWARNING)
        xbmc.log('group_id: ' + str(group_id), xbmc.LOGWARNING)
        xbmc.log('key: ' + key, xbmc.LOGWARNING)

    # sync mark flags
    sync = plugin_addon.getSetting("syncwatched")
    if sync == "true":
        if episode_id != '':
            body = '?id=' + episode_id
            get_json(key + body)
        elif anime_id != '':
            body = '?id=' + anime_id
            get_json(key + body)
        elif group_id != '':
            body = '?id=' + group_id
            get_json(key + body)
    else:
        xbmc.executebuiltin('XBMC.Action(ToggleWatched)')

    box = plugin_addon.getSetting("watchedbox")
    if box == "true":
        xbmc.executebuiltin("XBMC.Notification(%s, %s %s, 2000, %s)" % (script_addon.getLocalizedString(30024),
                                                                        script_addon.getLocalizedString(30025),
                                                                        watched_msg,
                                                                        plugin_addon.getAddonInfo('icon')))
    refresh()


def refresh():
    """
    Refresh and re-request data from server
    refresh watch status as we now mark episode and refresh list so it show real status not kodi_cached
    Allow time for the ui to reload
    """
    xbmc.executebuiltin('Container.Refresh')
    xbmc.sleep(int(plugin_addon.getSetting('refresh_wait')))


def set_sort_method(int_of_sort_method=0):
    """
    Ser given sort method
    :param int_of_sort_method: int parameter of sort method
    :return: set sort method
    """
    # xbmc.log('-> trying to set \'%s\' sorting' % int_of_sort_method, xbmc.LOGWARNING)
    xbmc.executebuiltin('Container.SetSortMethod(' + str(int_of_sort_method) + ')')


def set_user_sort_method(place):
    """
    Set user define type of sort method.
    For more check:
    https://codedocs.xyz/AlwinEsch/kodi/group___list__of__sort__methods.html
    https://github.com/xbmc/xbmc/blob/master/xbmc/utils/SortUtils.cpp#L529-L577
    """
    sort_method = {
        'Server': 0,
        'Title': 7,
        'Episode': 23,
        'Date': 2,
        'Rating': 17
    }

    place_setting = {
        'filter': plugin_addon.getSetting("default_sort_filter"),
        'group': plugin_addon.getSetting("default_sort_group_series"),
        'episode': plugin_addon.getSetting("default_sort_episodes")
    }

    user_sort_method = place_setting.get(place, 'Server')
    method_for_sorting = sort_method.get(user_sort_method, 0)
    set_sort_method(method_for_sorting)


def vote_series(series_id):
    """
    Marks a rating for a series
    Args:
        series_id: serie id

    """
    vote_list = ['Don\'t Vote', '10', '9', '8', '7', '6', '5', '4', '3', '2', '1', '0']
    my_vote = xbmcgui.Dialog().select(script_addon.getLocalizedString(30021), vote_list)
    if my_vote == -1:
        return
    elif my_vote != 0:
        vote_value = str(vote_list[my_vote])
        body = '?id=' + series_id + '&score=' + vote_value
        get_json(server + "/api/serie/vote" + body)
        xbmc.executebuiltin("XBMC.Notification(%s, %s %s, 7500, %s)" % (script_addon.getLocalizedString(30021),
                                                                        script_addon.getLocalizedString(30022),
                                                                        vote_value, plugin_addon.getAddonInfo('icon')))


def vote_episode(ep_id):
    """
    Marks a rating for an episode
    Args:
        ep_id: episode id

    """
    vote_list = ['Don\'t Vote', '10', '9', '8', '7', '6', '5', '4', '3', '2', '1', '0']
    my_vote = xbmcgui.Dialog().select(script_addon.getLocalizedString(30023), vote_list)
    if my_vote == -1:
        return
    elif my_vote != 0:
        vote_value = str(vote_list[my_vote])
        body = '?id=' + ep_id + '&score=' + vote_value
        get_json(server + "/api/ep/vote" + body)
        xbmc.executebuiltin("XBMC.Notification(%s, %s %s, 7500, %s)" % (script_addon.getLocalizedString(30023),
                                                                        script_addon.getLocalizedString(30022),
                                                                        vote_value, plugin_addon.getAddonInfo('icon')))


def get_data(url_in, referer, data_type):
    """
    Send a message to the server and wait for a response
    Args:
        url_in: the URL to get data from
        referer: currently not used always should be None
        data_type: extension for url (.json or .xml) to force return type

    Returns: The response from the server in forced type (.json or .xml)
    """
    if data_type != "json":
        data_type = "xml"

    url = url_in

    data = pyproxy.get_data(url, data_type, referer, plugin_addon.getSetting('timeout'),
                            plugin_addon.getSetting('apikey'))

    if data is not None and data != '':
        parse_possible_error(data, data_type)
    return data


def parse_possible_error(data, data_type):
    if data_type == 'json':
        stream = json.loads(data)
        if "StatusCode" in stream:
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
                error(error_msg, error_type='Network Error: ' + code)
                if stream.get('Details', '') != '':
                    xbmc.log(pyproxy.encode(stream.get('Details')), xbmc.LOGERROR)


def get_json(url_in, direct=False):
    """
    use 'get' to return json body as string
    :param url_in:
    :param direct: force to bypass cache
    :return:
    """
    try:
        if direct:
            body = get_data(url_in, None, "json")
        else:
            if (plugin_addon.getSetting("enableCache") == "true") and ("file?id" not in url_in):
                import cache
                db_row = cache.check_in_database(url_in)
                if db_row is None:
                    db_row = 0
                if db_row > 0:
                    expire_second = time.time() - float(db_row)
                    if expire_second > int(plugin_addon.getSetting("expireCache")):
                        # expire, get new date
                        body = get_data(url_in, None, "json")
                        params = {'extras': 'single-delete', 'name': url_in}
                        cache.remove_cache(params)
                        cache.add_cache(url_in, json.dumps(body))
                    else:
                        body = cache.get_data_from_cache(url_in)
                else:
                    body = get_data(url_in, None, "json")
                    cache.add_cache(url_in, json.dumps(body))
            else:
                body = get_data(url_in, None, "json")
            # if code does not exist, then assume we are receiving proper data
            # if str(body.get('code', '200')) != '200':
            #    raise HTTPError(url_in, body.get('code', '0'), body.get('message', ''), None, None)
    except pyproxy.http_error as err:
        body = err.code
        return body
    except:
        xbmc.log('--> body = None, because error in get_json')
        body = None
    return body


def error(msg, error_type='Error', silent=False):
    """
    Log and notify the user of an error
    Args:
        msg: the message to print to log and user notification
        error_type: Type of Error
        silent: disable visual notification
    """
    xbmc.log("Nakamori " + str(addonversion) + " id: " + str(addonid), xbmc.LOGERROR)
    xbmc.log('---' + msg + '---', xbmc.LOGERROR)
    key = sys.argv[0]
    if len(sys.argv) > 2 and sys.argv[2] != '':
        key += sys.argv[2]
    xbmc.log('On url: ' + unquote(key), xbmc.LOGERROR)
    try:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        if exc_type is not None and exc_obj is not None and exc_tb is not None:
            xbmc.log(str(exc_type) + " at line " + str(exc_tb.tb_lineno) + " in file " + str(
                os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]), xbmc.LOGERROR)
            traceback.print_exc()
    except Exception as e:
        xbmc.log("There was an error catching the error. WTF.", xbmc.LOGERROR)
        xbmc.log("The error message: " + str(e), xbmc.LOGERROR)
        traceback.print_exc()
    if not silent:
        xbmc.executebuiltin('XBMC.Notification(%s, %s %s, 2000, %s)' % (error_type, ' ', msg,
                                                                        plugin_addon.getAddonInfo('icon')))


home = pyproxy.decode(xbmc.translatePath(plugin_addon.getAddonInfo('path')))


def message_box(title, text, text2=None, text3=None):
    xbmcgui.Dialog().ok(title, text, text2, text3)


def valid_user():
    """
    Logs into the server and stores the apikey, then checks if the userid is valid
    :return: bool True if all completes successfully
    """

    if plugin_addon.getSetting("apikey") != "" and plugin_addon.getSetting("login") == "":
        return True, plugin_addon.getSetting("apikey")
    else:
        xbmc.log('-- apikey empty --', xbmc.LOGWARNING)
        try:
            if plugin_addon.getSetting("login") != "" and plugin_addon.getSetting("device") != "":
                _server = "http://" + plugin_addon.getSetting("ipaddress") + ":" + plugin_addon.getSetting("port")
                body = '{"user":"' + plugin_addon.getSetting("login") + '",' + \
                       '"device":"' + plugin_addon.getSetting("device") + '",' + \
                       '"pass":"' + plugin_addon.getSetting("password") + '"}'
                post_body = pyproxy.post_data(_server + "/api/auth", body)
                auth = json.loads(post_body)
                if "apikey" in auth:
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
    if plugin_addon.getSetting("spamLog") == 'true':
        if details is not None:
            xbmc.log("---- " + name + ' ----', xbmc.LOGWARNING)

            for i in details:
                if isinstance(details, dict):
                    a = details.get(pyproxy.decode(i))
                    if a is None:
                        temp_log = "\'unset\'"
                    elif isinstance(a, collections.Iterable):
                        # easier for recursion and pretty
                        temp_log = json.dumps(a, sort_keys=True, indent=4, separators=(',', ': '))
                    else:
                        temp_log = str(a)
                    xbmc.log("-" + str(i) + "- " + temp_log, xbmc.LOGWARNING)
                elif isinstance(details, collections.Iterable):
                    temp_log = json.dumps(i, sort_keys=True, indent=4, separators=(',', ': '))
                    xbmc.log("-" + temp_log, xbmc.LOGWARNING)


def get_server_status(ip=plugin_addon.getSetting('ipaddress'), port=plugin_addon.getSetting('port')):
    """
    Try to query server for status, display messages as needed
    don't bother with caching, this endpoint is really fast
    :return: bool
    """
    try:
        url = 'http://' + ip + ':' + port + '/api/init/status'
        response = get_json(url, True)
        if response is None or (safe_int(response) > 200 and safe_int(response) != 503 and safe_int(response) != 404):
            message_box('Connection Error', 'There was an error connecting to Shoko Server',
                        'If you have set up Shoko Server,', 'feel free to ask for advice on our discord')
            return False

        if safe_int(response) == 404:
            # 404 probably means that the user is a bad person who didn't update their server
            # Another possible circumstance is the user has something other than Shoko
            # running on port 8111 (or whatever they put)
            version = get_version(ip, port, True)
            if version == LooseVersion("0.0"):
                message_box('Connection Error', 'There was an error connecting to Shoko Server',
                            'If you have set up Shoko Server,', 'feel free to ask for advice on our discord')
                return False
            return True

        if safe_int(response) == 503:
            # 503 usually means that the server is not started,
            # which could mean that it's starting, but not even hosting yet
            # retry for a bit, then give up if it doesn't respond
            busy = xbmcgui.DialogProgress()
            busy.create('Waiting for Server Startup', 'This will retry for a short while')
            busy.update(1, 'Waiting for Server Startup', 'This will retry for a short while')
            # poll every second until the server gives us a response that we want
            counter = 1
            while not busy.iscanceled() and counter < 30:
                xbmc.sleep(1000)
                busy.update(counter * 5)
                response = get_json(url, True)

                if response is None or (safe_int(response) > 200 and safe_int(response) != 503):
                    busy.close()
                    message_box('Connection Error', 'There was an error connecting to Shoko Server',
                                'If you have set up Shoko Server,', 'feel free to ask for advice on our discord')
                    return False
                if safe_int(response) != 503:
                    break
                counter += 1

            busy.close()

        # we should have a json response now
        # example:
        # {"startup_state":"Complete!","server_started":false,"server_uptime":"04:00:45","first_run":false,"startup_failed":false,"startup_failed_error_message":""}
        json_tree = json.loads(response)

        server_started = json_tree.get('server_started', False)
        startup_failed = json_tree.get('startup_failed', False)
        startup_state = json_tree.get('startup_state', '')

        # server started successfully
        if server_started:
            return True

        # not started successfully
        if startup_failed:
            # server finished trying to start, but failed
            message_box('Server Error', 'There was an error starting Shoko Server', 'Check the server\'s status.',
                        'Feel free to ask for advice on our discord')
            return False

        busy = xbmcgui.DialogProgress()
        busy.create('Waiting for Server Startup', startup_state)
        busy.update(1, 'Waiting for Server Startup', startup_state)
        # poll every second until the server gives us a response that we want
        while not busy.iscanceled():
            xbmc.sleep(1000)
            response = get_json(url, True)

            # this should not happen
            if response is None or safe_int(response) > 200:
                busy.close()
                message_box('Connection Error', 'There was an error connecting to Shoko Server',
                            'If you have set up Shoko Server,', 'feel free to ask for advice on our discord')
                return False

            json_tree = json.loads(response)
            server_started = json_tree.get('server_started', False)
            if server_started:
                busy.close()
                return True

            startup_failed = json_tree.get('startup_failed', False)

            if json_tree.get('startup_state', '') == startup_state:
                continue
            startup_state = json_tree.get('startup_state', '')

            busy.update(1, 'Waiting for Server Startup', startup_state)
            if startup_failed:
                break

        busy.close()

        if startup_failed:
            message_box('Server Error', 'There was an error starting Shoko Server', 'Check the server\'s status.',
                        'Feel free to ask for advice on our discord')
            return False
        return True
    except pyproxy.http_error as httperror:
        message_box('Server Error', 'There was an error returned from Shoko Server', 'Check the server\'s status.' +
                    ' Error: ' + str(httperror.code),
                    'Feel free to ask for advice on our discord')
        return False
    except Exception as ex:
        error(ex)
        return False


def get_version(ip=plugin_addon.getSetting("ipaddress"), port=plugin_addon.getSetting("port"), force=False):
    legacy = LooseVersion('0.0')
    version = ''
    try:
        _shoko_version = plugin_addon.getSetting('good_version')
        _good_ip = plugin_addon.getSetting('good_ip')
        if not force:
            if _shoko_version != LooseVersion('0.1') and _good_ip == ip:
                return _shoko_version
        json_file = get_json("http://" + str(ip) + ":" + str(port) + "/api/version", direct=True)
        if json_file is None:
            return legacy
        try:
            data = json.loads(json_file)
        except:
            return legacy

        for module in data:
            if module["name"] == "server":
                version = module["version"]
                break

        plugin_addon.setSetting(id='good_ip', value=ip)

        if version != '':
            try:
                _shoko_version = LooseVersion(version)
                plugin_addon.setSetting(id='good_version', value=str(_shoko_version))
            except:
                return legacy
            return _shoko_version
    except:
        pass
    return legacy


def post_dict(url, body):
    try:
        json_body = json.dumps(body)
        pyproxy.post_data(url, json_body)
    except:
        error('Failed to send data')


def add_dir(name, url, mode, iconimage='DefaultTVShows.png', plot="", poster="DefaultVideo.png", filename="none",
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

    liz = xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo(type="Video", infoLabels={"Title": name, "Plot": plot})
    liz.setProperty("Poster_Image", iconimage)
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
    file_flag = 'news.log'
    if os.path.exists(os.path.join(home, file_flag)):
        os.remove(os.path.join(home, file_flag))
        xbmc.executebuiltin('RunScript(script.module.nakamori,?info=information)', True)


# not sure if needed


def kodi_jsonrpc(request):
    try:
        return_data = xbmc.executeJSONRPC(request)
        result = json.loads(return_data)
        return result
    except Exception as exc:
        error("jsonrpc_error: " + str(exc))
