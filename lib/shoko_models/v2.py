#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nakamori_utils import model_utils


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
        self.actors = model_utils.get_cast_info(json_node)


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


class Episode(Directory):
    """
    An episode object, contains a unified method of representing an episode, with convenient converters
    """
    def __init__(self, json_node):
        """
        Create an episode object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/episode
        :type json_node: Union[list,dict]
        """
        Directory.__init__(json_node)


class File(Directory):
    """
    A file object, contains a unified method of representing a video file, with convenient converters
    """
    def __init__(self, json_node):
        """
        Create a file object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/file
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node)
