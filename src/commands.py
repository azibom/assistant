import subprocess, datetime, shutil, os
import webbrowser
import urllib.request
from gi.repository import Gio, GLib

BOOT_TIME = datetime.datetime.now()

# === Commands ===
def _show_notification():
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.freedesktop.Notifications",
            "/org/freedesktop/Notifications",
            "org.freedesktop.Notifications",
            None
        )

        proxy.call_sync(
            "Notify",
            GLib.Variant("(susssasa{sv}i)", (
                "GNOME-AI",          # app name
                0,                   # replaces_id
                "",                  # app_icon
                "Hello!",            # summary
                "This is a notification from your Assistant 🤖", # body
                [],                  # actions
                {},                  # hints
                -1                   # expire_timeout
            )),
            Gio.DBusCallFlags.NONE,
            -1,
            None
        )

        return "Notification sent."
    except Exception as e:
        return f"Failed to send notification: {e}"


def _open_browser(url: str) -> str:
    if not url.startswith("http"):
        url = "https://google.com"
    Gio.AppInfo.launch_default_for_uri(url, None)
    return f"Opened URL via portal: {url}"

def _get_datetime():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _create_folder(folder_name: str):
    desktop_path = os.path.join(os.environ["HOME"], "Desktop")
    safe_folder_name = "".join(c for c in folder_name if c.isalnum() or c in (" ", "_", "-")).rstrip()
    new_folder_path = os.path.join(desktop_path, safe_folder_name)
    os.makedirs(new_folder_path, exist_ok=True)
    return f"Folder created: {new_folder_path}"


def _get_public_ip():
    try:
        ip = urllib.request.urlopen("https://api.ipify.org").read().decode()
        return f"My public IP is: {ip}"
    except Exception as e:
        return f"Failed to get IP: {e}"

# === Commands Dictionary ===

# === Commands Dictionary ===

commands = {
    "system": {
        "get_uptime": {
            "label":  "Uptime",
            "short":  "Show system uptime.",
            "long":   "Returns the current system uptime with `uptime -p`.",
            "usage":  "run: get_uptime()",
            "args":   [],
            "execute": lambda: subprocess.getoutput("uptime -p"),
        },
        "get_free_space": {
            "label":  "Free Disk Space",
            "short":  "Show available disk space.",
            "long":   "Displays free space on `/` via `df -h /`.",
            "usage":  "run: get_free_space()",
            "args":   [],
            "execute": lambda: subprocess.getoutput("df -h /"),
        },
        "get_bot_name": {
            "label":  "Assistant Name",
            "short":  "Tell the assistant's name.",
            "long":   "Returns the assistant's name.",
            "usage":  "run: get_bot_name()",
            "args":   [],
            "execute": lambda: "I'm GNOME-AI 🤖",
        },
        "get_bot_age": {
            "label":  "Assistant Age",
            "short":  "Tell assistant's age.",
            "long":   "Returns how long the assistant instance has been running.",
            "usage":  "run: get_bot_age()",
            "args":   [],
            "execute": lambda: f"I have been alive for {(datetime.datetime.now()-BOOT_TIME).seconds//60} minutes.",
        },
        "get_datetime": {
            "label":  "Date & Time",
            "short":  "Show current date and time.",
            "long":   "Displays the current date and time.",
            "usage":  "run: get_datetime()",
            "args":   [],
            "execute": _get_datetime,
        },
        "open_browser": {
            "label":  "Open Browser",
            "short":  "Open a website in browser.",
            "long":   "Opens a given URL in the default browser via portal.",
            "usage":  "run: open_browser(\"https://example.com\")",
            "args":   [
                {
                    "name": "url",
                    "description": "The URL of the website to open."
                }
            ],
            "execute": _open_browser,
        },

"create_folder": {
    "label":  "Create Folder",
    "short":  "Create a folder on Desktop.",
    "long":   "Creates a folder with a given name on the Desktop.",
    "usage":  "run: create_folder(\"MyFolder\")",
    "args":   [
        {
            "name": "folder_name",
            "description": "The name of the folder to create on the Desktop."
        }
    ],
    "execute": _create_folder,
},

        "show_notification": {
            "label":  "Show Notification",
            "short":  "Show GNOME notification.",
            "long":   "Shows a notification using GNOME notifications portal.",
            "usage":  "run: show_notification()",
            "args":   [],
            "execute": _show_notification,
        },
        "get_public_ip": {
            "label":  "Public IP",
            "short":  "Get public IP address.",
            "long":   "Returns the current public IP address.",
            "usage":  "run: get_public_ip()",
            "args":   [],
            "execute": _get_public_ip,
        },
    }
}


