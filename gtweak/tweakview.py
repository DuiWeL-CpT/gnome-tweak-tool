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

import os.path
import logging
import datetime

from gi.repository import Gtk, Gdk, GObject

import gtweak.tweakmodel
from gtweak.tweakmodel import TweakModel
from gtweak.utils import Notification
from gtweak.widgets import Title

DEFAULT_TWEAKGROUP = gtweak.tweakmodel.TWEAK_GROUP_APPEARANCE
WIDGET_SORT_ORDER = (Gtk.Switch, Gtk.SpinButton, Gtk.ComboBox, Gtk.Box, Gtk.VBox, Gtk.HBox)

def _sort_tweak_widgets_by_widget_type(tweak):
    #for appearance tries to make small widgets be packed first, followed by larger widgets,
    #followed by widgets of the same type
    if not tweak.widget_for_size_group:
        return -1
    if tweak.widget_sort_hint != None:
        return tweak.widget_sort_hint
    try:
        return WIDGET_SORT_ORDER.index(type(tweak.widget_for_size_group))
    except ValueError:
        return len(WIDGET_SORT_ORDER) #last

class Window(Gtk.ApplicationWindow):

    def __init__(self, app, model):
        Gtk.ApplicationWindow.__init__(self,
                              title="Tweak Tool",
                              application=app,
                              hide_titlebar_when_maximized=True)
        
        self.set_size_request(800, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        left_box = self.sidebar()
        right_box = self.main_content()
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        
        main_box.pack_start(left_box, False, False, 0)
        main_box.pack_start(separator, False, False, 0)
        main_box.pack_start(right_box, True, True, 0)
        
        self.load_css()      
        self._model = model
        self._model.load_tweaks()
        self.load_model_data()

        self.connect("key-press-event", self._on_key_press)
        self.add(main_box)
        
    def sidebar(self):
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
       
        left_header = Gtk.HeaderBar()
        left_header.set_title("Tweaks")
        
        icon = Gtk.Image()
        icon.set_from_icon_name("edit-find-symbolic", Gtk.IconSize.BUTTON)
        self.button = Gtk.ToggleButton()
        self.button.add(icon)
        self.button.connect("toggled", self._on_transition)
         
        self.revealer = Gtk.Revealer()
        self.entry = Gtk.SearchEntry(placeholder_text="Search Tweaks...")
        self.entry.props.margin_left = 5
        self.entry.props.margin_right = 5
        self.entry.props.margin_top = 5
        self.entry.props.margin_bottom = 5
        self.entry.connect("search-changed", self._on_search)
        self.revealer.add(self.entry)
        
        self.listbox = Gtk.ListBox(name="tweak-categories")
        self.listbox.set_size_request(200,-1)
        self.listbox.connect("row-selected", self._on_select_row)
        self.listbox.set_header_func(self._list_header_func, None)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER,
                          Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.listbox)
        
        left_header.pack_start(self.button)
        left_box.pack_start(left_header, False, False, 0)
        left_box.pack_start(self.revealer, False, False, 0)
        left_box.pack_start(scroll, True, True, 0)
        
        return left_box
        
    def main_content(self):        
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        self.right_header = Gtk.HeaderBar()
        #GRR why can I not put margin in the CSS?
        self.stack = Gtk.Stack(name="main-container",
                               margin=20)
        self._detail_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        right_box.pack_start(self.right_header, False, False, 0)
        right_box.pack_start(self.stack, True, True, 0)
        right_box.pack_start(self._detail_vbox, False, False, 0)
        
        return right_box

    def load_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(
                        os.path.join(gtweak.PKG_DATA_DIR, 'shell.css'))
        screen = Gdk.Screen.get_default()
        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, css_provider,
                                Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def load_model_data(self):

        def _items_listbox(text):
            lbl = Gtk.Label(text, xalign=0.0)
            lbl.set_name('row')
            row = Gtk.ListBoxRow(name="tweak-category")
            row.add(lbl)
            return row

        def _load_tweaks(group):
            itere = self._model.get_tweakgroup_iter(group)  
            tweakgroup = self._model.get_value(itere, self._model.COLUMN_TWEAK)
            box = Gtk.ListBox(name="tweak-group",
                              selection_mode=Gtk.SelectionMode.NONE)
            for t in sorted(tweakgroup.tweaks, key=_sort_tweak_widgets_by_widget_type):
                cssname = "tweak"
                if isinstance(t, Title):
                    cssname = "tweak-title"
                row = Gtk.ListBoxRow(name=cssname)
                row.add(t.widget)
                box.add(row)
                t.set_notify_cb(self._on_tweak_notify)
            scroll = Gtk.ScrolledWindow()
            scroll.add(box)
            self.stack.add_named(scroll, group)

        groups = self._model._tweak_group_names.keys()
        groups = sorted(groups)

        for g in groups:
            row = _items_listbox(g)
            self.listbox.add(row)
            _load_tweaks(g)

        widget = self.listbox.get_row_at_index(0)
        self.listbox.select_row (widget)
        self._notification_functions = {}

    def _list_filter_func(self, row, user_data):
        lbl = row.get_child()
        if lbl.get_text() in user_data:
            return row
    
    def _list_header_func(self, row, before, user_data):
        if not row.get_header():
            row.set_header (Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

    def _on_key_press(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            self.button.set_active(False)
        if event.state and Gdk.ModifierType.CONTROL_MASK:
            if keyname == 'f':
                self.button.set_active(True)

    def _on_list_changed(self, group):
        self.listbox.set_filter_func(self._list_filter_func, group)
        selected = self.listbox.get_selected_row().get_child().get_text()
        if group and not selected in group:
            index =  sorted(self._model._tweak_group_names.keys()).index(group[0])
            row = self.listbox.get_row_at_index(index)
            self.listbox.select_row(row)

    def _on_search(self, entry):
        txt = entry.get_text()
        tweaks, group = self._model.search_matches(txt)
        self.show_only_tweaks(tweaks)        
        self._on_list_changed(group)
        
    def _on_select_row(self, listbox, row):
        if row:
            group = row.get_child().get_text()
            self.stack.set_visible_child_name(group)
            self.right_header.set_title(group)

    def _on_transition(self, btn):
        if self.revealer.get_reveal_child():
            self.revealer.set_reveal_child(False)
            self.revealer.get_child().set_text("")
        else:
            self.revealer.set_reveal_child(True) 
            
    def show_only_tweaks(self, tweaks):
        for t in self._model.tweaks:
            if t in tweaks:
                t.widget.show_all()
            else:
                t.widget.hide()

    def _on_tweak_notify_response(self, info, response, func):
        self._detail_vbox.remove(info)
        func()
        try:
            del(self._notification_functions[func])
        except KeyError:
            logging.warning("Could not remove notification function")

    def _on_tweak_notify(self, tweak, desc, error, btn, func, need_logout):
        #if need to log out, do this as a notification area thing, not a note inside
        #the main window
        
        if need_logout:
            notification = Notification()
            notification.show()
        
        info = Gtk.InfoBar()
        info.get_content_area().add(Gtk.Label(desc))

        if error:
            info.props.message_type = Gtk.MessageType.ERROR
        else:
            info.props.message_type = Gtk.MessageType.INFO

        if btn and func:
            if func in self._notification_functions:
                return
            self._notification_functions[func] = True
            info.add_button(btn, Gtk.ResponseType.OK)
            info.connect("response", self._on_tweak_notify_response, func)
        else:
            GObject.timeout_add_seconds(2, lambda box, widget: box.remove(widget), self._detail_vbox, info)

        self._detail_vbox.pack_end(info, False, False, 0)

        info.show_all()
