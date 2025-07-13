from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Adw
import threading

from .message_item import MessageItem
from .window_actions import WindowActionHandler
from .utils.command_utils import CommandUtils
from .utils.llm_utils import LLMClient

# --------------- GTK Window ----------------------------------
@Gtk.Template(resource_path="/com/azibom/assistant/window.ui")
class AssistantWindow(Adw.ApplicationWindow):
    __gtype_name__ = "AssistantWindow"

    menu_button = Gtk.Template.Child()
    chat_list = Gtk.Template.Child()
    chat_entry = Gtk.Template.Child()
    send_button = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()
    overlay_placeholder = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_entry.connect("changed", self.on_entry_changed)
        self.chat_entry.connect("apply", self.on_entry_activate)
        self.action_handler = WindowActionHandler(self)
        self.action_handler.setup_actions()
        self.llm_client = LLMClient()
        self.cmd_utils = CommandUtils(self.llm_client)

    def on_entry_changed(self, entry):
        self.send_button.set_sensitive(bool(entry.get_text().strip()))

    def append_message(self, who, msg, model=None):
        item = MessageItem(
            self,
            {
                "role": who,
                "content": msg,
                "time": self.get_time(),
                "model": model or "human",
            },
        )
        self.chat_list.append(item)

        GLib.timeout_add(50, self.scroll_down)

    def scroll_down(self, *args):
        self.scrolled_window.emit("scroll-child", Gtk.ScrollType.END, False)

    def get_time(self):
        return GLib.DateTime.new_now_local().format("%H:%M")

    @Gtk.Template.Callback()
    def on_entry_activate(self, _widget):
        text = self.chat_entry.get_text().strip()
        if not text:
            return
        self.append_message("You", text)
        self.chat_entry.set_text("")

        def worker():
            cat = self.cmd_utils.pick_category(text)
            fn, sim = self.cmd_utils.pick_command(text, cat)

            if sim >= self.cmd_utils.COMMAND_THRESHOLD:
                model_info = f"{cat} > {fn} ({sim:.1%})"
                out = self.cmd_utils.run_cmd(fn, cat, text)
                GLib.idle_add(self.append_message, "Assistant", str(out), model_info)
            else:
                GLib.idle_add(
                    self.append_message,
                    "Assistant",
                    (
                        f"I don't think this is a command "
                        f"(similarity {sim:.2%}). "
                        "Let me answer as an assistant..."
                    ),
                )
                out = self.llm_client.ask_llm(text)
                GLib.idle_add(self.append_message, "Assistant", out, "LLM_MODEL")

        threading.Thread(target=worker, daemon=True).start()
