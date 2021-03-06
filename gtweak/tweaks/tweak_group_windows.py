# This file is part of gnome-tweak-tool.
#
# Copyright (c) 2011 John Stowers
#
# gnome-tweak-tool is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gnome-tweak-tool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gnome-tweak-tool.  If not, see <http://www.gnu.org/licenses/>.

import gtweak
from gtweak.gshellwrapper import GnomeShellFactory
from gtweak.tweakmodel import TWEAK_GROUP_WINDOWS
from gtweak.widgets import ListBoxTweakGroup, GSettingsComboEnumTweak, GSettingsComboTweak, GSettingsSwitchTweak, Title, GSettingsSwitchTweakValue

_shell = GnomeShellFactory().get_shell()
_shell_loaded = _shell is not None
            
class ShowWindowButtons(GSettingsSwitchTweakValue):

    def __init__(self, name, value, **options):
        self.value = value
        GSettingsSwitchTweakValue.__init__(self,
                                           name,
                                           "org.gnome.desktop.wm.preferences",
                                           "button-layout",
                                           loaded=_shell_loaded,
                                           **options)
        self.values=[':close',':minimize,close', ':maximize,close', ':minimize,maximize,close']
        
    def get_active(self):
        return self.value in self.settings.get_string(self.key_name)
            
    def set_active(self, v):
        val = self.settings.get_string(self.key_name)
        if v:
            id = self.values.index(val)
            if id == 0:
                val = val.replace(":", ":"+self.value+",")
            else:
                val= self.values[len(self.values)-1]
        else:
            val = val.replace(self.value+",", "")

        self.settings.set_string(self.key_name, val)

TWEAK_GROUPS = [ 
    ListBoxTweakGroup(TWEAK_GROUP_WINDOWS,
        GSettingsSwitchTweak(_("Attached Modal Dialogs"),"org.gnome.mutter", "attach-modal-dialogs"),
        GSettingsSwitchTweak(_("Automatically Raise Windows"),"org.gnome.desktop.wm.preferences", "raise-on-click"),
        GSettingsSwitchTweak(_("Resize with Secondary-click"),"org.gnome.desktop.wm.preferences", "resize-with-right-button"),
        GSettingsComboTweak(_("Window Action Key"),
                        "org.gnome.desktop.wm.preferences",
                        "mouse-button-modifier",
                        [("disabled", _("Disabled")), ("<Alt>", "Alt"), ("<Super>", "Super")]),
        GSettingsComboEnumTweak(_("Focus Mode"), "org.gnome.desktop.wm.preferences", "focus-mode"),
        Title(_("Titlebar Actions"), "", uid="title-titlebar-actions"),
        GSettingsComboEnumTweak(_("Double-click"),"org.gnome.desktop.wm.preferences", "action-double-click-titlebar"),
        GSettingsComboEnumTweak(_("Middle-click"),"org.gnome.desktop.wm.preferences", "action-middle-click-titlebar"),
        GSettingsComboEnumTweak(_("Secondary-click"),"org.gnome.desktop.wm.preferences", "action-right-click-titlebar"),
        Title(_("Titlebar Buttons"), "", uid="title-theme"),
        ShowWindowButtons(_("Maximize"), "maximize"),
        ShowWindowButtons(_("Minimize"), "minimize"),
    )
]

