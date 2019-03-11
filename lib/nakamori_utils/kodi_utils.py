# -*- coding: utf-8 -*-
import json
import sys

import xbmcgui

from nakamori_utils import nakamoritools as nt
from nakamori_utils.globalvars import *
from proxy.python_version_proxy import python_proxy as pyproxy

try:
    from sqlite3 import dbapi2 as database
except:
    # noinspection PyUnresolvedReferences
    from pysqlite2 import dbapi2 as database


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
        nt.error('set_window_heading Exception', str(e))
        window_obj.clearProperty('heading')
    try:
        window_obj.setProperty('heading2', str(window_name))
    except Exception as e:
        nt.error('set_window_heading2 Exception', str(e))
        window_obj.clearProperty('heading2')
        

def play_continue_item():
    """
    Move to next item that was not marked as watched
    Essential information are query from Parameters via util lib
    """
    params = pyproxy.parse_parameters(sys.argv[2])
    if 'offset' in params:
        offset = params['offset']
        pos = int(offset)
        if pos == 1:
            xbmcgui.Dialog().ok(plugin_addon.getLocalizedString(30182), plugin_addon.getLocalizedString(30183))
        else:
            wind = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            control_id = wind.getFocusId()
            control_list = wind.getControl(control_id)
            nt.move_position_on_list(control_list, pos)
            xbmc.sleep(1000)
    else:
        pass


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


def import_folder_list():
    """
    Create DialogBox with folder list to pick if there
    :return: int (vl of selected folder)
    """
    pick_folder = []
    get_id = []
    import_list = json.loads(nt.get_json(nt.server + '/api/folder/list'))
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


def fix_mark_watch_in_kodi_db():
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


def clear_image_cache_in_kodi_db():
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
