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


localize = plugin_addon.getLocalizedString

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


def perform_server_action(command, object_id=None, refresh='refresh10', post=False):
    """
    Performs an action on the server
    Args:
        object_id: the object_id or None
        command: string representing api/command?object_id=...
        refresh: whether to refresh
        post: is it a POST endpoint
    """
    key_url = server + '/api/' + command
    if object_id is not None and object_id != 0 and object_id != '':
        key_url = pyproxy.set_parameter(key_url, 'id', object_id)
    if plugin_addon.getSetting('spamLog') == 'true':
        xbmc.log('object_id: ' + str(object_id), xbmc.LOGWARNING)
        xbmc.log('key: ' + key_url, xbmc.LOGWARNING)

    if post:
        response = pyproxy.post_json(key_url, '')
    else:
        response = pyproxy.get_json(key_url)

    if plugin_addon.getSetting('spamLog') == 'true':
        xbmc.log('response: ' + response, xbmc.LOGWARNING)

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
    THIS DOES NOT HAVE API YET. DON'T TRY TO USE IT
    Same as pressing run import in Shoko. It performs many tasks, such as checking for files that are not added
    :return: None
    """
    pass


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
    This give a different localization, so for now, use another method. Ideally, we would make an Enum for Refresh Message
    :return:
    """
    perform_server_action('remove_missing_files', refresh='awhile')


# TODO MOVE BOTH OF THESE INTO A DIALOG AND A METHOD IN MODELS
def vote_series(series_id):
    """
    Marks a rating for a series
    Args:
        series_id: serie id

    """
    vote_list = ['Don\'t Vote', '10', '9', '8', '7', '6', '5', '4', '3', '2', '1']
    my_vote = xbmcgui.Dialog().select(localize(30021), vote_list)
    if my_vote > 0:
        vote_value = str(vote_list[my_vote])
        body = '?id=' + series_id + '&score=' + vote_value
        pyproxy.get_json(server + '/api/serie/vote' + body)
        xbmc.executebuiltin('XBMC.Notification(%s, %s %s, 7500, %s)' % (localize(30021),
                                                                        localize(30022),
                                                                        vote_value, plugin_addon.getAddonInfo('icon')))


def vote_episode(self, value):
    url = server + '/api/ep/vote'
    url = pyproxy.set_parameter(url, 'id', self.id)
    url = pyproxy.set_parameter(url, 'score', value)
    pyproxy.get_json(url)
    xbmc.executebuiltin('XBMC.Notification(%s, %s %s, 7500, %s)' % (localize(30023),
                                                                    localize(30022),
                                                                    str(value), plugin_addon.getAddonInfo('icon')))


def get_server_status(ip=plugin_addon.getSetting('ipaddress'), port=plugin_addon.getSetting('port')):
    """
    Try to query server for status, display messages as needed
    don't bother with caching, this endpoint is really fast
    :return: bool
    """
    if port is None:
        port = plugin_addon.getSetting('port')
    if isinstance(port, (str, unicode)):
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
            message_box('Server Error', 'There was an error starting Shoko Server', 'Check the server\'s status.',
                        'Feel free to ask for advice on our discord')
            return False

        busy = xbmcgui.DialogProgress()
        busy.create('Waiting for Server Startup', startup_state)
        busy.update(1)
        # poll every second until the server gives us a response that we want
        while not busy.iscanceled():
            xbmc.sleep(1000)
            response = pyproxy.get_json(url, True)

            # this should not happen
            if response is None or pyproxy.safe_int(response) > 200:
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
    message_box('Connection Error', 'There was an error connecting to Shoko Server\n'
                                    'If you have set up Shoko Server, feel free to ask for advice on our discord.'
                                    'If you do, please provide your kodi.log and Shoko Server log.')


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
    if isinstance(port, (str, unicode)):
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
