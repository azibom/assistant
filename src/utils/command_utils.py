from .llm_utils import LLMClient
from ..commands import commands


class CommandUtils:
    def __init__(self, llm_client=None):
        self.llm = llm_client or LLMClient()
        self.CATEGORIES = {
            "system": "System-level commands: uptime, "
            "free space, assistant name, open browser",
        }
        self.CATEGORY_EMB = {}
        self.COMMAND_EMB = {}
        self.KEYWORDS = {
            "get_bot_name": ["your name", "who are you", "name of assistant"],
            "get_bot_age": ["how old are you", "your age"],
            "get_uptime": ["uptime", "how long", "system running"],
            "get_free_space": ["free space", "disk space", "storage left"],
            "open_browser": ["open", "website", "browser", "go to", "search"],
        }
        self.COMMAND_THRESHOLD = 0.70
        self.refresh_embeddings()

    def refresh_embeddings(self):
        self.CATEGORY_EMB = {}
        for k, v in self.CATEGORIES.items():
            emb, err = self.llm.embed(v)
            self.CATEGORY_EMB[k] = emb if err is None else None

        self.COMMAND_EMB = {}
        for cat, cmds in commands.items():
            self.COMMAND_EMB[cat] = {}
            for n, c in cmds.items():
                emb, err = self.llm.embed(c["short"] + " " + c["long"])
                self.COMMAND_EMB[cat][n] = emb if err is None else None

    def pick_category(self, text):
        q, err = self.llm.embed(text)
        if err:
            return None, err
        return (
            max(
                self.CATEGORY_EMB,
                key=lambda c: self.llm.cosine(q, self.CATEGORY_EMB[c]),
            ),
            None,
        )

    def pick_command(self, text, category):
        t = text.lower()
        for fn, words in self.KEYWORDS.items():
            if any(w in t for w in words):
                return fn, 1.0, None
        q, err = self.llm.embed(text)
        if err:
            return None, 0.0, err
        best, best_sim = None, -1.0
        for fn, vec in self.COMMAND_EMB[category].items():
            sim = self.llm.cosine(q, vec)
            if sim > best_sim:
                best, best_sim = fn, sim
        return best, best_sim, None

    def run_cmd(self, fn_name, category, user_text):
        cmd = commands[category][fn_name]
        args_values = []
        if cmd["args"]:
            for arg in cmd["args"]:
                arg_name = arg["name"]
                arg_description = arg["description"]
                result, error = self.llm.extract_argument(user_text, arg_description)
                if error is not None:
                    return (
                        f"Missing argument '{arg_name}' for {fn_name}, error: {error}!"
                    )
                args_values.append(result)
        return cmd["execute"](*args_values)
