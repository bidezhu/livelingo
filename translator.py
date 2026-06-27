import threading
import queue
import requests
import re


def _detect_language(text):
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    en_chars = len(re.findall(r'[a-zA-Z]', text))
    total = cn_chars + en_chars
    if total == 0:
        return "zh"
    return "zh" if cn_chars / total > 0.3 else "en"


class Translator:
    def __init__(self, model="qwen3.5:9b", base_url="http://localhost:11434"):
        self.model = model
        self.api_url = f"{base_url}/api/chat"
        self.tags_url = f"{base_url}/api/tags"
        self.result_queue = queue.Queue()
        self._thread = None
        self._running = False
        self._input_queue = queue.Queue()

    def check_available(self):
        try:
            resp = requests.get(self.tags_url, timeout=3)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return any(self.model in m for m in models)
        except Exception:
            pass
        return False

    def translate(self, text, target_lang=None):
        if target_lang is None:
            src_lang = _detect_language(text)
            target_lang = "en" if src_lang == "zh" else "zh"

        lang_name = "英文" if target_lang == "en" else "中文"
        if target_lang == "zh":
            prompt = (
                f"你是一位专业的会议同声传译。将以下英文翻译成地道的中文。\n"
                f"要求：准确、自然、简洁、符合中文表达习惯。只输出翻译结果。\n"
                f"英文：{text}"
            )
        else:
            prompt = (
                f"You are a professional conference interpreter. Translate the following Chinese into natural English.\n"
                f"Requirements: accurate, natural, concise. Output only the translation.\n"
                f"Chinese: {text}"
            )

        try:
            resp = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0.1, "num_predict": 256},
                },
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "").strip()
                return content if content else "[翻译为空]"
        except Exception as e:
            return f"[翻译错误: {e}]"
        return "[翻译失败]"

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._translate_loop, daemon=True)
        self._thread.start()
        threading.Thread(target=self._warmup, daemon=True).start()

    def _warmup(self):
        try:
            self.translate("你好")
        except Exception:
            pass

    def stop(self):
        self._running = False

    def submit(self, text):
        self._input_queue.put(text)

    def _translate_loop(self):
        while self._running:
            try:
                text = self._input_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if text is None:
                continue
            print(f"[翻译] 收到: {text[:40]}...", flush=True)
            result = self.translate(text)
            print(f"[翻译] 结果: {result[:40]}...", flush=True)
            self.result_queue.put({"original": text, "translated": result})
