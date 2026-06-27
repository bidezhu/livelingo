import tkinter as tk
import queue


class SubtitleUI:
    def __init__(self, cfg, on_device_change=None, on_asr_final=None, on_settings=None):
        self.cfg = cfg
        self.on_device_change = on_device_change
        self.on_asr_final = on_asr_final
        self.on_settings = on_settings
        self.root = tk.Tk()
        self.root.title("Live Subtitle")

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_h = cfg.get("window_height", 220)
        self.root.geometry(f"{screen_w}x{win_h}+0+{screen_h - win_h}")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=cfg["bg_color"])

        self._build_ui()
        self._bind_keys()

        self._partial_text = ""
        self._subtitle_pairs = []
        self._status_text = "初始化中..."

    def _build_ui(self):
        cfg = self.cfg

        status_bar = tk.Frame(self.root, bg="#111111", height=32)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)

        self.status_label = tk.Label(
            status_bar, text="初始化中...", bg="#111111", fg="#666666",
            font=("Helvetica", 11), anchor="w",
        )
        self.status_label.pack(side="left", padx=10)

        btn_style = dict(bg="#333333", fg="#999999", font=("Helvetica", 11),
                         relief="flat", padx=10, pady=2, cursor="hand2")

        tk.Button(status_bar, text="退出", command=self.root.destroy,
                  **btn_style).pack(side="right", padx=(0, 10), pady=3)

        tk.Button(status_bar, text="设置", command=self._on_settings_click,
                  **btn_style).pack(side="right", pady=3)

        tk.Button(status_bar, text="麦克风", command=self._on_mic_click,
                  **btn_style).pack(side="right", pady=3)

        self.main_frame = tk.Frame(self.root, bg=cfg["bg_color"])
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        self.text_area = tk.Text(
            self.main_frame,
            bg=cfg["bg_color"],
            fg=cfg["text_color_cn"],
            font=("PingFang SC", cfg["font_size_cn"], "bold"),
            relief="flat",
            wrap="word",
            state="disabled",
            highlightthickness=0,
            spacing1=2,
            spacing3=2,
        )
        self.text_area.pack(fill="both", expand=True)

        self.text_area.tag_configure("cn", font=("PingFang SC", cfg["font_size_cn"], "bold"),
                                     foreground=cfg["text_color_cn"])
        self.text_area.tag_configure("en", font=("PingFang SC", cfg["font_size_en"]),
                                     foreground=cfg["text_color_en"])
        self.text_area.tag_configure("partial", foreground=cfg["text_color_partial"])

    def _bind_keys(self):
        self.root.bind("<Command-q>", lambda e: self.root.destroy())
        self.root.bind("<Command-Up>", lambda e: self._move_window(-30))
        self.root.bind("<Command-Down>", lambda e: self._move_window(30))
        self.root.bind("<Command-h>", lambda e: self._toggle_visibility())
        self.root.bind("<Command-,>", lambda e: self._on_settings_click())

    def _move_window(self, delta):
        geo = self.root.geometry()
        parts = geo.split("+")
        if len(parts) >= 3:
            x, y = int(parts[1]), int(parts[2]) + delta
            self.root.geometry(f"+{x}+{y}")

    def _toggle_visibility(self):
        if self.root.winfo_viewable():
            self.root.withdraw()
        else:
            self.root.deiconify()

    def _on_mic_click(self):
        if self.on_device_change:
            self.on_device_change()

    def _on_settings_click(self):
        if self.on_settings:
            self.on_settings()

    def apply_settings(self, cfg):
        self.cfg = cfg
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_h = cfg.get("window_height", 220)
        self.root.geometry(f"{screen_w}x{win_h}+0+{screen_h - win_h}")

        self.text_area.configure(
            font=("PingFang SC", cfg["font_size_cn"], "bold"),
        )
        self.text_area.tag_configure("cn", font=("PingFang SC", cfg["font_size_cn"], "bold"),
                                     foreground=cfg["text_color_cn"])
        self.text_area.tag_configure("en", font=("PingFang SC", cfg["font_size_en"]),
                                     foreground=cfg["text_color_en"])
        self._render()

    def update_status(self, text):
        self._status_text = text
        self.status_label.config(text=text)

    def update_subtitles(self, partial_text=None, new_pair=None):
        if new_pair:
            self._subtitle_pairs.append(new_pair)
            max_lines = self.cfg.get("max_subtitle_lines", 4)
            if len(self._subtitle_pairs) > max_lines:
                self._subtitle_pairs = self._subtitle_pairs[-max_lines:]

        if partial_text is not None:
            self._partial_text = partial_text

        self._render()

    def _render(self):
        self.text_area.config(state="normal")
        self.text_area.delete("1.0", "end")

        for cn_text, en_text in self._subtitle_pairs:
            self.text_area.insert("end", cn_text + "\n", "cn")
            if en_text:
                self.text_area.insert("end", en_text + "\n", "en")
            self.text_area.insert("end", "\n")

        if self._partial_text:
            last_pair = self._subtitle_pairs[-1] if self._subtitle_pairs else ("", "")
            if self._partial_text != last_pair[0]:
                self.text_area.insert("end", self._partial_text, "partial")

        self.text_area.config(state="disabled")
        self.text_area.see("end")

    def poll_results(self, asr_queue, translator_queue):
        try:
            while True:
                result = asr_queue.get_nowait()
                if result["type"] == "partial":
                    self.update_subtitles(partial_text=result["text"])
                elif result["type"] == "final":
                    text = result["text"]
                    self.update_subtitles(partial_text="")
                    self.update_status(f"识别: {text[:30]}...")
                    if self.on_asr_final:
                        self.on_asr_final(text)
        except queue.Empty:
            pass

        try:
            while True:
                result = translator_queue.get_nowait()
                self.update_subtitles(
                    new_pair=(result["original"], result["translated"])
                )
                self.update_status("翻译完成")
        except queue.Empty:
            pass

        self.root.after(100, self.poll_results, asr_queue, translator_queue)

    def run(self):
        self.root.mainloop()
