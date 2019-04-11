# -*- coding: utf-8 -*-
import json
from distutils.version import LooseVersion

import xbmcgui
from nakamori_utils import kodi_utils
from nakamori_utils.globalvars import *
from nakamori_utils.kodi_utils import message_box
from proxy import python_version_proxy
from proxy.python_version_proxy import python_proxy as pyproxy
import error_handler as eh
from error_handler import ErrorPriority
import xbmc

localized = lib_addon.getLocalizedString

try:
    basestring
except NameError:
    basestring = str  # For Python 3


localization_notification_map = {
    'rescan': plugin_addon.getLocalizedString(30190),
    'rehash': plugin_addon.getLocalizedString(30189),
    'runimport': plugin_addon.getLocalizedString(30198),
    'folderscan': plugin_addon.getLocalizedString(30199),
}

localization_refresh_map = {
    'refresh10': plugin_addon.getLocalizedString(30191),
    'awhile': plugin_addon.getLocalizedString(30193),
}


def perform_server_action(command, object_id=None, refresh='refresh10', post=False, post_body=''):
    """
    Performs an action on the server
    Args:
        object_id: the object_id or None
        command: string representing api/command?object_id=...
        refresh: whether to refresh
        post: is it a POST endpoint
        post_body: the body to post, minus the {}
    """
    key_url = server + '/api/' + command
    if object_id is not None and object_id != 0 and object_id != '':
        key_url = pyproxy.set_parameter(key_url, 'id', object_id)

    eh.spam('url:', key_url, 'id:', object_id)
    eh.spam('post:', post, 'body:', post_body)

    if post:
        response = pyproxy.post_json(key_url, post_body)
    else:
        response = pyproxy.get_json(key_url)

    eh.spam(response)

    refresh_message = localization_refresh_map.get(refresh, '')
    xbmc.executebuiltin('XBMC.Notification(%s, %s, 2000, %s)' % (
        localization_notification_map.get(command, command),
        refresh_message, plugin_addon.getAddonInfo('icon')))

    # there's a better way to do this, but I don't feel like trying to make it work in Python
    if refresh != '' and refresh != 'awhile':
        xbmc.sleep(10000)
        kodi_utils.refresh()


def rescan_file(object_id):
    """
    This rescans a file for info from AniDB.
    :param object_id: VideoLocalID
    """
    perform_server_action('rescan', object_id=object_id)


def rehash_file(object_id):
    """
    This rehashes and rescans a file
    :param object_id: VideoLocalID
    """
    perform_server_action('rehash', object_id=object_id)


def folder_list():
    """
    List all import folders
    :return: ImportFolderID of picked folder
    """
    return kodi_utils.import_folder_list()


def mediainfo_update():
    """
    Update mediainfo for all files
    :return:
    """
    perform_server_action('mediainfo_update', refresh='awhile')


def stats_update():
    """
    Update stats via server
    :return:
    """
    perform_server_action('stats_update', refresh='awhile')


def run_import():
    """
    Same as pressing run import in Shoko. It performs many tasks, such as checking for files that are not added
    :return: None
    """
    perform_server_action('/folder/import', object_id=None, refresh='awhile')


def scan_folder(object_id):
    """
    THE API FOR THIS IS BROKEN. DON'T TRY TO USE IT
    Scans an import folder. This checks files for hashes and adds new ones. It takes longer than run import
    :param object_id:
    :return:
    """
    pass


def remove_missing_files():
    """
    Run "remove missing files" on server to remove every file that is not accessible by server
    This give a different localization, so for now, use another method.
    Ideally, we would make an Enum for Refresh Message
    :return:
    """
    perform_server_action('remove_missing_files', refresh='awhile')


def get_server_status(ip=plugin_addon.getSetting('ipaddress'), port=plugin_addon.getSetting('port')):
    """
    Try to query server for status, display messages as needed
    don't bother with caching, this endpoint is really fast
    :return: bool
    """
    if port is None:
        port = plugin_addon.getSetting('port')
    if isinstance(port, basestring):
        port = pyproxy.safe_int(port)
        port = port if port != 0 else 8111

    url = 'http://%s:%i/api/init/status' % (ip, port)
    try:
        # this should throw if there's an error code
        response = pyproxy.get_json(url, True)

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
            message_box(localized(30017), localized(30018), localized(30019), localized(30020))
            return False

        busy = xbmcgui.DialogProgress()
        busy.create(localized(30021), startup_state)
        busy.update(1)
        # poll every second until the server gives us a response that we want
        while not busy.iscanceled():
            xbmc.sleep(1000)
            response = pyproxy.get_json(url, True)

            # this should not happen
            if response is None or pyproxy.safe_int(response) > 200:
                busy.close()
                message_box(localized(30022), localized(30023), localized(30033), localized(30034))
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

            busy.update(1, localized(30021), startup_state)
            if startup_failed:
                break

        busy.close()

        if startup_failed:
            message_box(localized(30017), localized(30018), localized(30019),
                        localized(30020))
            return False
        return True
    except python_version_proxy.http_error as httperror:
        eh.exception(ErrorPriority.NORMAL)
        if httperror.code == 503:
            return startup_handle_no_connection(ip, port)
        if httperror.code == 404:
            return startup_handle_404()
        show_connection_error()
        return False
    except:
        eh.exception(ErrorPriority.HIGHEST)
        return False


