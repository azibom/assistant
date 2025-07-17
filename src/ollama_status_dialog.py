from gi.repository import Gtk, Adw


@Gtk.Template(resource_path="/com/azibom/assistant/gtk/ollama_status.ui")
class OllamaStatusDialog(Adw.Dialog):
    """A dialog to show the connection status of Ollama."""

    __gtype_name__ = "OllamaStatusDialog"

    # Define template children
    not_connected_view = Gtk.Template.Child()
    connected_view = Gtk.Template.Child()

    def __init__(self, is_connected=False, **kwargs):
        super().__init__(**kwargs)
        self.update_status(is_connected)

    def update_status(self, is_connected: bool):
        """Shows the appropriate view based on connection status."""
        self.connected_view.set_visible(is_connected)
        self.not_connected_view.set_visible(not is_connected)

    @Gtk.Template.Callback()
    def on_retry_clicked(self, _widget):
        """Callback to close the dialog."""
        self.close()
