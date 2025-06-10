import json, urllib.request, threading, re, numpy as np
from gi.repository import Gtk, GLib
from .commands import commands

# --------------- Embedding via Ollama (GPU) -----------------
EMBED_URL  = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
LLM_URL = "http://localhost:11434/api/generate"
COMMAND_THRESHOLD = 0.70

def extract_argument(prompt: str, arg_description: str) -> str | None:
    sys_prompt = (
        f"You are an assistant extracting argument values from user input.\n"
        f"Argument: {arg_description}\n"
        f"User may provide the argument directly or implicitly.\n"
        f"For example, if the user says 'open Facebook', you should respond with 'https://facebook.com'.\n"
        f"Respond ONLY with the final value or the single word: NONE.\n"
    )
    payload = {"model": "phi:2.7b-chat-v2-q4_0", "prompt": f"{sys_prompt}\nUser: {prompt}", "stream": False}
    data = json.dumps(payload).encode()
    resp = urllib.request.urlopen(urllib.request.Request(LLM_URL, data=data))
    out = json.loads(resp.read())["response"].strip()
    return None if out.upper() == "NONE" else out

def embed(text: str) -> np.ndarray:
    payload = {"model": EMBED_MODEL, "prompt": text}
    vec = urllib.request.urlopen(
        urllib.request.Request(EMBED_URL, data=json.dumps(payload).encode())
    ).read()
    return np.asarray(json.loads(vec)["embedding"], dtype=np.float32)

def cosine(a, b): return float(np.dot(a, b) / (np.linalg.norm(a)*np.linalg.norm(b)))

# --------------- Categories / Commands ----------------------
CATEGORIES = {
    "system":  "System-level commands: uptime, free space, assistant name, open browser",
}
CATEGORY_EMB = {k: embed(v) for k, v in CATEGORIES.items()}
COMMAND_EMB  = {
    cat: {n: embed(c["short"]+" "+c["long"]) for n, c in cmds.items()}
    for cat, cmds in commands.items()
}

# --------------- Keyword overrides --------------------------
KEYWORDS = {
    "get_bot_name":   ["your name", "who are you", "name of assistant"],
    "get_bot_age":    ["how old are you", "your age"],
    "get_uptime":     ["uptime", "how long", "system running"],
    "get_free_space": ["free space", "disk space", "storage left"],
    "open_browser":   ["open", "website", "browser", "go to", "search"],
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
    payload = {"model": "tinyllama", "prompt": f"{sys_prompt}\nUser: {prompt}", "stream": False}
    data = json.dumps(payload).encode()
    resp = urllib.request.urlopen(urllib.request.Request(LLM_URL, data=data))
    out = json.loads(resp.read())["response"].strip()
    return None if out.upper() == "NONE" else out

# --------------- GTK Window ----------------------------------
@Gtk.Template(resource_path="/com/azibom/assistant/window.ui")
class AssistantWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "AssistantWindow"

    chat_view = Gtk.Template.Child()
    chat_entry = Gtk.Template.Child()

    def ask_phi(self, prompt: str) -> str:
        try:
            sys_prompt = (
                "You are a helpful assistant. Please answer the user's question clearly but briefly, in 1-2 short sentences. "
                "Do not give long explanations. Be concise."
            )
            phi_payload = {
                "model": "phi:2.7b-chat-v2-q4_0",
                "prompt": f"{sys_prompt}\nUser: {prompt}",
                "stream": False,
                "max_tokens": 100
            }
            data = json.dumps(phi_payload).encode()
            resp = urllib.request.urlopen(urllib.request.Request(LLM_URL, data=data))
            out = json.loads(resp.read())["response"].strip()
            return out
        except Exception as e:
            return f"Failed to get response from phi model: {e}"

    def append(self, who, msg):
        buf = self.chat_view.get_buffer()
        buf.insert(buf.get_end_iter(), f"{who}: {msg}\n")

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
    def on_entry_activate(self, entry):
        text = entry.get_text().strip()
        if not text: return
        self.append("🙋 You", text)
        entry.set_text("…")
        def worker():
            cat = self.pick_category(text)
            GLib.idle_add(self.append, "🔍 Category", cat)

            fn, sim = self.pick_command(text, cat)

            if sim >= COMMAND_THRESHOLD:
                GLib.idle_add(self.append, "🤖 Command", f"run: {fn}() | similarity: {sim:.2%}")
                out = self.run_cmd(fn, cat, text)
                GLib.idle_add(self.append, "🖥️ Output", str(out))
            else:
                GLib.idle_add(self.append, "🤖", f"I don't think this is a command (similarity {sim:.2%}). Let me answer as an assistant...")
                out = self.ask_phi(text)
                GLib.idle_add(self.append, "🖥️ Assistant Answer", out)
        threading.Thread(target=worker, daemon=True).start()

