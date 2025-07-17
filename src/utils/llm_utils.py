import json
import urllib.request
import urllib.error
import numpy as np
import re


class LLMClient:
    def __init__(
        self,
        window,
        ollama_url="http://localhost:11434",
        api_endpoint="/api",
        embed_model="nomic-embed-text",
        llm_model="phi:2.7b-chat-v2-q4_0",
    ):
        self.window = window
        self.base_url = ollama_url
        self.api_url = f"{ollama_url}{api_endpoint}"
        self.tags_url = f"{ollama_url}/api/tags"
        self.embed_model = embed_model
        self.llm_model = llm_model
        self.is_ollama_connected = False

    def set_ollama_connected(self, status: bool):
        if status is True and self.is_ollama_connected is False:
            self.is_ollama_connected = True
            self.window.cmd_utils.refresh_embeddings()
        self.is_ollama_connected = status

    def check_connection(self) -> bool:
        """
        Checks if a local Ollama instance is running 
        and has the required model.
        Updates self.is_ollama_connected accordingly.
        Returns True if the model is present, False otherwise.
        """

        try:
            with urllib.request.urlopen(self.tags_url, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read())
                    local_models = [
                        model["name"].split(":")[0] for model in data.get("models", [])
                    ]
                    if self.embed_model in local_models:
                        self.set_ollama_connected(True)
                        return True
                    else:
                        self.set_ollama_connected(False)
                        return False
                else:
                    self.set_ollama_connected(False)
                    return False
        except urllib.error.URLError:
            self.set_ollama_connected(False)
            return False
        except json.JSONDecodeError:
            self.set_ollama_connected(False)
            return False
        except Exception:
            self.set_ollama_connected(False)
            return False

    def _send_request(
        self, endpoint: str, payload: dict
    ) -> tuple[dict | None, str | None]:
        # ... (This method remains the same as the previous version)
        try:
            url = f"{self.api_url}{endpoint}"
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req) as response:
                self.set_ollama_connected(True)
                return json.loads(response.read()), None
        except urllib.error.URLError as e:
            self.set_ollama_connected(False)
            err_msg = f"Ollama server is down or not reachable at {self.base_url}. Error: {e.reason}"
            return None, err_msg
        except Exception as e:
            self.set_ollama_connected(False)
            err_msg = f"An unexpected error occurred: {e}"
            return None, err_msg

    def extract_argument(
        self, prompt: str, arg_description: str
    ) -> tuple[str | None, str | None]:
        sys_prompt = (
            f"You are an assistant extracting argument values from user input.\n"
            f"Argument: {arg_description}\n"
            f"User may provide the argument directly or implicitly.\n"
            f"Respond ONLY with the final value or the single word: NONE.\n"
        )
        payload = {
            "model": self.llm_model,
            "prompt": f"{sys_prompt}\nUser: {prompt}",
            "stream": False,
            "max_tokens": 100,
        }

        result, err = self._send_request("/generate", payload)
        if err:
            return None, err

        out = result.get("response", "").strip()
        final_val = None if out.upper() == "NONE" else out
        return final_val, None

    def embed(self, text: str) -> tuple[np.ndarray | None, str | None]:
        payload = {"model": self.embed_model, "prompt": text}
        result, err = self._send_request("/embeddings", payload)

        if err:
            return None, err

        embedding = result.get("embedding")
        if embedding:
            return np.asarray(embedding, dtype=np.float32), None
        return None, "Failed to get embedding from the response."

    @staticmethod
    def cosine(a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def ask_llm(self, prompt: str) -> tuple[str | None, str | None]:
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

        result, err = self._send_request("/generate", phi_payload)
        if err:
            return None, err

        response = result.get("response", "No response from LLM.").strip()
        return response, None

    def extract_url(self, prompt: str) -> tuple[str | None, str | None]:
        url_regex = r"(https?://[^\s]+)"
        m = re.search(url_regex, prompt)
        if m:
            return m.group(1), None

        sys_prompt = (
            "Extract the first valid URL from the user's request. "
            "Respond ONLY with the URL or, if no URL present, the single word: NONE."
        )
        payload = {
            "model": "tinyllama",
            "prompt": f"{sys_prompt}\nUser: {prompt}",
            "stream": False,
        }

        result, err = self._send_request("/generate", payload)
        if err:
            return None, err

        out = result.get("response", "").strip()
        final_val = None if out.upper() == "NONE" else out
        return final_val, None
