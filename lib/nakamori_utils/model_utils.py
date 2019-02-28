# -*- coding: utf-8 -*-
from collections import defaultdict

from nakamori_utils import nakamoritools as nt
from nakamori_utils.globalvars import *
from proxy.python_version_proxy import python_proxy as pyproxy


def get_tags(tag_node):
    """
    Get the tags from the new style
    Args:
        tag_node: node containing group

    Returns: a string of all of the tags formatted

    """
    try:
        if tag_node is None:
            return ''
        if len(tag_node) > 0:
            temp_genres = []
            for tag in tag_node:
                if isinstance(tag, str) or isinstance(tag, unicode):
                    temp_genres.append(tag)
                else:
                    temp_genre = pyproxy.decode(tag["tag"]).strip()
                    temp_genres.append(temp_genre)
            temp_genre = " | ".join(temp_genres)
            return temp_genre
        else:
            return ''
    except Exception as exc:
        nt.error('util.error generating tags', str(exc))
        return ''


def get_cast_and_role_new(data):
    """
    Get cast from the json and arrange in the new setCast format
    :param data: json node containing 'roles'
    :type data: list
    :return: a list of dictionaries for the cast
    :rtype: List[Dict[str,str]]
    """
    result_list = []
    if data is not None and len(data) > 0:
        for char in data:
            char_charname = char.get("character", "")
            char_seiyuuname = char.get("staff", "")
            char_seiyuupic = server + char.get("character_image", "")

            # only add it if it has data
            # reorder these to match the convention (Actor is cast, character is role, in that order)
            if len(char_charname) != 0:
                actor = {
                    'name':         char_seiyuuname,
                    'role':         char_charname,
                    'thumbnail':    char_seiyuupic
                }
                result_list.append(actor)
        if len(result_list) == 0:
            return None
        return result_list
    return None


def get_cast_and_role(data):
    """
    Get cast from the json and arrange in the new setCast format
    Args:
        data: json node containing 'roles'

    Returns: a list of dictionaries for the cast
    """
    result_list = []
    if data is not None and len(data) > 0:
        for char in data:
            char_charname = char["role"]
            char_seiyuuname = char['name']
            char_seiyuupic = char["rolepic"]

            # only add it if it has data
            # reorder these to match the convention (Actor is cast, character is role, in that order)
            if len(char_charname) != 0:
                actor = {
                    'name':         char_seiyuuname,
                    'role':         char_charname,
                    'thumbnail':    char_seiyuupic
                }
                result_list.append(actor)
        if len(result_list) == 0:
            return None
        return result_list
    return None


def convert_cast_and_role_to_legacy(list_of_dicts):
    """
    Convert standard cast_and_role to version supported by Kodi16 and lower
    :param list_of_dicts:
    :return: list
    """

    result_list = []
    list_cast = []
    list_cast_and_role = []
    if list_of_dicts is not None and len(list_of_dicts) > 0:
        for actor in list_of_dicts:
            seiyuu = actor.get('name', '')
            role = actor.get('role', '')
            if len(role) != 0:
                list_cast.append(role)
                if len(seiyuu) != 0:
                    list_cast_and_role.append((seiyuu, role))
        result_list.append(list_cast)
        result_list.append(list_cast_and_role)
    return result_list


def is_type_list(title):
    """
    Returns if a title matches an episode type
    :param title:
    :return:
    """
    if title == 'ova' or title == 'ovas':
        return True
    if title == 'episode' or title == 'episodes':
        return True
    if title == 'special' or title == 'specials':
        return True
    if title == 'parody' or title == 'parodies':
        return True
    if title == 'credit' or title == 'credits':
        return True
    if title == 'trailer' or title == 'trailers':
        return True
    if title == 'other' or title == 'others':
        return True
    return False


