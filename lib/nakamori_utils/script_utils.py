# THIS IS A SUPPLEMENTARY FILE UNTIL WE GET THE ROUTING REGISTRY
# Yes this was super tedious and the reason that I want a routing registry
import xbmc
from proxy.python_version_proxy import python_proxy as pyproxy
from nakamori_utils.globalvars import *

run = 'RunScript(script.module.nakamori,%s)'


def url_calendar(when=0, page=0):
    url = '/calendar/%i/%i/' % (when, page)
    return run % url


def url_ac_calendar(when=0, page=0):
    url = '/ac_calendar/%i/%i/' % (when, page)
    return run % url


def url_cr_calendar(when=0, page=0):
    url = '/cr_calendar/%i/%i/' % (when, page)
    return run % url


def calendar(when=0, page=0):
    url = url_calendar(when, page)
    xbmc.executebuiltin(url)


def ac_calendar(when=0, page=0):
    url = url_ac_calendar(when, page)
    xbmc.executebuiltin(url)


def cr_calendar(when=0, page=0):
    url = url_cr_calendar(when, page)
    xbmc.executebuiltin(url)


def url_series_info(id=0, aid=0):
    if aid > 0:
        url = '/seriesinfo/aid/%s/' % aid
    else:
        url = '/seriesinfo/%s/' % id
    return run % url


def series_info(id=0, aid=0):
    url = url_series_info(id, aid)
    xbmc.executebuiltin(url)


def arbiter(wait, arg):
    url = '/arbiter/%i/%s' % (wait, arg)
    url = run % url
    xbmc.executebuiltin(url)


def url_wizard_connection():
    url = '/dialog/wizard/connection'
    return run % url


def wizard_connection():
    url = url_wizard_connection()
    xbmc.executebuiltin(url, True)


def url_wizard_login():
    url = '/dialog/wizard/login'
    return run % url


def wizard_login():
    url = url_wizard_login()
    xbmc.executebuiltin(url, True)


def url_clearcache():
    url = '/calendar/clear_cache'
    return run % url


def clearcache():
    url = url_clearcache()
    xbmc.executebuiltin(url)


def url_whats_new():
    url = '/dialog/whats_new'
    return run % url


def whats_new():
    url = url_whats_new()
    xbmc.executebuiltin(url)


def url_settings():
    url = '/dialog/settings'
    return run % url


def url_script_settings():
    url = '/dialog/script_settings'
    return run % url


def url_service_settings():
    url = '/dialog/service_settings'
    return run % url


def settings():
    url = url_settings()
    xbmc.executebuiltin(url)


def url_shoko_menu():
    url = '/dialog/shoko'
    return run % url


def shoko_menu():
    url = url_shoko_menu()
    xbmc.executebuiltin(url)


def url_remove_search_term(query):
    url = '/search/remove/%s' % pyproxy.quote(pyproxy.quote(query))
    return run % url


def remove_search_term(query):
    url = url_remove_search_term(query)
    xbmc.executebuiltin(url, True)


def url_clear_search_terms():
    url = '/search/clear'
    return run % url


def clear_search_terms():
    url = url_clear_search_terms()
    xbmc.executebuiltin(url, True)


def url_clear_listitem_cache():
    url = '/kodi/clear_listitem_cache'
    return run % url


def clear_listitem_cache():
    url = url_clear_listitem_cache()
    xbmc.executebuiltin(url, True)


def url_clear_image_cache():
    url = '/kodi/clear_image_cache'
    return run % url


def clear_image_cache():
    url = url_clear_image_cache()
    xbmc.executebuiltin(url, True)


def url_refresh():
    url = '/refresh'
    return run % url


def refresh():
    url = url_refresh()
    xbmc.executebuiltin(url, True)


def url_cohesion():
    url = '/cohesion'
    return run % url


def cohesion():
    url = url_cohesion()
    xbmc.executebuiltin(url)


def url_show_series_vote_dialog(series_id):
    url = '/dialog/vote_series/%i/' % series_id
    return run % url


def show_series_vote_dialog(series_id):
    url = url_show_series_vote_dialog(series_id)
    xbmc.executebuiltin(url)


def url_show_episode_vote_dialog(ep_id):
    url = '/dialog/vote_episode/%i/' % ep_id
    return run % url


def show_episode_vote_dialog(ep_id):
    url = url_show_episode_vote_dialog(ep_id)
    xbmc.executebuiltin(url)


def url_vote_for_series(series_id):
    url = '/series/%i/vote' % series_id
    return run % url


def vote_for_series(series_id, wait=False):
    url = url_vote_for_series(series_id)
    xbmc.executebuiltin(url, wait)


def url_vote_for_episode(ep_id):
    url = '/episode/%i/vote' % ep_id
    return run % url


def vote_for_episode(ep_id, wait=False):
    url = url_vote_for_episode(ep_id)
    xbmc.executebuiltin(url, wait)


def url_file_list(ep_id):
    url = '/ep/%i/file_list' % ep_id
    return run % url


def file_list(ep_id):
    url = url_file_list(ep_id)
    xbmc.executebuiltin(url, True)


def url_rescan_file(file_id):
    url = '/file/%i/rescan' % file_id
    return run % url


