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
from __future__ import print_function

import os.path
import subprocess

from gi.repository import Gtk, GLib, Gio

from gtweak.tweakmodel import Tweak
from gtweak.widgets import ListBoxTweakGroup, UI_BOX_SPACING
from gtweak.utils import AutostartManager

def _list_header_func(row, before, user_data):
    if before and not row.get_header():
        row.set_header (Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

class _AppChooser(Gtk.Dialog):
    def __init__(self, main_window, running_exes):
        Gtk.Dialog.__init__(self)

        self._running = {}
        self._all = {}

        lb = Gtk.ListBox()
        lb.props.margin = 5
        lb.set_sort_func(self._sort_apps, None)
        lb.set_header_func(_list_header_func, None)

        apps = Gio.app_info_get_all()
        for a in apps:
            if a.should_show():
                running = a.get_executable() in running_exes
                w = self._build_widget(
                        a,
                        'running' if running else '')
                lb.add(w)
                self._all[w] = a
                self._running[w] = running

        sw = Gtk.ScrolledWindow()
        sw.props.hscrollbar_policy = Gtk.PolicyType.NEVER
        sw.add(lb)

        self.get_content_area().pack_start(sw, True, True, 0)
        self.set_modal(True)
        self.set_transient_for(main_window)
        self.set_size_request(400,300)

    def _sort_apps(self, a, b, user_data):
        if self._running.get(a) and not self._running.get(b):
            return -1
        return 1

    def _build_widget(self, a, extra):
        row = Gtk.ListBoxRow()
        g = Gtk.Grid()
        img = Gtk.Image.new_from_gicon(a.get_icon(),Gtk.IconSize.DIALOG)
        g.attach(img, 0, 0, 1, 1)
        img.props.hexpand = False
        lbl = Gtk.Label(a.get_name(), xalign=0)
        g.attach_next_to(lbl,img,Gtk.PositionType.RIGHT,1,1)
        lbl.props.hexpand = True
        lbl.props.halign = Gtk.Align.START
        lbl.props.vexpand = False
        lbl.props.valign = Gtk.Align.CENTER
        if extra:
            g.attach_next_to(
                Gtk.Label(extra),
                lbl,Gtk.PositionType.RIGHT,1,1)
        row.add(g)
        #row.get_style_context().add_class('tweak-white')
        return row

class _StartupTweak(Gtk.ListBoxRow, Tweak):
    def __init__(self, df, **options):

        Gtk.ListBoxRow.__init__(self)
        Tweak.__init__(self, 
                        df.get_name(),
                        df.get_description(),
                        **options)
        
        grid = Gtk.Grid(column_spacing=10)

        img = Gtk.Image.new_from_gicon(df.get_icon(),Gtk.IconSize.DIALOG)
        grid.attach(img, 0, 0, 1, 1)

        lbl = Gtk.Label(df.get_name(), xalign=0.0)
        grid.attach_next_to(lbl,img,Gtk.PositionType.RIGHT,1,1)
        lbl.props.hexpand = True
        lbl.props.halign = Gtk.Align.START

        btn = Gtk.Button("Remove")
        grid.attach_next_to(btn,lbl,Gtk.PositionType.RIGHT,1,1)
        btn.props.vexpand = False
        btn.props.valign = Gtk.Align.CENTER

        self.add(grid)

        self.props.margin = 5
        self.get_style_context().add_class('tweak-white')
    
class AutostartListBoxTweakGroup(ListBoxTweakGroup):
    def __init__(self):
        tweaks = []

        files = AutostartManager.get_user_autostart_files()
        for f in files:
            df = Gio.DesktopAppInfo.new_from_filename(f)
            tweaks.append( _StartupTweak(df) )

        ListBoxTweakGroup.__init__(self,
            "Startup Applications",
            *tweaks,
            css_class='tweak-group-white')
        self.set_header_func(_list_header_func, None)
        
        btn = Gtk.Button("")
        btn.get_style_context().remove_class("button")
        img = Gtk.Image()
        img.set_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)
        btn.set_image(img)
        btn.props.always_show_image = True
        btn.connect("clicked", self._on_add_clicked)
        #b.props.hexpand = True
        #b.props.vexpand = True
        self.add(btn)

    def _on_add_clicked(self, btn):
        a = _AppChooser(
                self.main_window,
                set(self._get_running_executables()))
        a.show_all()
        a.run()
        a.destroy()

    def _get_running_executables(self):
        exes = []
        cmd = subprocess.Popen([
                    'ps','-e','-w','-w','-U',
                    os.getlogin(),'-o','cmd'],
                    stdout=subprocess.PIPE)
        out = cmd.communicate()[0]
        for l in out.split('\n'):
            exe = l.split(' ')[0]
            if exe and exe[0] != '[': #kernel process
                exes.append( os.path.basename(exe) )

        return exes




TWEAK_GROUPS = [
    AutostartListBoxTweakGroup(),
]
