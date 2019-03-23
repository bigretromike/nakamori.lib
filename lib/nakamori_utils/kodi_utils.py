# -*- coding: utf-8 -*-
import json

import xbmcgui
import xbmcplugin

from nakamori_utils.globalvars import *
import error_handler as eh
from error_handler import ErrorPriority
from nakamori_utils.globalvars import plugin_addon
from proxy.python_version_proxy import python_proxy as pyproxy

try:
    from sqlite3 import dbapi2 as database
except:
    # noinspection PyUnresolvedReferences
    from pysqlite2 import dbapi2 as database


localize = script_addon.getLocalizedString

sorting_types = []


class Sorting(object):
    class SortingMethod(object):
        def __init__(self, container_id, name, listitem_id):
            self.container_id = container_id
            self.name = name
            self.listitem_id = listitem_id
            sorting_types.append(self)

    # There are apparently two lists. SetSortMethod uses a container sorting list, and ListItem uses the one from stubs
    none = SortingMethod(45, 'Server', xbmcplugin.SORT_METHOD_UNSORTED)
    label = SortingMethod(1, 'Label', xbmcplugin.SORT_METHOD_LABEL)
    date = SortingMethod(2, 'Date', xbmcplugin.SORT_METHOD_DATE)
    title = SortingMethod(7, 'Title', xbmcplugin.SORT_METHOD_TITLE)
    time = SortingMethod(9, 'Time', xbmcplugin.SORT_METHOD_DURATION)
    genre = SortingMethod(14, 'Genre', xbmcplugin.SORT_METHOD_GENRE)
    year = SortingMethod(16, 'Year', xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    rating = SortingMethod(17, 'Rating', xbmcplugin.SORT_METHOD_VIDEO_RATING)
    user_rating = SortingMethod(18, 'UserRating', xbmcplugin.SORT_METHOD_VIDEO_USER_RATING)
    episode_number = SortingMethod(23, 'Episode', xbmcplugin.SORT_METHOD_EPISODE)
    sort_title = SortingMethod(29, 'SortTitle', xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
    date_added = SortingMethod(40, 'DateAdded', xbmcplugin.SORT_METHOD_DATEADDED)

    string2id = dict((k.name, k.container_id) for k in sorting_types)
    # inverse dict
    id2string = dict((v, k) for k, v in string2id.items())


def set_window_heading(window_name):
    """
    Sets the window titles
    Args:
        window_name: name to put in titles
    """
    if window_name == 'Continue Watching (SYSTEM)':
        window_name = 'Continue Watching'
    elif window_name == 'Unsort':
        window_name = 'Unsorted'

    window_obj = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    try:
        window_obj.setProperty('heading', str(window_name))
    except Exception as e:
        eh.exception(ErrorPriority.LOW, 'Failed set_window_heading')
        window_obj.clearProperty('heading')
    try:
        window_obj.setProperty('heading2', str(window_name))
    except Exception as e:
        eh.exception(ErrorPriority.LOW, 'Failed set_window_heading 2')
        window_obj.clearProperty('heading2')


def file_list_gui(ep_body):
    """
    Create DialogBox with file list to pick if there is more than 1 file for episode
    :param ep_body:
    :return: int (id of picked file or 0 if none)
    """
    pick_filename = []
    get_fileid = []
    if len(ep_body['files']) > 1:
        for body in ep_body['files']:
            filename = os.path.basename(body['filename'])
            pick_filename.append(filename)
            get_fileid.append(str(body['id']))
        my_file = xbmcgui.Dialog().select(plugin_addon.getLocalizedString(30196), pick_filename)
        if my_file > -1:
            return get_fileid[my_file]
        else:
            # cancel -1,0
            return 0
    elif len(ep_body['files']) == 1:
        return ep_body['files'][0]['id']
    else:
        return 0


def show_file_list(files):
    """
    Create DialogBox with file list to pick if there is more than 1 file for episode
    :param files: list of tuples of names to the object
    :type files: List[Tuple[str,int]]
    :return: int (id of picked file or 0 if none)
    """
    if len(files) > 1:
        items = [x[0] for x in files]
        my_file = xbmcgui.Dialog().select(plugin_addon.getLocalizedString(30196), items)
        if my_file > -1:
            return files[my_file][1]
        else:
            # cancel -1,0
            return 0
    elif len(files) == 1:
        return files[0][1]
    else:
        return 0


def import_folder_list():
    """
    Create DialogBox with folder list to pick if there
    :return: int (vl of selected folder)
    """
    pick_folder = []
    get_id = []
    import_list = json.loads(pyproxy.get_json(server + '/api/folder/list'))
    if len(import_list) > 1:
        for body in import_list:
            location = str(body['ImportFolderLocation'])
            pick_folder.append(location)
            get_id.append(str(body['ImportFolderID']))
        my_folder = xbmcgui.Dialog().select(plugin_addon.getLocalizedString(30119), pick_folder)
        if my_folder > -1:
            return get_id[my_folder]
        else:
            # cancel -1,0
            return 0
    elif len(import_list) == 1:
        return import_list[0]['ImportFolderID']
    else:
        return 0


def clear_listitem_cache():
    """
    Clear mark for nakamori files in kodi db
    :return:
    """
    ret = xbmcgui.Dialog().yesno(plugin_addon.getLocalizedString(30104),
                                 plugin_addon.getLocalizedString(30081), plugin_addon.getLocalizedString(30112))
    if ret:
        db_files = []
        db_path = os.path.join(pyproxy.decode(xbmc.translatePath('special://home')), 'userdata')
        db_path = os.path.join(db_path, 'Database')
        for r, d, f in os.walk(db_path):
            for files in f:
                if 'MyVideos' in files:
                    db_files.append(files)
        for db_file in db_files:
            db_connection = database.connect(os.path.join(db_path, db_file))
            db_cursor = db_connection.cursor()
            db_cursor.execute('DELETE FROM files WHERE strFilename like "%plugin.video.nakamori%"')
            db_connection.commit()
            db_connection.close()
        if len(db_files) > 0:
            xbmcgui.Dialog().ok('', plugin_addon.getLocalizedString(30138))


def clear_image_cache():
    """
    Clear image cache in kodi db
    :return:
    """
    ret = xbmcgui.Dialog().yesno(plugin_addon.getLocalizedString(30104),
                                 plugin_addon.getLocalizedString(30081), plugin_addon.getLocalizedString(30112))
    if ret:
        db_files = []
        db_path = os.path.join(pyproxy.decode(xbmc.translatePath('special://home')), 'userdata')
        db_path = os.path.join(db_path, 'Database')
        for r, d, f in os.walk(db_path):
            for files in f:
                if 'Textures' in files:
                    db_files.append(files)
        for db_file in db_files:
            db_connection = database.connect(os.path.join(db_path, db_file))
            db_cursor = db_connection.cursor()
            db_cursor.execute('DELETE FROM texture WHERE url LIKE "%' + plugin_addon.getSetting('port') + '/api/%"')
            db_connection.commit()
            db_cursor.execute('DELETE FROM texture WHERE url LIKE "%nakamori%"')
            db_connection.commit()
            db_connection.close()
        if len(db_files) > 0:
            xbmcgui.Dialog().ok('', plugin_addon.getLocalizedString(30138))


def search_box():
    """
    Shows a keyboard, and returns the text entered
    :return: the text that was entered
    """
    keyb = xbmc.Keyboard('', localize(30026))
    keyb.doModal()
    search_text = ''

    if keyb.isConfirmed():
        search_text = keyb.getText()
    return search_text


def move_to_index(index, absolute=False):
    try:
        wind = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        control_id = wind.getFocusId()
        control_list = wind.getControl(control_id)
        assert isinstance(control_list, xbmcgui.ControlList)
        move_position_on_list(control_list, index, absolute)
    except:
        eh.exception(ErrorPriority.HIGH, 'Unable to Select Item')


def move_position_on_list(control_list, position=0, absolute=False):
    """
    Move to the position in a list - use episode number for position
    Args:
        control_list: the list control
        position: the index of the item not including settings
        absolute: bypass setting and set position directly
    """
    if not absolute:
        if position < 0:
            position = 0
        if plugin_addon.getSetting('show_continue') == 'true':
            position = int(position + 1)
        if get_kodi_setting('filelists.showparentdiritems'):
            position = int(position + 1)
    try:
        control_list.selectItem(position)
    except:
        try:
            control_list.selectItem(position - 1)
        except:
            eh.exception(ErrorPriority.HIGH, 'Unable to Select Item')


def refresh():
    """
    Refresh and re-request data from server
    refresh watch status as we now mark episode and refresh list so it show real status not kodi_cached
    Allow time for the ui to reload
    """
    xbmc.executebuiltin('Container.Refresh')
    xbmc.sleep(int(plugin_addon.getSetting('refresh_wait')))


def message_box(title, text, text2=None, text3=None):
    xbmcgui.Dialog().ok(title, text, text2, text3)


def kodi_jsonrpc(method, params):
    try:
        request = '{"jsonrpc":"2.0","method":"%s","params":%s, "id": 1}' % (pyproxy.decode(method), json.dumps(params))
        return_data = xbmc.executeJSONRPC(request)
        result = json.loads(return_data)
        return result
    except:
        eh.exception(ErrorPriority.HIGH, 'Unable to Execute JSONRPC to Kodi')
        return None


def get_kodi_setting(setting):
    try:
        method = 'Settings.GetSettingValue'
        params = {'setting': setting}
        result = kodi_jsonrpc(method, params)
        if result is not None and 'result' in result and 'value' in result['result']:
            return result['result']['value']
    except:
        eh.exception(ErrorPriority.HIGH)
    return None


def set_sort_method(int_of_sort_method=0):
    """
    Ser given sort method
    :param int_of_sort_method: int parameter of sort method
    :return: set sort method
    """
    xbmc.executebuiltin('Container.SetSortMethod(' + str(int_of_sort_method) + ')')


def set_user_sort_method(content):
    method_for_sorting = Sorting.string2id.get(content, Sorting.none.container_id)
    if method_for_sorting == Sorting.none.container_id:
        return
    set_sort_method(method_for_sorting)
