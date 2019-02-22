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


class Series(Directory):
    def __init__(self, json_node):
        """
        Create a series object from a json node, containing everything that is relevant to a ListItem
        :param json_node: the json response from things like api/serie
        :type json_node: Union[list,dict]
        """
        Directory.__init__(self, json_node)