def rescan_file(file_id):
    url = url_rescan_file(file_id)
    xbmc.executebuiltin(url)


def url_rehash_file(file_id):
    url = '/file/%i/rehash' % file_id
    return run % url


def rehash_file(file_id):
    url = url_rehash_file(file_id)
    xbmc.executebuiltin(url)


def url_episode_watched_status(ep_id, watched):
    url = '/episode/%i/set_watched/%s' % (ep_id, watched)
    return run % url


def set_episode_watched_status(ep_id, watched, wait=True):
    url = url_episode_watched_status(ep_id, watched)
    xbmc.executebuiltin(url, wait)


def url_series_watched_status(series_id, watched):
    url = '/series/%i/set_watched/%s' % (series_id, watched)
    return run % url


def set_series_watched_status(series_id, watched, wait=False):
    url = url_series_watched_status(series_id, watched)
    xbmc.executebuiltin(url, wait)


def url_group_watched_status(group_id, watched):
    url = '/group/%i/set_watched/%s' % (group_id, watched)
    return run % url


def set_group_watched_status(group_id, watched, wait=False):
    url = url_group_watched_status(group_id, watched)
    xbmc.executebuiltin(url, wait)


def url_move_to_item(index):
    url = '/menu/episode/move_to_item/%i/' % index
    return run % url


def move_to_item(index):
    url = url_move_to_item(index)
    xbmc.executebuiltin(url)


def url_probe_file(file_id):
    url = '/file/%i/probe' % file_id
    return run % url


def url_probe_episode(ep_id):
    url = '/episode/%i/probe' % ep_id
    return run % url


def url_transcode_file(file_id):
    url = '/file/%i/transcode' % file_id
    return run % url


def url_transcode_episode(ep_id):
    url = '/episode/%i/transcode' % ep_id
    return run % url


def url_add_favorite(s_id):
    url = '/favorite/%i/add' % s_id
    return run % url


def add_favorite(s_id):
    url = url_add_favorite(s_id)
    xbmc.executebuiltin(url)


def url_remove_favorite(s_id):
    url = '/favorite/%i/remove' % s_id
    return run % url


def remove_favorite(s_id):
    url = url_remove_favorite(s_id)
    xbmc.executebuiltin(url)


def url_add_bookmark(s_id):
    url = '/bookmark/%s/add' % s_id
    return run % url


def add_bookmark(s_id):
    url = url_add_bookmark(s_id)
    xbmc.executebuiltin(url)


def url_remove_bookmark(s_id):
    url = '/bookmark/%s/remove' % s_id
    return run % url


def remove_bookmark(s_id):
    url = url_remove_bookmark(s_id)
    xbmc.executebuiltin(url)


def url_clear_favorite():
    url = '/favorite/clear'
    return run % url


def clear_favorite():
    url = url_clear_favorite()
    xbmc.executebuiltin(url)


def log_setsuzoku(category, action, event):
    url = '/log/%s/%s/%s' % (category, action, event)
    xbmc.executebuiltin(run % url)


def url_move_to_item_and_enter(index):
    url = '/menu/move_to_item_and_enter/%i/' % index
    return run % url


def move_to_item_and_enter(index):
    url = url_move_to_item_and_enter(index)
    xbmc.executebuiltin(url)


def url_command_queue(role, command):
    url = '/queue/%s/%s/' % (role, command)
    return run % url


def command_queue(role, command):
    url = url_command_queue(role, command)
    xbmc.executebuiltin(url)


def url_folder_scan(id):
    url = '/folder/%s/scan/' % id
    return run % url


def folder_scan(id):
    url = url_folder_scan(id)
    xbmc.executescript(url)


def url_shoko_scandropfolder():
    url = '/shoko/scandrop/'
    return run % url


def url_shoko_statusupdate():
    url = '/shoko/statusupdate/'
    return run % url


def url_shoko_mediainfoupdate():
    url = '/shoko/mediainfoupdate/'
    return run % url


def url_shoko_rescanunlinked():
    url = '/shoko/rescanunlinked/'
    return run % url


def url_shoko_rehashunlinked():
    url = '/shoko/rehashunlinked/'
    return run % url


def url_shoko_rescanmanuallinks():
    url = '/shoko/rescanmanuallinks/'
    return run % url


def url_shoko_rehashmanuallinks():
    url = '/shoko/rehashmanuallinks/'
    return run % url


def url_shoko_runimport():
    url = '/shoko/runimport/'
    return run % url


def url_shoko_removemissing():
    url = '/shoko/removemissing/'
    return run % url


def url_calendar_refresh():
    url = '/shoko/calendarrefresh/'
    return run % url


def url_playlist_series(series_id):
    url = '/series/%i/playlist/' % series_id
    return run % url


def playlist_series(series_id, wait=False):
    url = url_playlist_series(series_id)
    xbmc.executebuiltin(url, wait)


def url_install_webui():
    url = '/shoko/webui/install/'
    return run % url


def url_stable_webui():
    url = '/shoko/webui/update/'
    return run % url


def url_unstable_webui():
    url = '/shoko/webui/unstable/'
    return run % url