def get_title(data, lang=None, title_type=None):
    """
    Get the title based on settings
    :param data: json node containing the title
    :return: string of the desired title
    :rtype: str

    """
    try:
        if 'titles' not in data or plugin_addon.getSetting('use_server_title') == 'true':
            return pyproxy.decode(data.get('name', ''))
        # xbmc.log(data.get('title', 'Unknown'))
        title = pyproxy.decode(data.get('name', '').lower())
        if is_type_list(title):
            return pyproxy.decode(data.get('name', ''))

        if lang is None:
            lang = plugin_addon.getSetting("displaylang")
        if title_type is None:
            title_type = plugin_addon.getSetting("title_type")

        try:
            for title_tag in data.get("titles", []):
                title = pyproxy.decode(title_tag.get("Title", ""))
                if pyproxy.decode(title_tag.get("Title", "")) == "":
                    continue

                if title_tag.get("Language", "").lower() == lang.lower():
                    # does it match the proper type
                    if title_tag.get("Type", "").lower() == title_type.lower():
                        return title
                    # fallback on language any title
                    if title_tag.get("Type", "").lower() != 'short':
                        return title
                    # fallback on x-jat main title
                    if title_tag.get("Type", "").lower() == 'main' and title_tag.get("Language", "").lower() == "x-jat":
                        return title
            # fallback on directory title
            return pyproxy.decode(data.get('name', ''))
        except Exception as ex1:
            nt.error('util.error thrown on getting title', str(ex1))
            return pyproxy.decode(data.get('name', ''))
    except Exception as ex2:
        nt.error("get_title Exception", str(ex2))
        return 'util.error'


def set_watch_flag(extra_data, details):
    """
    Set the flag icon for the list item to the desired state based on watched episodes
    Args:
        extra_data: the extra_data dict
        details: the details dict
    """
    # Set up overlays for watched and unwatched episodes
    if extra_data['WatchedEpisodes'] == 0:
        details['playcount'] = 0
    elif extra_data['UnWatchedEpisodes'] == 0:
        details['playcount'] = 1
    else:
        extra_data['partialTV'] = 1


def video_file_information(node, detail_dict):
    """
    Process given 'node' and parse it to create proper file information dictionary 'detail_dict'
    :param node: node that contains file
    :param detail_dict: dictionary for output
    :return: dict
    """
    detail_dict['VideoStreams'] = get_video_streams(node)
    detail_dict['AudioStreams'] = get_audio_streams(node)
    detail_dict['SubStreams'] = get_sub_streams(node)


def get_video_streams(node):
    """
    Process given 'node' and parse it to create a Kodi friendly format
    :param node: node that contains file
    :return: dict
    """
    streams = defaultdict(dict)
    if "videos" in node:
        for stream_node in node["videos"]:
            stream_info = node["videos"][stream_node]
            if not isinstance(stream_info, dict):
                continue
            stream_id = int(stream_info["Index"])
            streams[stream_id]['VideoCodec'] = stream_info['Codec']
            streams['xVideoCodec'] = stream_info['Codec']
            streams[stream_id]['width'] = stream_info['Width']
            if 'width' not in streams:
                streams['width'] = stream_info['Width']
            streams['xVideoResolution'] = str(stream_info['Width'])
            streams[stream_id]['height'] = stream_info['Height']
            if 'height' not in streams:
                streams['height'] = stream_info['Height']
                streams[stream_id]['aspect'] = round(int(streams['width']) / int(streams['height']), 2)
            streams['xVideoResolution'] += "x" + str(stream_info['Height'])
            streams[stream_id]['duration'] = int(round(float(stream_info.get('Duration', 0)) / 1000, 0))
    return streams


def get_audio_streams(node):
    """
    Process given 'node' and parse it to create a Kodi friendly format
    :param node: node that contains file
    :return: dict
    """
    streams = defaultdict(dict)
    if "audios" in node:
        for stream_node in node["audios"]:
            stream_info = node["audios"][stream_node]
            if not isinstance(stream_info, dict):
                continue
            stream_id = int(stream_info["Index"])
            streams[stream_id]['AudioCodec'] = stream_info["Codec"]
            streams['xAudioCodec'] = streams[stream_id]['AudioCodec']
            streams[stream_id]['AudioLanguage'] = stream_info["LanguageCode"] if "LanguageCode" in stream_info \
                else "unk"
            streams[stream_id]['AudioChannels'] = int(stream_info["Channels"]) if "Channels" in stream_info else 1
            streams['xAudioChannels'] = nt.safe_int(streams[stream_id]['AudioChannels'])
    return streams


