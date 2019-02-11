#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xbmcaddon

# The plugin object for nakamori.plugin
plugin_addon = xbmcaddon.Addon('plugin.video.nakamori')
service_addon = xbmcaddon.Addon('service.nakamori')
script_addon = xbmcaddon.Addon('script.module.nakamori')

server = "http://" + plugin_addon.getSetting("ipaddress") + ":" + plugin_addon.getSetting("port")
