# -*- coding: utf-8 -*-
plugin = 'plugin://plugin.video.nakamori%s'
run = 'RunPlugin(%s)' % plugin


def url_play_video(ep_id=0, file_id=0, runplugin=False, party_mode=False):
    url = '/episode/%d/file/%s/play/' % (ep_id, file_id)
    if party_mode:
        url = '/episode/%d/file/%s/play/party/' % (ep_id, file_id)
    if runplugin:
        return run % url
    return plugin % url


def url_play_video_without_marking(ep_id, file_id, runplugin=False):
    url = '/episode/%d/file/%d/play_without_marking/' % (ep_id, file_id)
    if runplugin:
        return run % url
    return plugin % url


def url_transcode_play_video(ep_id, file_id=0, runplugin=False):
    url = '/episode/%d/file/%d/transcode/' % (ep_id, file_id)
    if runplugin:
        return run % url
    return plugin % url


def url_direct_play_video(ep_id, file_id=0, runplugin=False):
    url = '/episode/%d/file/%d/directplay/' % (ep_id, file_id)
    if runplugin:
        return run % url
    return plugin % url


def url_resume_video(ep_id, file_id, runplugin=False):
    url = '/episode/%d/file/%d/resume/' % (ep_id, file_id)
    if runplugin:
        return run % url
    return plugin % url


def url_show_unsorted_menu(runplugin=False):
    url = '/menu/filter/unsorted/'
    if runplugin:
        return run % url
    return plugin % url


def url_show_group_menu(group_id, filter_id, runplugin=False):
    url = '/menu/group/%d/filterby/%d/' % (group_id, filter_id)
    if runplugin:
        return run % url
    return plugin % url


def url_show_series_menu(series_id, runplugin=False):
    url = '/menu/series/%d/' % series_id
    if runplugin:
        return run % url
    return plugin % url


def url_show_series_episode_types_menu(series_id, episode_type, runplugin=False):
    url = '/menu/series/%d/type/%s/' % (series_id, episode_type)
    if runplugin:
        return run % url
    return plugin % url


def url_show_filter_menu(filter_id, runplugin=False):
    url = '/menu/filter/%d/' % filter_id
    if runplugin:
        return run % url
    return plugin % url


def url_show_folder_menu(folder_id, runplugin=False):
    url = '/menu/folder/%d/' % folder_id
    if runplugin:
        return run % url
    return plugin % url