def get_sub_streams(node):
    """
    Process given 'node' and parse it to create a Kodi friendly format
    :param node: node that contains file
    :return: dict
    """
    streams = defaultdict(dict)
    if "subtitles" in node:
        i = 0
        for stream_node in node["subtitles"]:
            stream_info = node["subtitles"][stream_node]
            if not isinstance(stream_info, dict):
                continue
            try:
                stream_id = int(stream_node)
            except:
                stream_id = i
            streams[stream_id]['SubtitleLanguage'] = stream_info["LanguageCode"] if "LanguageCode" in stream_info \
                else "unk"
            i += 1
    return streams


def get_cast_info(json_node):
    """
    Extracts and processes cast and staff info
    :param json_node: json response
    :return: list of cast objects { 'name': str, 'role': str, 'thumbnail': str (url) }
    :rtype:
    """
    if 'roles' in json_node:
        cast_nodes = json_node.get("roles", {})
        if len(cast_nodes) > 0:
            if cast_nodes[0].get("character", "") != "":
                result_list = get_cast_and_role_new(cast_nodes)
            else:
                result_list = get_cast_and_role(cast_nodes)
            return result_list


def get_airdate(json_node):
    """
    get the air from json, removing default value
    :param json_node: the json response
    :return: str date or ''
    :rtype: str
    """
    air = json_node.get('air', '')
    if air == '0001-01-01' or air == '01-01-0001':
        air = ''
    return air


def get_date(date):
    """
    get date format from air date
    :param date: 'air'
    :type date: str
    :return:
    """
    temp_date = date.split('-')
    if len(temp_date) == 3:  # format is 2016-01-24, we want it 24.01.2016
        return temp_date[1] + '.' + temp_date[2] + '.' + temp_date[0]
    return None


def get_sort_name(episode):
    """
    gets the sort name from an episode
    :param episode:
    :type episode: Episode
    :return:
    """
    return str(episode.episode_number).zfill(3) + ' ' + episode.name


# noinspection Duplicates
def set_stream_info(listitem, file):
    """
    :param listitem: the ListItem to set data
    :type listitem: ListItem
    :param file: the file object to pull data from
    :type file: File
    """
    listitem.setProperty('TotalTime', str(file.duration))

    video = file.video_streams
    if video is not None and len(video) > 0:
        video = video[0]
        listitem.addStreamInfo('video', video)
        listitem.setProperty('VideoResolution', str(video.get('xVideoResolution', '')))
        listitem.setProperty('VideoCodec', video.get('xVideoCodec', ''))
        listitem.setProperty('VideoAspect', str(video.get('aspect', '')))

    audio = file.audio_streams
    if audio is not None and len(audio) > 0:
        listitem.setProperty('AudioCodec', audio.get('xAudioCodec', ''))
        listitem.setProperty('AudioChannels', str(audio.get('xAudioChannels', '')))
        for stream in audio:
            if not isinstance(audio[stream], dict):
                continue
            listitem.setProperty('AudioCodec.' + str(stream), str(audio[stream]['AudioCodec']))
            listitem.setProperty('AudioChannels.' + str(stream), str(audio[stream]['AudioChannels']))
            audio_codec = dict()
            audio_codec['codec'] = str(audio[stream]['AudioCodec'])
            audio_codec['channels'] = int(audio[stream]['AudioChannels'])
            audio_codec['language'] = str(audio[stream]['AudioLanguage'])
            listitem.addStreamInfo('audio', audio_codec)

    subs = file.sub_streams
    if subs is not None and len(subs) > 0:
        for stream2 in subs:
            listitem.setProperty('SubtitleLanguage.' + str(stream2), str(subs[stream2]['SubtitleLanguage']))
            subtitle_codec = dict()
            subtitle_codec['language'] = str(subs[stream2]['SubtitleLanguage'])
            listitem.addStreamInfo('subtitle', subtitle_codec)