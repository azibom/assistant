from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Adw
import json
import urllib.request
import threading
import re
import numpy as np

from .commands import commands
from .message_item import MessageItem

# --------------- Embedding via Ollama (GPU) -----------------
OLLAMA_URL = "http://localhost:11434/api"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "phi:2.7b-chat-v2-q4_0"
COMMAND_THRESHOLD = 0.70


def extract_argument(prompt: str, arg_description: str) -> str | None:
    sys_prompt = (
        f"You are an assistant extracting argument values from user input.\n"
        f"Argument: {arg_description}\n"
        f"User may provide the argument directly or implicitly.\n"
        f"For example, if the user says 'open Facebook', "
        f"you should respond with 'https://facebook.com'.\n"
        f"Respond ONLY with the final value or the single word: NONE.\n"
    )
    payload = {
        "model": LLM_MODEL,
        "prompt": f"{sys_prompt}\nUser: {prompt}",
        "stream": False,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/generate", data=data)
    resp = urllib.request.urlopen(req)
    out = json.loads(resp.read())["response"].strip()
    return None if out.upper() == "NONE" else out


def embed(text: str) -> np.ndarray:
    payload = {"model": EMBED_MODEL, "prompt": text}
    req = urllib.request.Request(
        f"{OLLAMA_URL}/embeddings", data=json.dumps(payload).encode()
    )
    vec = urllib.request.urlopen(req).read()
    return np.asarray(json.loads(vec)["embedding"], dtype=np.float32)


def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# --------------- Categories / Commands ----------------------
CATEGORIES = {
    "system": "System-level commands: uptime, free space, assistant name, open browser",
}
CATEGORY_EMB = {k: embed(v) for k, v in CATEGORIES.items()}
COMMAND_EMB = {
    cat: {n: embed(c["short"] + " " + c["long"]) for n, c in cmds.items()}
    for cat, cmds in commands.items()
}

# --------------- Keyword overrides --------------------------
KEYWORDS = {
    "get_bot_name": ["your name", "who are you", "name of assistant"],
    "get_bot_age": ["how old are you", "your age"],
    "get_uptime": ["uptime", "how long", "system running"],
    "get_free_space": ["free space", "disk space", "storage left"],
    "open_browser": ["open", "website", "browser", "go to", "search"],
}


# --------------- TinyLlama helper to extract URL -------------
def extract_url(prompt: str) -> str | None:
    url_regex = r"(https?://[^\s]+)"
    m = re.search(url_regex, prompt)
    if m:
        return m.group(1)

    sys_prompt = (
        "Extract the first valid URL from the user's request. "
        "Respond ONLY with the URL or, if no URL present, the single word: NONE."
    )
    payload = {
        "model": "tinyllama",
        "prompt": f"{sys_prompt}\nUser: {prompt}",
        "stream": False,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/generate", data=data)
    resp = urllib.request.urlopen(req)
    out = json.loads(resp.read())["response"].strip()
    return None if out.upper() == "NONE" else out


# --------------- GTK Window ----------------------------------
@Gtk.Template(resource_path="/com/azibom/assistant/window.ui")
class AssistantWindow(Adw.ApplicationWindow):
    __gtype_name__ = "AssistantWindow"

    chat_list = Gtk.Template.Child()
    chat_entry = Gtk.Template.Child()
    send_button = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_entry.connect("changed", self.on_entry_changed)
        self.chat_entry.connect("apply", self.on_entry_activate)

    def on_entry_changed(self, entry):
        self.send_button.set_sensitive(bool(entry.get_text().strip()))

    def ask_llm(self, prompt: str) -> str:
        try:
            sys_prompt = (
                "You are a helpful assistant. Please answer the user's question "
                "clearly but briefly, in 1-2 short sentences. "
                "Do not give long explanations. Be concise."
            )
            phi_payload = {
                "model": LLM_MODEL,
                "prompt": f"{sys_prompt}\nUser: {prompt}",
                "stream": False,
                "max_tokens": 100,
            }
            data = json.dumps(phi_payload).encode()
            req = urllib.request.Request(f"{OLLAMA_URL}/generate", data=data)
            resp = urllib.request.urlopen(req)
            out = json.loads(resp.read())["response"].strip()
            return out
        except Exception as e:
            return f"Failed to get response from LLM: {e}"

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

    @Gtk.Template.Callback()
    def scroll_down(self, *args):
        self.scrolled_window.emit("scroll-child", Gtk.ScrollType.END, False)

    def get_time(self):
        return GLib.DateTime.new_now_local().format("%H:%M")

    def pick_category(self, text):
        q = embed(text)
        return max(CATEGORY_EMB, key=lambda c: cosine(q, CATEGORY_EMB[c]))

    def pick_command(self, text, category):
        t = text.lower()
        for fn, words in KEYWORDS.items():
            if any(w in t for w in words):
                return fn, 1.0
        q = embed(text)
        best, best_sim = None, -1.0
        for fn, vec in COMMAND_EMB[category].items():
            sim = cosine(q, vec)
            if sim > best_sim:
                best, best_sim = fn, sim
        return best, best_sim

    def run_cmd(self, fn_name, category, user_text):
        cmd = commands[category][fn_name]
        args_values = []
        if cmd["args"]:
            for arg in cmd["args"]:
                arg_name = arg["name"]
                arg_description = arg["description"]
                value = extract_argument(user_text, arg_description)
                if value is None:
                    return f"Missing argument '{arg_name}' for {fn_name}."
                args_values.append(value)
        return cmd["execute"](*args_values)

    @Gtk.Template.Callback()
    def on_entry_activate(self, _widget):
        text = self.chat_entry.get_text().strip()
        if not text:
            return
        self.append_message("You", text)
        self.chat_entry.set_text("")

        def worker():
            cat = self.pick_category(text)
            fn, sim = self.pick_command(text, cat)

            if sim >= COMMAND_THRESHOLD:
                model_info = f"{cat} > {fn} ({sim:.1%})"
                out = self.run_cmd(fn, cat, text)
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
                out = self.ask_llm(text)
                GLib.idle_add(self.append_message, "Assistant", out, LLM_MODEL)

        threading.Thread(target=worker, daemon=True).start()