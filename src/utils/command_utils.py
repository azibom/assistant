from .llm_utils import LLMClient
from ..commands import commands


class CommandUtils:
    def __init__(self, llm_client=None):
        self.llm = llm_client or LLMClient()
        self.CATEGORIES = {
            "system": "System-level commands: uptime, free space, assistant name, open browser",
        }
        self.CATEGORY_EMB = {k: self.llm.embed(v) for k, v in self.CATEGORIES.items()}
        self.COMMAND_EMB = {
            cat: {
                n: self.llm.embed(c["short"] + " " + c["long"]) for n, c in cmds.items()
            }
            for cat, cmds in commands.items()
        }
        self.KEYWORDS = {
            "get_bot_name": ["your name", "who are you", "name of assistant"],
            "get_bot_age": ["how old are you", "your age"],
            "get_uptime": ["uptime", "how long", "system running"],
            "get_free_space": ["free space", "disk space", "storage left"],
            "open_browser": ["open", "website", "browser", "go to", "search"],
        }
        self.COMMAND_THRESHOLD = 0.70

    def pick_category(self, text):
        q = self.llm.embed(text)
        return max(
            self.CATEGORY_EMB, key=lambda c: self.llm.cosine(q, self.CATEGORY_EMB[c])
        )

    def pick_command(self, text, category):
        t = text.lower()
        for fn, words in self.KEYWORDS.items():
            if any(w in t for w in words):
                return fn, 1.0
        q = self.llm.embed(text)
        best, best_sim = None, -1.0
        for fn, vec in self.COMMAND_EMB[category].items():
            sim = self.llm.cosine(q, vec)
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
                value = self.llm.extract_argument(user_text, arg_description)
                if value is None:
                    return f"Missing argument '{arg_name}' for {fn_name}."
                args_values.append(value)
        return cmd["execute"](*args_values)
