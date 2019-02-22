#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon

# The plugin object for nakamori.plugin
plugin_addon = xbmcaddon.Addon('plugin.video.nakamori')
service_addon = xbmcaddon.Addon('service.nakamori')
script_addon = xbmcaddon.Addon('script.module.nakamori')
plugin_home = xbmc.translatePath(plugin_addon.getAddonInfo('path'))

server = "http://" + plugin_addon.getSetting("ipaddress") + ":" + plugin_addon.getSetting("port")
