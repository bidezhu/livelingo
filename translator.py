import threading
import queue
import re


class Translator:
    def __init__(self, api_key=None, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                 model="qwen-plus", **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.result_queue = queue.Queue()
        self._thread = None
        self._running = False
        self._input_queue = queue.Queue()
        self._client = None

    def load(self):
        from openai import OpenAI
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def translate(self, text, target_lang=None):
        if target_lang is None:
            cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            en_chars = len(re.findall(r'[a-zA-Z]', text))
            total = cn_chars + en_chars
            src_lang = "zh" if total > 0 and cn_chars / max(total, 1) > 0.3 else "en"
            target_lang = "en" if src_lang == "zh" else "zh"

        if target_lang == "zh":
            prompt = (
                "你是一位专业的会议同声传译。将以下英文翻译成地道的中文。\n"
                "要求：准确、自然、简洁、符合中文表达习惯。只输出翻译结果。\n"
                f"英文：{text}"
            )
        else:
            prompt = (
                "You are a professional conference interpreter. Translate the following Chinese into natural English.\n"
                "Requirements: accurate, natural, concise. Output only the translation.\n"
                f"Chinese: {text}"
            )

        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=256,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"[翻译错误: {e}]"

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._translate_loop, daemon=True)
        self._thread.start()
        threading.Thread(target=self._warmup, daemon=True).start()

    def _warmup(self):
        try:
            self.translate("test")
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
            result = self.translate(text)
            self.result_queue.put({"original": text, "translated": result})
