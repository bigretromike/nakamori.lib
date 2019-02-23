#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import defaultdict

from nakamori_utils.globalvars import *
from nakamori_utils import nakamoritools as nt
from nakamori_utils import model_utils

from proxy.kodi_version_proxy import kodi_proxy
from proxy.python_version_proxy import python_proxy as pyproxy


class Directory(object):
    """
    A directory object, the base for Groups, Series, Episodes, etc
    """
    def __init__(self, json_node):
        """
        Create a directory object from a json node, containing only what is needed to form a ListItem
        :param json_node: the json response from things like api/serie
        :type json_node: Union[list,dict]
        """
        self.id = json_node.get('id', 0)
        self.name = model_utils.get_title(json_node)


class Filter(Directory):
    """
    A filter object, contains a unified method of representing a filter, with convenient converters
    """
    def __init__(self, json_node):
        """
        Create a filter object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/filter
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node)
        self.size = int(json_node.get('size', '0'))


class Group(Directory):
    """
    A group object, contains a unified method of representing a group, with convenient converters
    """
    def __init__(self, json_node):
        """
        Create a group object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/group
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node)
        self.actors = model_utils.get_cast_info(json_node)
        self.date = model_utils.get_date(json_node)


class Series(Directory):
    """
    A series object, contains a unified method of representing a series, with convenient converters
    """
    def __init__(self, json_node):
        """
        Create a series object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/serie
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node)
        self.season = json_node.get('season', '1')
        self.date = model_utils.get_date(json_node)
        self.actors = model_utils.get_cast_info(json_node)


class Episode(Directory):
    """
    An episode object, contains a unified method of representing an episode, with convenient converters
    """
    def __init__(self, json_node):
        """
        Create an episode object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/serie.eps[]
        :type json_node: Union[list,dict]
        """
        Directory.__init__(json_node)
        self.date = model_utils.get_date(json_node)
        self.tvdb_episode = json_node.get('season', '0x0')

        self.files = []
        try:
            for _file in json_node['files']:
                self.files.append(File(_file))
        except:
            pass

        if self.name is None:
            self.name = 'Episode ' + str(json_node.get('epnumber', '??'))

        self.watched = json_node.get("view", '0') != '0'
        self.year = nt.safe_int(json_node.get('year', ''))
        self.episode_number = nt.safe_int(json_node.get('epnumber', ''))
        self.rating = float(str(json_node.get('rating', '0')).replace(',', '.'))
        self.user_rating = float(str(json_node.get('UserRating', '0')).replace(',', '.'))
        self.overview = nt.remove_anidb_links(pyproxy.decode(json_node['summary']))
        self.votes = nt.safe_int(json_node.get('votes', ''))

        if str(json_node['eptype']) != "Special":
            season = str(json_node.get('season', '1'))
            if 'x' in season:
                season = season.split('x')[0]
                if season == '0':
                    season = '1'
        else:
            season = '0'
        self.season = nt.safe_int(season)

        thumb = ''
        if len(json_node["art"]["thumb"]) > 0:
            thumb = json_node["art"]["thumb"][0]["url"]
            if thumb is not None and ":" not in thumb:
                thumb = server + thumb
        fanart = ''
        if len(json_node["art"]["fanart"]) > 0:
            fanart = json_node["art"]["fanart"][0]["url"]
            if fanart is not None and ":" not in fanart:
                fanart = server + fanart
        banner = ''
        if len(json_node["art"]["banner"]) > 0:
            banner = json_node["art"]["banner"][0]["url"]
            if banner is not None and ":" not in banner:
                banner = server + banner

        self.fanart = fanart
        self. thumb = thumb
        self.banner = banner


class File(Directory):
    """
    A file object, contains a unified method of representing a json_node file, with convenient converters
    """
    def __init__(self, json_node):
        """
        Create a file object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/file
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node)
        # Check for empty duration from MediaInfo check fail and handle it properly
        tmp_duration = json_node.get('duration', '1')
        if tmp_duration != 1:
            duration = kodi_proxy.duration(tmp_duration)

        self.size = nt.safe_int(json_node.get('size', '0'))
        self.duration = duration
        self.resume_time = int(int(json_node.get('offset', '0')) / 1000)
        self.url = json_node["url"]

        video_streams = defaultdict(dict)
        audio_streams = defaultdict(dict)
        sub_streams = defaultdict(dict)

        # Information about streams inside json_node file
        if len(json_node.get("media", {})) > 0:
            self.video_streams = model_utils.get_video_streams(json_node['media'], video_streams)
            self.audio_streams = model_utils.get_audio_streams(json_node['media'], audio_streams)
            self.sub_streams = model_utils.get_sub_streams(json_node['media'], sub_streams)
