# handlers/window_actions.py
#
# Copyright 2025 azibom
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gio


class WindowActionHandler:
    """Handles window-level actions and keyboard shortcuts"""

    def __init__(self, window):
        self.window = window

    def setup_actions(self):
        """Setup all window actions and keyboard shortcuts"""
        actions = [
            ("open-menu", self.on_open_menu_action, ["F10"]),
            (
                "show-help-overlay",
                self.on_show_help_overlay,
                ["<primary>question", "F1"],
            ),
            ("scroll-to-bottom", self.on_scroll_to_bottom_action, ["<primary>End"]),
            ("scroll-to-top", self.on_scroll_to_top_action, ["<primary>Home"]),
            ("toggle-fullscreen", self.on_toggle_fullscreen_action, ["F11"]),
            (
                "copy-last-response",
                self.on_copy_last_response_action,
                ["<primary><shift>c"],
            ),
            ("quit", self.on_close_window_action, ["<primary>q", "<primary>w"]),
        ]

        for action_name, callback, shortcuts in actions:
            self._create_action(action_name, callback, shortcuts)

    def _create_action(self, name, callback, shortcuts=None):
        """Create and register an action with optional keyboard shortcuts"""
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.window.add_action(action)
        if shortcuts:
            app = self.window.get_application()
            app.set_accels_for_action(f"win.{name}", shortcuts)

    def on_open_menu_action(self, action, param):
        self.window.menu_button.activate()

    def on_show_help_overlay(self, action, param):
        """Show the keyboard shortcuts overlay"""
        self.window.get_help_overlay().present()

    def on_scroll_to_bottom_action(self, action, param):
        """Scroll to the bottom of the chat"""
        if hasattr(self.window, "scrolled_window"):
            adjustment = self.window.scrolled_window.get_vadjustment()
            adjustment.set_value(adjustment.get_upper() - adjustment.get_page_size())

    def on_scroll_to_top_action(self, action, param):
        """Scroll to the top of the chat"""
        if hasattr(self.window, "scrolled_window"):
            adjustment = self.window.scrolled_window.get_vadjustment()
            adjustment.set_value(0)

    def on_toggle_fullscreen_action(self, action, param):
        """Toggle fullscreen mode"""
        if self.window.is_fullscreen():
            self.window.unfullscreen()
        else:
            self.window.fullscreen()

    def on_copy_last_response_action(self, action, param):
        """Copy the last AI response to clipboard"""
        last_child = self.window.chat_list.get_last_child()
        if last_child:
            message_item = last_child.get_child()
            if message_item:
                text = message_item.message_data.get("content", "")
                if text:
                    clipboard = self.window.get_clipboard()
                    clipboard.set(text)

    def on_close_window_action(self, action, param):
        """Close the window"""
        self.window.close()
