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

import logging
import os.path

from gi.repository import GLib, Gtk, Gdk, Gio, Pango

from gtweak.tweakmodel import Tweak
from gtweak.gsettings import GSettingsSetting, GSettingsFakeSetting, GSettingsMissingError
from gtweak.gtksettings import GtkSettingsManager
from gtweak.gshellwrapper import GnomeShellFactory

UI_BOX_SPACING = 4
_shell = GnomeShellFactory().get_shell()

def build_label_beside_widget(txt, *widget, **kwargs):
    """
    Builds a HBox containing widgets.

    Optional Kwargs:
        hbox: Use an existing HBox, not a new one
        info: Informational text to be shown after the label
        warning: Warning text to be shown after the label
    """
    def make_image(icon, tip):
        image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU)
        image.set_tooltip_text(tip)
        return image

    def show_tooltip_when_ellipsized(label, x, y, keyboard_mode, tooltip):
        layout = label.get_layout()
        if layout.is_ellipsized():
            tooltip.set_text(label.get_text())
            return True
        else:
            return False

    if kwargs.get("hbox"):
        hbox = kwargs.get("hbox")
    else:
        hbox = Gtk.HBox()

    hbox.props.spacing = UI_BOX_SPACING
    lbl = Gtk.Label(txt)
    lbl.props.ellipsize = Pango.EllipsizeMode.END
    lbl.props.xalign = 0.0
    lbl.set_has_tooltip(True)
    lbl.connect("query-tooltip", show_tooltip_when_ellipsized)
    hbox.pack_start(lbl, True, True, 0)

    if kwargs.get("info"):
        hbox.pack_start(
                make_image("dialog-information-symbolic", kwargs.get("info")),
                False, False, 0)
    if kwargs.get("warning"):
        hbox.pack_start(
                make_image("dialog-warning-symbolic", kwargs.get("warning")),
                False, False, 0)

    for w in widget:
        hbox.pack_start(w, False, False, 0)

    #For Atk, indicate that the rightmost widget, usually the switch relates to the
    #label. By convention this is true in the great majority of cases. Settings that
    #construct their own widgets will need to set this themselves
    lbl.set_mnemonic_widget(widget[-1])
    
    if kwargs.get("desc"):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(hbox, False, False, 0)
        desc = kwargs.get("desc")
        lbl_des = Gtk.Label()
        lbl_des.props.xalign = 0.0
        lbl_des.set_markup("<span size='x-small'>"+desc+"</span>")
        box.pack_start(lbl_des, False, False,0)
        return box
        
    else:
        return hbox

def build_combo_box_text(selected, *values):
    """
    builds a GtkComboBox and model containing the supplied values.
    @values: a list of 2-tuples (value, name)
    """
    store = Gtk.ListStore(str, str)
    store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

    selected_iter = None
    for (val, name) in values:
        _iter = store.append( (val, name) )
        if val == selected:
            selected_iter = _iter

    combo = Gtk.ComboBox(model=store)
    renderer = Gtk.CellRendererText()
    combo.pack_start(renderer, True)
    combo.add_attribute(renderer, 'markup', 1)
    if selected_iter:
        combo.set_active_iter(selected_iter)

    return combo

def build_horizontal_sizegroup():
    sg = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
    sg.props.ignore_hidden = True
    return sg

def build_tight_button(stock_id):
    button = Gtk.Button()
    button.set_relief(Gtk.ReliefStyle.NONE)
    button.set_focus_on_click(False)
    button.add(Gtk.Image.new_from_stock(stock_id, Gtk.IconSize.MENU))
    data =  ".button {\n" \
            "-GtkButton-default-border : 0px;\n" \
            "-GtkButton-default-outside-border : 0px;\n" \
            "-GtkButton-inner-border: 0px;\n" \
            "-GtkWidget-focus-line-width : 0px;\n" \
            "-GtkWidget-focus-padding : 0px;\n" \
            "padding: 0px;\n" \
            "}"
    provider = Gtk.CssProvider()
    provider.load_from_data(data)
    # 600 = GTK_STYLE_PROVIDER_PRIORITY_APPLICATION
    button.get_style_context().add_provider(provider, 600) 
    return button

def adjust_schema_for_overrides(originalSchema, key, options):
    if (_shell is None):
        return originalSchema

    if (_shell.mode == 'classic'):
        overridesSchema = "org.gnome.shell.extensions.classic-overrides"
        overridesFile = None
    else:
        overridesSchema = "org.gnome.shell.overrides"
        overridesFile = "org.gnome.shell.gschema.xml"

    if (key in Gio.Settings(overridesSchema).list_keys()):
        options['schema_filename'] = overridesFile
        return overridesSchema
    return originalSchema


