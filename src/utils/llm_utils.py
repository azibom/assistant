import json
import urllib.request
import numpy as np
import re


class LLMClient:
    def __init__(
        self,
        ollama_url="http://localhost:11434/api",
        embed_model="nomic-embed-text",
        llm_model="phi:2.7b-chat-v2-q4_0",
    ):
        self.ollama_url = ollama_url
        self.embed_model = embed_model
        self.llm_model = llm_model

    def extract_argument(self, prompt: str, arg_description: str) -> str | None:
        try:
            sys_prompt = (
                f"You are an assistant extracting argument values from user input.\n"
                f"Argument: {arg_description}\n"
                f"User may provide the argument directly or implicitly.\n"
                f"For example, if the user says 'open Facebook', "
                f"you should respond with 'https://facebook.com'.\n"
                f"Respond ONLY with the final value or the single word: NONE.\n"
            )
            payload = {
                "model": self.llm_model,
                "prompt": f"{sys_prompt}\nUser: {prompt}",
                "stream": False,
                "max_tokens": 100,
            }
            data = json.dumps(payload).encode()
            req = urllib.request.Request(f"{self.ollama_url}/generate", data=data)
            resp = urllib.request.urlopen(req)
            out = json.loads(resp.read())["response"].strip()
            return None if out.upper() == "NONE" else out
        except Exception as e:
            return f"Failed to get response from LLM: {e}"

    def embed(self, text: str) -> np.ndarray:
        payload = {"model": self.embed_model, "prompt": text}
        req = urllib.request.Request(
            f"{self.ollama_url}/embeddings", data=json.dumps(payload).encode()
        )
        vec = urllib.request.urlopen(req).read()
        return np.asarray(json.loads(vec)["embedding"], dtype=np.float32)

    @staticmethod
    def cosine(a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def ask_llm(self, prompt: str) -> str:
        try:
            sys_prompt = (
                "You are a helpful assistant. Please answer the user's question "
                "clearly but briefly, in 1-2 short sentences. "
                "Do not give long explanations. Be concise."
            )
            phi_payload = {
                "model": self.llm_model,
                "prompt": f"{sys_prompt}\nUser: {prompt}",
                "stream": False,
                "max_tokens": 100,
            }
            data = json.dumps(phi_payload).encode()
            req = urllib.request.Request(f"{self.ollama_url}/generate", data=data)
            resp = urllib.request.urlopen(req)
            out = json.loads(resp.read())["response"].strip()
            return out
        except Exception as e:
            return f"Failed to get response from LLM: {e}"

    def extract_url(self, prompt: str) -> str | None:
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
        req = urllib.request.Request(f"{self.ollama_url}/generate", data=data)
        resp = urllib.request.urlopen(req)
        out = json.loads(resp.read())["response"].strip()
        return None if out.upper() == "NONE" else out
