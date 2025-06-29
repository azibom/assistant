from gi.repository import Gtk, Adw, Gio, Gdk


@Gtk.Template(resource_path="/com/azibom/assistant/message_item.ui")
class MessageItem(Gtk.Box):
    __gtype_name__ = "MessageItem"

    user = Gtk.Template.Child()
    content = Gtk.Template.Child()
    timestamp = Gtk.Template.Child()
    popover = Gtk.Template.Child()
    avatar = Gtk.Template.Child()
    message_bubble = Gtk.Template.Child()
    model = Gtk.Template.Child()

    def __init__(self, parent, message_data, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.message_data = message_data
        self.content_text = self.message_data["content"]

        self._setup_content_label()
        self._setup_role_specific_ui()

        self.timestamp.set_text(self.message_data.get("time", ""))
        self.model.set_text(self.message_data.get("model", ""))

        self._setup_gestures_and_actions()

    def _setup_content_label(self):
        """Creates and configures the main message content label."""
        label = Gtk.Label()
        label.set_text(self.content_text)
        label.set_wrap(True)
        label.set_selectable(True)
        label.set_xalign(0)
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        self.content.append(label)

    def _setup_role_specific_ui(self):
        """Applies styling and sets text based on the message role."""
        role_type = self.message_data["role"].lower()
        display_role = role_type.capitalize()

        if role_type == "you":
            self.message_bubble.add_css_class("message-bubble-user")
            self.avatar.add_css_class("avatar-user")
        elif role_type == "assistant":
            self.message_bubble.add_css_class("message-bubble-assistant")
            self.avatar.set_icon_name("bot-symbolic")
            self.user.add_css_class("warning")
        
        self.avatar.set_text(display_role)
        self.user.set_text(display_role)

    def _setup_gestures_and_actions(self):
        """Initializes right-click context menu and associated actions."""
        self._setup_actions()

        right_click_gesture = Gtk.GestureClick.new()
        right_click_gesture.connect("pressed", self._show_popover_menu)
        right_click_gesture.set_button(3)
        self.add_controller(right_click_gesture)

    def _show_popover_menu(self, gesture, n_press, x, y):
        self.popover.set_parent(self)
        self.popover.popup()

    def _setup_actions(self):
        self.action_group = Gio.SimpleActionGroup()
        self._create_action("copy", self.on_copy)
        edit_action = self._create_action("edit", self.on_edit)
        self.insert_action_group("event", self.action_group)

        if self.message_data["role"].lower() == "assistant":
            edit_action.set_enabled(False)

    def _create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.action_group.add_action(action)

        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)
        return action

    def on_edit(self, *args):
        if self.message_data["role"].lower() == "you":
            self.parent.chat_entry.set_text(self.content_text)
            self.parent.chat_entry.grab_focus()


    def on_copy(self, *args):
        Gdk.Display.get_default().get_clipboard().set(self.content_text)

        toast = Adw.Toast()
        toast.set_title('Message copied')
        self.parent.toast_overlay.add_toast(toast)