class _GSettingsTweak(Tweak):
    def __init__(self, schema_name, key_name, **options):
        schema_name = adjust_schema_for_overrides(schema_name, key_name, options)
        self.schema_name = schema_name
        self.key_name = key_name
        try:
            self.settings = GSettingsSetting(schema_name, **options)
            Tweak.__init__(self,
                options.get("summary",self.settings.schema_get_summary(key_name)),
                options.get("description",self.settings.schema_get_description(key_name)),
                **options)
        except GSettingsMissingError, e:
            self.settings = GSettingsFakeSetting()
            Tweak.__init__(self,"","")
            self.loaded = False
            logging.info("GSetting missing %s" % (e.message))
        except KeyError:
            self.settings = GSettingsFakeSetting()
            Tweak.__init__(self,"","")
            self.loaded = False
            logging.info("GSettings missing key %s (key %s)" % (schema_name, key_name))

        if options.get("logout_required") and self.loaded:
            self.settings.connect("changed::%s" % key_name, self._on_changed_notify_logout)

    def _on_changed_notify_logout(self, settings, key_name):
        self.notify_action_required(
                "Configuration changes require restart",
                btn="Restart Session",
                func=None,
                need_logout=True,
        )

class _DependableMixin:

    def add_dependency_on_tweak(self, depends, depends_how):
        if isinstance(depends, Tweak):
            self._depends = depends
            if depends_how is None:
                depends_how = lambda x,kn: x.get_boolean(kn)
            self._depends_how = depends_how

            sensitive = self._depends_how(
                                depends.settings,
                                depends.key_name,
            )
            self.widget.set_sensitive(sensitive)

            depends.settings.connect("changed::%s" % depends.key_name, self._on_changed_depend)

    def _on_changed_depend(self, settings, key_name):
        sensitive = self._depends_how(settings,key_name)
        self.widget.set_sensitive(sensitive)

class GSettingsCheckTweak(_GSettingsTweak, _DependableMixin):
    def __init__(self, name, schema_name, key_name, **options):
        _GSettingsTweak.__init__(self, schema_name, key_name, **options)

        self.widget = Gtk.CheckButton.new_with_label(name)
        self.settings.bind(
                key_name,
                self.widget,
                "active", Gio.SettingsBindFlags.DEFAULT)
        self.widget_for_size_group = None

        self.add_dependency_on_tweak(
                options.get("depends_on"),
                options.get("depends_how")
        )

class GSettingsSwitchTweak(_GSettingsTweak, _DependableMixin):
    def __init__(self, name, schema_name, key_name, **options):
        _GSettingsTweak.__init__(self, schema_name, key_name, **options)

        w = Gtk.Switch()
        self.settings.bind(key_name, w, "active", Gio.SettingsBindFlags.DEFAULT)
        self.widget = build_label_beside_widget(name, w)
        # never change the size of a switch
        self.widget_for_size_group = None

        self.add_dependency_on_tweak(
                options.get("depends_on"),
                options.get("depends_how")
        )

class GSettingsFontButtonTweak(_GSettingsTweak, _DependableMixin):
    def __init__(self, name, schema_name, key_name, **options):
        _GSettingsTweak.__init__(self, schema_name, key_name, **options)

        w = Gtk.FontButton()
        self.settings.bind(key_name, w, "font-name", Gio.SettingsBindFlags.DEFAULT)
        self.widget = build_label_beside_widget(name, w)
        self.widget_for_size_group = w

class GSettingsRangeTweak(_GSettingsTweak, _DependableMixin):
    def __init__(self, schema_name, key_name, **options):
        _GSettingsTweak.__init__(self, schema_name, key_name, **options)

        #returned variant is range:(min, max)
        _min, _max = self.settings.get_range(key_name)[1]

        w = Gtk.HScale.new_with_range(_min, _max, options.get('adjustment_step', 1))
        self.settings.bind(key_name, w.get_adjustment(), "value", Gio.SettingsBindFlags.DEFAULT)
        self.widget = build_label_beside_widget(self.name, w)
        self.widget_for_size_group = w

class GSettingsSpinButtonTweak(_GSettingsTweak, _DependableMixin):
    def __init__(self, schema_name, key_name, **options):
        _GSettingsTweak.__init__(self, schema_name, key_name, **options)

        #returned variant is range:(min, max)
        _min, _max = self.settings.get_range(key_name)[1]

        adjustment = Gtk.Adjustment(0, _min, _max, options.get('adjustment_step', 1))
        w = Gtk.SpinButton()
        w.set_adjustment(adjustment)
        w.set_digits(options.get('digits', 0))
        self.settings.bind(key_name, adjustment, "value", Gio.SettingsBindFlags.DEFAULT)
        self.widget = build_label_beside_widget(self.name, w)
        self.widget_for_size_group = w