def startup_handle_no_connection(ip=None, port=None):
    # 503 usually means that the server is not started,
    # which could mean that it's starting, but not even hosting yet
    # retry for a bit, then give up if it doesn't respond
    busy = xbmcgui.DialogProgress()
    # TODO LOCALIZE
    busy.create('Waiting for Server Startup', 'This will retry for a short while')
    busy.update(1)
    # poll every second until the server gives us a response that we want
    counter = 0
    time = 30
    while not busy.iscanceled() and counter < time:
        xbmc.sleep(1000)
        busy.update(int(round(counter * 100.0 / 30)))
        if can_connect(ip, port):
            break
        counter += 1

    if counter == time - 1:
        busy.close()
        return False

    busy.close()
    return True


def startup_handle_404():
    # 404 probably means that the user is a bad person who didn't update their server
    # Another possible circumstance is the user has something other than Shoko
    # running on port 8111 (or whatever they put)
    show_connection_error()
    return False


def show_connection_error():
    message_box(localized(30022), localized(30023), localized(30024), localized(30025))


def get_version(ip=plugin_addon.getSetting('ipaddress'), port=plugin_addon.getSetting('port'), force=False):
    legacy = LooseVersion('0.0')
    version = ''
    try:
        _shoko_version = plugin_addon.getSetting('good_version')
        _good_ip = plugin_addon.getSetting('good_ip')
        if not force and _shoko_version != LooseVersion('0.1') and _good_ip == ip:
            return _shoko_version
        json_file = pyproxy.get_json('http://' + str(ip) + ':' + str(port) + '/api/version', direct=True)
        if json_file is None:
            return legacy
        try:
            data = json.loads(json_file)
        except:
            return legacy

        for module in data:
            if module['name'] == 'server':
                version = module['version']
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


def can_connect(ip=None, port=None):
    if port is None:
        port = plugin_addon.getSetting('port')
    if isinstance(port, basestring):
        port = pyproxy.safe_int(port)
        port = port if port != 0 else 8111

    if ip is None:
        ip = plugin_addon.getSetting('ipaddress')
    try:
        # this handles the case of errors as well
        json_file = pyproxy.get_json('http://%s:%i/api/version' % (ip, port), direct=True)
        if json_file is None:
            return False
        return True
    except:
        return False


def auth():
    """
    Checks the apikey, if any, attempts to log in, and saves if we have auth
    :return: bool True if all completes successfully
    """
    # new flow for auth
    # we store the apikey, and its existence is what determines whether to try to connect
    # we will have a log out button, and that wipes the apikey, then we go through the log in steps

    # we have an apikey. try to connect
    if plugin_addon.getSetting('apikey') != '' and can_user_connect():
        return True

    # just in case there's a situation where the wizard isn't working, we can fill it in the settings
    if plugin_addon.getSetting('login') != '':
        login = plugin_addon.getSetting('login')
        password = plugin_addon.getSetting('password')
        apikey = get_apikey(login, password)
        if apikey is not None:
            plugin_addon.setSetting('apikey', apikey)
            plugin_addon.setSetting(id='login', value='')
            plugin_addon.setSetting(id='password', value='')
            return can_user_connect()
    # we tried the apikey, and login failed, too
    return False


def get_apikey(login, password):
    creds = (login, password, plugin_addon.getSetting('device'))
    body = '{"user":"%s","pass":"%s","device":"%s"}' % creds
    post_body = pyproxy.post_data(server + '/api/auth', body)
    auth_body = json.loads(post_body)
    if 'apikey' in auth_body:
        apikey_found_in_auth = str(auth_body['apikey'])
        return apikey_found_in_auth
    else:
        raise Exception(localized(30026))


def can_user_connect():
    try:
        ping = pyproxy.get_json(server + '/api/ping')
        if '"response":"pong"' in ping:
            return True
        raise RuntimeError(localized(30027))
    except:
        # because we always check for connection first, we can assume that auth is the only problem
        # we need to log in
        plugin_addon.setSetting('apikey', '')
        return False


def trakt_scrobble(ep_id, status, progress, movie, notification):
    note_text = ''
    if status == 1:
        # start
        progress = 0
        note_text = localized(30028)
    elif status == 2:
        # pause
        note_text = localized(30029)
    elif status == 3:
        # finish
        progress = 100
        note_text = localized(30030)

    if notification:
        xbmc.executebuiltin('XBMC.Notification(%s, %s %s, 7500, %s)' % ('Trakt.tv', note_text, '',
                                                                        plugin_addon.getAddonInfo('icon')))

    pyproxy.get_json(server + '/api/ep/scrobble?id=%i&ismovie=%s&status=%i&progress=%i' %
                     (ep_id, movie, status, progress))
