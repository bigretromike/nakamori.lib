# -*- coding: utf-8 -*-
from nakamori_utils.globalvars import *
from nakamori_utils import kodi_utils
from proxy.python_version_proxy import python_proxy as pyproxy
import error_handler as eh
import json
import xbmc
import xbmcgui

eigakan_url = plugin_addon.getSetting('ipEigakan')
eigakan_port = plugin_addon.getSetting('portEigakan')
eigakan_host = 'http://' + eigakan_url + ':' + eigakan_port

clientid = kodi_utils.get_device_id()

def probe_file(file_id, file_url):
    probe_url = eigakan_host + '/api/probe/%s/%s' % (clientid, file_id)
    post_data = '"file":"' + file_url + '"'
    streams = pyproxy.post_json(probe_url, post_data)
    streams = json.loads(streams)
    stream = streams.get('stream', {})
    audio = ''
    subs = ''
    if len(stream) > 0:
        audio = stream.get('audio', '')
        subs = stream.get('subs', '')
    return audio, subs

def pick_best_streams(audio_streams, subs_streams):
    a_index = -1
    s_index = -1
    subs_type = ''
    eh.spam('Processing streams a: %s; s: %s' % (audio_streams, subs_streams))
    if plugin_addon.getSetting('eigakan_manual_mode') == 'false':
        if len(audio_streams.split('\r')) == 1:
            a_index = audio_streams.split('|')[0]
        else:
            for a in audio_streams.split('\r'):
                a = a.split('|')
                for x in a:
                    if x == "*":
                        if a_index == -1:
                            a_index = a[0]
                        else:
                            a_index = -1
                            break

        if len(subs_streams.split('\r')) == 1:
            s_index = subs_streams.split('|')[0]
        else:
            for s in subs_streams.split('\r'):
                s = s.split('|')
                for x in s:
                    if x == "*":
                        if s_index == -1:
                            s_index = s[0]
                        else:
                            s_index = -1
                            break

    if not isinstance(a_index, int):
        a_index = -1

    if not isinstance(s_index, int):
        s_index = -1

    eh.spam('Pick_Best_Streams (after preference): "%s" "%s" "%s"' % (a_index, s_index, subs_type))
    # we use manual mode or we didn't have your preferred streams
    if a_index == -1 or s_index == -1:
        if a_index == -1:
            if audio_streams != '':  # less likely but check anyway
                a_option = audio_streams.split('\r')
                if len(a_option) == 1:
                    a_index = a_option[0].split('|')[0]
                else:
                    a_idx = xbmcgui.Dialog().select(plugin_addon.getLocalizedString(30178), a_option)
                    if a_idx > -1:
                        a_index = a_option[a_idx].split('|')[0]
                        if a_index == '':
                            a_index = -1
        if s_index == -1:
            if subs_streams != '':  # check for no data
                s_option = subs_streams.split('\r')
                if len(s_option) == 1:
                    s_index = s_option[0].split('|')[0]
                    subs_type = s_option[0].split('|')[1]
                else:
                    s_idx = xbmcgui.Dialog().select(plugin_addon.getLocalizedString(30179), s_option)
                    if s_idx > -1:
                        s_index = s_option[s_idx].split('|')[0]
                        if s_index == '':
                            s_index = -1
                        else:
                            subs_type = s_option[s_idx].split('|')[1]
                            if subs_type not in ['ass', 'aas', 'srt']:
                                subs_type = ''
            else:
                # TODO try to get external subtitles
                pass
    eh.spam('Pick_Best_Streams results: "%s" "%s" "%s"' % (a_index, s_index, subs_type))
    return a_index, s_index, subs_type

def is_fileid_added_to_transcoder(file_id):
    ask_for_queue = json.loads(pyproxy.get_json(eigakan_host + '/api/queue/status'))
    if ask_for_queue is None:
        ask_for_queue = {}
    # {"queue":{"queue":["6330","6330"],"subtitles":{"6330":{"status":"{'init'}"}},"videos":{}}}
    x = ask_for_queue.get('queue', {'queue': ''}).get('queue', [])
    for y in x:
        if int(y) == int(file_id):
            return True
    return False