class GSettingsComboEnumTweak(_GSettingsTweak, _DependableMixin):
    def __init__(self, name, schema_name, key_name, **options):
        _GSettingsTweak.__init__(self, schema_name, key_name, **options)

        _type, values = self.settings.get_range(key_name)
        value = self.settings.get_string(key_name)
        self.settings.connect('changed::'+self.key_name, self._on_setting_changed)

        w = build_combo_box_text(value, *[(v,v.replace("-"," ").title()) for v in values])
        w.connect('changed', self._on_combo_changed)
        self.combo = w

        self.widget = build_label_beside_widget(name, w)
        self.widget_for_size_group = w


    def _values_are_different(self):
        #to stop bouncing back and forth between changed signals. I suspect there must be a nicer
        #Gio.settings_bind way to fix this
        return self.settings.get_string(self.key_name) != \
               self.combo.get_model().get_value(self.combo.get_active_iter(), 0)

    def _on_setting_changed(self, setting, key):
        assert key == self.key_name
        val = self.settings.get_string(key)
        model = self.combo.get_model()
        for row in model:
            if val == row[0]:
                self.combo.set_active_iter(row.iter)
                break

    def _on_combo_changed(self, combo):
        val = self.combo.get_model().get_value(self.combo.get_active_iter(), 0)
        if self._values_are_different():
            self.settings.set_string(self.key_name, val)

class GSettingsComboTweak(_GSettingsTweak, _DependableMixin):
    def __init__(self, name, schema_name, key_name, key_options, **options):
        _GSettingsTweak.__init__(self, schema_name, key_name, **options)

        #check key_options is iterable
        #and if supplied, check it is a list of 2-tuples
        assert len(key_options) >= 0
        if len(key_options):
            assert len(key_options[0]) == 2

        self.combo = build_combo_box_text(
                    self.settings.get_string(self.key_name),
                    *key_options)
        self.combo.connect('changed', self._on_combo_changed)
        self.widget = build_label_beside_widget(name, self.combo)
        self.widget_for_size_group = self.combo

        self.settings.connect('changed::'+self.key_name, self._on_setting_changed)

    def _on_setting_changed(self, setting, key):
        assert key == self.key_name
        val = self.settings.get_string(key)
        model = self.combo.get_model()
        for row in model:
            if val == row[0]:
                self.combo.set_active_iter(row.iter)
                return

        self.combo.set_active(-1)

    def _on_combo_changed(self, combo):
        _iter = combo.get_active_iter()
        if _iter:
            value = combo.get_model().get_value(_iter, 0)
            self.settings.set_string(self.key_name, value)

class FileChooserButton(Gtk.FileChooserButton):
    def __init__(self, title, local_only, mimetypes):
        Gtk.FileChooserButton.__init__(self, title=title)

        if mimetypes:
            f = Gtk.FileFilter()
            for m in mimetypes:
                f.add_mime_type(m)
            self.set_filter(f)

        #self.set_width_chars(15)
        self.set_local_only(local_only)
        self.set_action(Gtk.FileChooserAction.OPEN)

class GSettingsFileChooserButtonTweak(_GSettingsTweak, _DependableMixin):
    def __init__(self, schema_name, key_name, local_only, mimetypes, **options):
        _GSettingsTweak.__init__(self, schema_name, key_name, **options)

        self.settings.connect('changed::'+self.key_name, self._on_setting_changed)

        self.filechooser = FileChooserButton(self.name,local_only,mimetypes)
        self.filechooser.set_uri(self.settings.get_string(self.key_name))
        self.filechooser.connect("file-set", self._on_file_set)

        self.widget = build_label_beside_widget(self.name, self.filechooser)
        self.widget_for_size_group = self.filechooser

    def _values_are_different(self):
        return self.settings.get_string(self.key_name) != self.filechooser.get_uri()

    def _on_setting_changed(self, setting, key):
        self.filechooser.set_uri(self.settings.get_string(key))

    def _on_file_set(self, chooser):
        uri = self.filechooser.get_uri()
        if uri and self._values_are_different():
            self.settings.set_string(self.key_name, uri)

class DarkThemeSwitcher(Tweak):
    def __init__(self, **options):
        Tweak.__init__(self, _("Enable dark theme for all applications"),
                       _("Enable the dark theme hint for all the applications in the session"),
                       **options)

        self._gtksettings = GtkSettingsManager()

        w = Gtk.Switch()
        w.set_active(self._gtksettings.get_integer("gtk-application-prefer-dark-theme"))
		
        title = _("Global Dark Theme")
        description = _("Applications need to be restarted for change to take effect")
        w.connect("notify::active", self._on_switch_changed)
        self.widget = build_label_beside_widget(title, w, desc=description)

    def _on_switch_changed(self, switch, param):
        active = switch.get_active()

        try:
            self._gtksettings.set_integer("gtk-application-prefer-dark-theme",
                                          active)
        except:
            self.notify_error(_("Error writing setting"))

class Title(Tweak):
    def __init__(self, name, desc, **options):
        Tweak.__init__(self, name, desc, **options)
        self.widget = Gtk.Label()
        self.widget.set_markup("<b>"+name+"</b>")
        self.widget.props.xalign = 0.0

