from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Adw
import threading

from .message_item import MessageItem
from .window_actions import WindowActionHandler
from .utils.command_utils import CommandUtils
from .utils.llm_utils import LLMClient
from .ollama_status_dialog import OllamaStatusDialog


@Gtk.Template(resource_path="/com/azibom/assistant/window.ui")
class AssistantWindow(Adw.ApplicationWindow):
    __gtype_name__ = "AssistantWindow"

    menu_button = Gtk.Template.Child()
    chat_list = Gtk.Template.Child()
    chat_entry = Gtk.Template.Child()
    send_button = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()
    overlay_placeholder = Gtk.Template.Child()
    connection_status_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_entry.connect("changed", self.on_entry_changed)
        self.chat_entry.connect("apply", self.on_entry_activate)
        self.action_handler = WindowActionHandler(self)
        self.action_handler.setup_actions()
        self.llm_client = LLMClient(self)
        self.cmd_utils = CommandUtils(self.llm_client)
        self.start_ollama_health_check(interval_seconds=5)

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
            # Pick category
            cat, cat_err = self.cmd_utils.pick_category(text)
            if cat_err:
                GLib.idle_add(
                    self.append_message,
                    "Assistant",
                    f"Error picking category: {cat_err}",
                    self.llm_client.embed_model,
                )
                return

            # Pick command
            fn, sim, com_err = self.cmd_utils.pick_command(text, cat)
            if com_err:
                GLib.idle_add(
                    self.append_message,
                    "Assistant",
                    f"Error picking command: {com_err}",
                    self.llm_client.embed_model,
                )
                return

            # If command is recognized
            if sim >= self.cmd_utils.COMMAND_THRESHOLD:
                model_info = f"{cat} > {fn} ({sim:.1%})"
                out = self.cmd_utils.run_cmd(fn, cat, text)
                GLib.idle_add(self.append_message, "Assistant", str(out), model_info)
                return

            # Otherwise, fallback to LLM
            GLib.idle_add(
                self.append_message,
                "Assistant",
                (
                    f"I don't think this is a command "
                    f"(similarity {sim:.2%}).\n"
                    "Let me answer as an assistant..."
                ),
                self.llm_client.embed_model,
            )
            out, error = self.llm_client.ask_llm(text)
            if error:
                GLib.idle_add(
                    self.append_message,
                    "Assistant",
                    f'Make Sure "{self.llm_client.llm_model}" is'
                    "running and connected!",
                    self.llm_client.llm_model,
                )
            else:
                GLib.idle_add(
                    self.append_message, "Assistant", out, self.llm_client.llm_model
                )

        threading.Thread(target=worker, daemon=True).start()

    @Gtk.Template.Callback()
    def on_connection_status_clicked(self, _widget):
        """Shows the Ollama status dialog."""
        dialog = OllamaStatusDialog(
            is_connected=self.llm_client.is_ollama_connected,
        )
        dialog.present(self)

    def start_ollama_health_check(self, interval_seconds: int) -> int:
        """
        Sets up a recurring task to check the Ollama connection status.
        """

        def updater() -> bool:
            self.llm_client.check_connection()
            self.update_connection_status()
            return GLib.SOURCE_CONTINUE

        event_source_id = GLib.timeout_add_seconds(interval_seconds, updater)
        updater()
        return event_source_id

    def update_connection_status(self):
        if self.llm_client.is_ollama_connected:
            self.connection_status_button.set_child(
                Gtk.Image.new_from_icon_name("check-round-outline2-symbolic")
            )
            self.connection_status_button.set_tooltip_text("Ollama is connected")
        else:
            current_child = self.connection_status_button.get_child()
            if not isinstance(current_child, Adw.Spinner):
                self.connection_status_button.set_child(Adw.Spinner())
            self.connection_status_button.set_tooltip_text("Ollama is not connected")
