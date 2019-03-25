#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

import xbmc
import xbmcaddon

# in kodi 18, this will just work, but in kodi <18, these are regenerated each time this is called.
# We can make this an object belonging to nakamori.service, but we may need to make script and plugin
# dependent on service if that is the case

# The plugin object for nakamori.plugin
plugin_addon = xbmcaddon.Addon('plugin.video.nakamori')
plugin_version = plugin_addon.getAddonInfo('version')
plugin_home = xbmc.translatePath(plugin_addon.getAddonInfo('path'))
plugin_img_path = os.path.join(xbmcaddon.Addon(plugin_addon.getSetting('icon_pack')).getAddonInfo('path'), 'resources', 'media')

service_addon = xbmcaddon.Addon('service.nakamori')
script_addon = xbmcaddon.Addon('script.module.nakamori')

server = 'http://' + plugin_addon.getSetting('ipaddress') + ':' + plugin_addon.getSetting('port')

tag_setting_flags = 0
tag_setting_flags |= 0b0000001 if plugin_addon.getSetting('hideMiscTags') == 'true' else 0
tag_setting_flags |= 0b0000010 if plugin_addon.getSetting('hideArtTags') == 'true' else 0
tag_setting_flags |= 0b0000100 if plugin_addon.getSetting('hideSourceTags') == 'true' else 0
tag_setting_flags |= 0b0001000 if plugin_addon.getSetting('hideUsefulMiscTags') == 'true' else 0
tag_setting_flags |= 0b0010000 if plugin_addon.getSetting('hideSpoilerTags') == 'true' else 0
tag_setting_flags |= 0b0100000 if plugin_addon.getSetting('hideSettingTags') == 'true' else 0
tag_setting_flags |= 0b1000000 if plugin_addon.getSetting('hideProgrammingTags') == 'true' else 0
