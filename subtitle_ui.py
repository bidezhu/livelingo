import queue
import re
import tkinter as tk


THEME = {
    "bg": "#071014",
    "panel": "#0d171c",
    "panel_soft": "#111f26",
    "border": "#1f343d",
    "text": "#f6fbff",
    "muted": "#8fa6af",
    "cn": "#ffffff",
    "en": "#bfe9f0",
    "accent": "#2dd4bf",
    "accent_hover": "#5eead4",
    "amber": "#fbbf24",
    "danger": "#ef4444",
}


ENGLISH_FILLER_RE = re.compile(
    r"\b(?:um+|uh+|er+|ah+|you know|i mean|sort of|kind of)\b[\s,，]*",
    re.IGNORECASE,
)
CHINESE_VOCAL_FILLER_RE = re.compile(
    r"(^|[，。！？；、,\s])(?:嗯+|呃+|额+|啊+|唔+|呣+)(?:[，。！？；、,\s]+)?"
)
CHINESE_DISCOURSE_FILLER_RE = re.compile(
    r"(^|[，。！？；、,\s])(?:这个|那个|就是|就是说|然后|那么)(?:[，、,\s]+)"
)


def clean_subtitle_text(text, remove_fillers=True):
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text or not remove_fillers:
        return text

    text = ENGLISH_FILLER_RE.sub("", text)
    text = CHINESE_VOCAL_FILLER_RE.sub(lambda m: m.group(1), text)
    text = CHINESE_DISCOURSE_FILLER_RE.sub(lambda m: m.group(1), text)
    text = re.sub(r"\s+([,.;:!?，。！？；：])", r"\1", text)
    text = re.sub(r"([，。！？；、])\1+", r"\1", text)
    return re.sub(r"\s+", " ", text).strip(" ，,")


class SubtitleUI:
    def __init__(self, cfg, on_device_change=None, on_asr_final=None, on_settings=None):
        self.cfg = cfg
        self.on_device_change = on_device_change
        self.on_asr_final = on_asr_final
        self.on_settings = on_settings
        self.root = tk.Tk()
        self.root.title("LiveLingo")

        self._fullscreen = False
        self._segments = []
        self._partial_segment = None
        self._max_chars = cfg.get("subtitle_max_chars", 520)
        self._display_segments = cfg.get("display_segments", cfg.get("max_subtitle_lines", 2))
        self._vertical_align = float(cfg.get("subtitle_vertical_align", 0.5))
        self._drag_data = {"x": 0, "y": 0}

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_h = cfg.get("window_height", 220)
        self.root.geometry(f"{screen_w}x{win_h}+0+{screen_h - win_h}")
        self.root.attributes("-topmost", True)
        self.root.configure(bg=THEME["bg"])

        self._build_ui()
        self._build_menus()
        self._bind_keys()
        self._render()

    def _build_ui(self):
        self.main_frame = tk.Frame(self.root, bg=THEME["bg"])
        self.main_frame.pack(fill="both", expand=True, padx=34, pady=(18, 8))

        self.text_area = tk.Text(
            self.main_frame,
            bg=THEME["bg"],
            fg=THEME["text"],
            relief="flat",
            wrap="word",
            state="disabled",
            highlightthickness=0,
            borderwidth=0,
            insertwidth=0,
            cursor="arrow",
            spacing1=4,
            spacing2=2,
            spacing3=10,
        )
        self.text_area.pack(fill="both", expand=True)
        self._configure_text_tags()

        self.control_bar = tk.Frame(self.root, bg=THEME["panel"], height=46)
        self.control_bar.pack(fill="x", side="bottom")
        self.control_bar.pack_propagate(False)

        self.status_pill = tk.Label(
            self.control_bar,
            text="LIVE",
            bg=THEME["accent"],
            fg="#042f2e",
            font=("Helvetica", 10, "bold"),
            padx=10,
            pady=3,
        )
        self.status_pill.pack(side="left", padx=(14, 8), pady=10)

        self._make_control_button("⚙ 设置", self._on_settings_click, accent="amber").pack(
            side="left", padx=(0, 10), pady=7
        )

        self.status_label = tk.Label(
            self.control_bar,
            text="初始化中...",
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Helvetica", 12),
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self._make_control_button("退出", self.root.destroy, danger=True).pack(
            side="right", padx=(4, 14), pady=7
        )
        if self.on_device_change:
            self._make_control_button("音频来源", self.on_device_change).pack(side="right", padx=4, pady=7)
        self._make_control_button("适配", self._fit_screen).pack(side="right", padx=4, pady=7)
        self.fullscreen_btn = self._make_control_button("全屏", self._toggle_fullscreen, primary=True)
        self.fullscreen_btn.pack(side="right", padx=4, pady=7)

    def _make_control_button(self, text, command, primary=False, danger=False, accent=None):
        bg = THEME["accent"] if primary else THEME["panel_soft"]
        fg = "#042f2e" if primary else THEME["text"]
        hover = THEME["accent_hover"] if primary else THEME["border"]
        if accent == "amber":
            bg = THEME["amber"]
            fg = "#3b2601"
            hover = "#fcd34d"
        if danger:
            bg = "#2a1518"
            fg = "#fecaca"
            hover = "#3b1d22"

        btn = tk.Button(
            self.control_bar,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=hover,
            activeforeground=fg,
            font=("Helvetica", 12, "bold" if primary else "normal"),
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=5,
            cursor="hand2",
        )
        btn.bind("<Enter>", lambda _e: btn.configure(bg=hover))
        btn.bind("<Leave>", lambda _e: btn.configure(bg=bg))
        return btn

    def _build_menus(self):
        menu_bar = tk.Menu(self.root)
        app_menu = tk.Menu(menu_bar, tearoff=False)
        app_menu.add_command(label="设置...", accelerator="⌘,", command=self._on_settings_click)
        if self.on_device_change:
            app_menu.add_command(label="音频来源...", command=self.on_device_change)
        app_menu.add_separator()
        app_menu.add_command(label="全屏/窗口", command=self._toggle_fullscreen)
        app_menu.add_command(label="适配屏幕", command=self._fit_screen)
        app_menu.add_separator()
        app_menu.add_command(label="退出", accelerator="⌘Q", command=self.root.destroy)
        menu_bar.add_cascade(label="LiveLingo", menu=app_menu)
        self.root.config(menu=menu_bar)

        self.context_menu = tk.Menu(self.root, tearoff=False)
        self.context_menu.add_command(label="设置...", command=self._on_settings_click)
        if self.on_device_change:
            self.context_menu.add_command(label="音频来源...", command=self.on_device_change)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="全屏/窗口", command=self._toggle_fullscreen)
        self.context_menu.add_command(label="退出", command=self.root.destroy)

    def _bind_keys(self):
        self.root.bind("<Command-q>", lambda e: self.root.destroy())
        self.root.bind("<Command-Up>", lambda e: self._move_window(-30))
        self.root.bind("<Command-Down>", lambda e: self._move_window(30))
        self.root.bind("<Command-h>", lambda e: self._toggle_visibility())
        self.root.bind("<Command-,>", lambda e: self._on_settings_click())
        self.root.bind("<Escape>", lambda e: self._fit_screen())
        self.root.bind("<Button-1>", self._on_drag_start)
        self.root.bind("<B1-Motion>", self._on_drag_motion)
        self.root.bind("<Button-2>", self._show_context_menu)
        self.root.bind("<Button-3>", self._show_context_menu)
        self.root.bind("<Control-Button-1>", self._show_context_menu)
        self.text_area.bind("<Button-1>", self._on_drag_start)
        self.text_area.bind("<B1-Motion>", self._on_drag_motion)
        self.text_area.bind("<Button-2>", self._show_context_menu)
        self.text_area.bind("<Button-3>", self._show_context_menu)
        self.text_area.bind("<Control-Button-1>", self._show_context_menu)

    def _show_context_menu(self, event):
        if hasattr(self, "context_menu"):
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def _font_scale(self):
        if self._fullscreen:
            return float(self.cfg.get("fullscreen_font_scale", 1.35))
        return 1.0

    def _scaled(self, size):
        return max(10, int(size * self._font_scale()))

    def _configure_text_tags(self):
        cn_size = self._scaled(self.cfg["font_size_cn"])
        en_size = self._scaled(self.cfg["font_size_en"])
        prev_cn_size = max(16, int(cn_size * 0.58))
        prev_en_size = max(14, int(en_size * 0.62))
        label_size = max(10, int(en_size * 0.42))
        self.text_area.configure(font=("PingFang SC", cn_size, "bold"))
        self.text_area.tag_configure(
            "cn_label",
            font=("Helvetica", label_size, "bold"),
            foreground=THEME["accent"],
            justify="center",
            spacing1=0,
            spacing3=2,
        )
        self.text_area.tag_configure(
            "cn",
            font=("PingFang SC", cn_size, "bold"),
            foreground=self.cfg.get("text_color_cn", THEME["cn"]),
            justify="center",
            spacing1=0,
            spacing3=8,
        )
        self.text_area.tag_configure(
            "cn_prev",
            font=("PingFang SC", prev_cn_size, "bold"),
            foreground="#8aa0a8",
            justify="center",
            spacing1=0,
            spacing3=4,
        )
        self.text_area.tag_configure(
            "cn_draft",
            font=("PingFang SC", cn_size, "bold"),
            foreground="#d7f8f3",
            justify="center",
            spacing1=0,
            spacing3=8,
        )
        self.text_area.tag_configure(
            "en_label",
            font=("Helvetica", label_size, "bold"),
            foreground=THEME["amber"],
            justify="center",
            spacing1=0,
            spacing3=2,
        )
        self.text_area.tag_configure(
            "en",
            font=("Helvetica", en_size),
            foreground=self.cfg.get("text_color_en", THEME["en"]),
            justify="center",
            spacing1=0,
            spacing3=18,
        )
        self.text_area.tag_configure(
            "en_prev",
            font=("Helvetica", prev_en_size),
            foreground="#78919a",
            justify="center",
            spacing1=0,
            spacing3=12,
        )
        self.text_area.tag_configure(
            "en_draft",
            font=("Helvetica", en_size),
            foreground="#d9f99d",
            justify="center",
            spacing1=0,
            spacing3=18,
        )
        self.text_area.tag_configure(
            "empty",
            font=("PingFang SC", max(18, int(cn_size * 0.62))),
            foreground=THEME["muted"],
            justify="center",
            spacing1=24,
        )
        self.text_area.tag_configure("gap", font=("Helvetica", max(6, en_size // 2)))
        self.text_area.tag_configure(
            "top_pad",
            font=("Helvetica", 1),
            foreground=THEME["bg"],
            justify="center",
            spacing1=0,
            spacing3=0,
        )
        self.text_area.tag_configure(
            "draft_label",
            font=("Helvetica", label_size, "bold"),
            foreground=THEME["amber"],
            justify="center",
            spacing1=0,
            spacing3=4,
        )

    def _on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag_motion(self, event):
        if self._fullscreen:
            return
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    def _move_window(self, delta):
        if self._fullscreen:
            return
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

    def _on_settings_click(self):
        if self.on_settings:
            self.on_settings()

    def _toggle_fullscreen(self):
        if self._fullscreen:
            self._fit_screen()
            return

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_w}x{screen_h}+0+0")
        try:
            self.root.attributes("-fullscreen", True)
        except tk.TclError:
            pass
        self._fullscreen = True
        self.fullscreen_btn.configure(text="窗口")
        self.main_frame.pack_configure(padx=72, pady=(44, 12))
        self.control_bar.configure(height=50)
        self._configure_text_tags()
        self._render()

    def _fit_screen(self):
        try:
            self.root.attributes("-fullscreen", False)
        except tk.TclError:
            pass
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_h = self.cfg.get("window_height", 220)
        self.root.geometry(f"{screen_w}x{win_h}+0+{screen_h - win_h}")
        self._fullscreen = False
        self.fullscreen_btn.configure(text="全屏")
        self.main_frame.pack_configure(padx=34, pady=(18, 8))
        self.control_bar.configure(height=46)
        self._configure_text_tags()
        self._render()

    def apply_settings(self, cfg):
        self.cfg = cfg
        self._max_chars = cfg.get("subtitle_max_chars", self._max_chars)
        self._display_segments = cfg.get("display_segments", cfg.get("max_subtitle_lines", self._display_segments))
        self._vertical_align = float(cfg.get("subtitle_vertical_align", self._vertical_align))

        if not self._fullscreen:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            win_h = cfg.get("window_height", 220)
            self.root.geometry(f"{screen_w}x{win_h}+0+{screen_h - win_h}")

        self._configure_text_tags()
        self._trim_segments()
        self._render()

    def update_status(self, text):
        self.status_label.config(text=text)
        lower_text = text.lower()
        if "错误" in text or "error" in lower_text:
            self.status_pill.configure(text="ERR", bg=THEME["danger"], fg="#fff1f2")
        elif "就绪" in text or "ready" in lower_text or "已切换" in text:
            self.status_pill.configure(text="LIVE", bg=THEME["accent"], fg="#042f2e")
        else:
            self.status_pill.configure(text="RUN", bg=THEME["amber"], fg="#3b2601")

    def add_subtitle(self, cn_text, en_text):
        cn_text = self._limit_text(self._clean_text(cn_text))
        en_text = self._limit_text(self._clean_text(en_text))
        if not cn_text and not en_text:
            return

        segment = {"cn": cn_text, "en": en_text}
        if self._segments and self._segments[-1] == segment:
            self._partial_segment = None
            self._render()
            return

        self._segments.append(segment)
        self._partial_segment = None
        self._trim_segments()
        self._render()

    def update_partial(self, cn_text="", en_text="", direction=""):
        cn_text = self._limit_text(self._clean_text(cn_text))
        en_text = self._limit_text(self._clean_text(en_text))
        if not cn_text and not en_text:
            return

        segment = {"cn": cn_text, "en": en_text, "direction": direction}
        if self._partial_segment == segment:
            return
        self._partial_segment = segment
        self._render()

    def _clean_text(self, text):
        return clean_subtitle_text(text, self.cfg.get("clean_fillers", True))

    def _limit_text(self, text):
        if not text or len(text) <= self._max_chars:
            return text
        return text[-self._max_chars:]

    def _trim_segments(self):
        keep = max(1, int(self._display_segments or 2))
        if len(self._segments) > keep:
            self._segments = self._segments[-keep:]

    def _estimate_content_height(self, render_segments, partial):
        cn_size = self._scaled(self.cfg["font_size_cn"])
        en_size = self._scaled(self.cfg["font_size_en"])
        width = max(520, self.text_area.winfo_width() or self.root.winfo_width() - 80)
        cn_chars_per_line = max(12, int(width / max(18, cn_size * 1.05)))
        en_chars_per_line = max(24, int(width / max(8, en_size * 0.56)))
        height = 0

        def wrapped_lines(text, chars_per_line):
            text = text or ""
            return max(1, (len(text) + chars_per_line - 1) // chars_per_line)

        all_segments = list(render_segments)
        if partial:
            all_segments.append(partial)

        for idx, segment in enumerate(all_segments):
            if segment.get("cn"):
                height += wrapped_lines(segment["cn"], cn_chars_per_line) * int(cn_size * 1.35)
            if segment.get("en"):
                height += wrapped_lines(segment["en"], en_chars_per_line) * int(en_size * 1.4)
            if idx != len(all_segments) - 1:
                height += max(8, int(en_size * 0.45))
        return height

    def _apply_vertical_padding(self, render_segments, partial):
        available = self.text_area.winfo_height()
        if available <= 1:
            available = max(120, self.root.winfo_height() - self.control_bar.winfo_height() - 42)
        content_height = self._estimate_content_height(render_segments, partial)
        free_space = max(0, available - content_height)
        align = min(0.7, max(0.2, self._vertical_align))
        pad = int(free_space * align)
        if pad <= 4:
            return
        self.text_area.tag_configure("top_pad", spacing3=pad)
        self.text_area.insert("end", "\n", "top_pad")

    def _render(self):
        self.text_area.config(state="normal")
        self.text_area.delete("1.0", "end")

        render_segments = list(self._segments)
        partial = self._partial_segment

        if not render_segments and not partial:
            self.text_area.insert("end", "\n等待声音输入\n", "empty")
        else:
            self._apply_vertical_padding(render_segments, partial)
            for idx, segment in enumerate(render_segments):
                is_current = idx == len(render_segments) - 1 and partial is None
                show_labels = self.cfg.get("show_language_labels", False)
                cn_tag = "cn" if is_current else "cn_prev"
                en_tag = "en" if is_current else "en_prev"
                if segment.get("cn"):
                    if show_labels and is_current:
                        self.text_area.insert("end", "中文\n", "cn_label")
                    self.text_area.insert("end", f"{segment['cn']}\n", cn_tag)
                if segment.get("en"):
                    if show_labels and is_current:
                        self.text_area.insert("end", "English\n", "en_label")
                    self.text_area.insert("end", f"{segment['en']}\n", en_tag)
                if idx != len(render_segments) - 1 or partial:
                    self.text_area.insert("end", "\n", "gap")

            if partial:
                show_labels = self.cfg.get("show_language_labels", False)
                if show_labels:
                    self.text_area.insert("end", "实时生成中\n", "draft_label")
                if partial.get("cn"):
                    self.text_area.insert("end", f"{partial['cn']}\n", "cn_draft")
                if partial.get("en"):
                    self.text_area.insert("end", f"{partial['en']}\n", "en_draft")

        self.text_area.config(state="disabled")
        self.text_area.yview_moveto(0.0)

    def poll_results(self, asr_queue, translator_queue):
        try:
            while True:
                result = asr_queue.get_nowait()

                if result.get("type") == "error":
                    self.update_status(f"错误: {result.get('text', '')[:60]}")
                    continue

                if result.get("type") == "partial":
                    cn_text = result.get("cn_text", "")
                    en_text = result.get("en_text", "")
                    if not cn_text and not en_text:
                        text = result.get("text", "") or result.get("source_text", "")
                        translated = result.get("translated", "") or result.get("translated_text", "")
                        display = text if text else translated
                        if display:
                            has_cn = any("\u4e00" <= c <= "\u9fff" for c in display)
                            if has_cn:
                                cn_text = display
                            else:
                                en_text = display
                    if cn_text or en_text:
                        self.update_partial(cn_text, en_text, result.get("direction", ""))
                        status = self._clean_text(cn_text or en_text)
                        self.update_status(f"流式显示: {status[:25]}...")
                    continue

                if result.get("type") != "final":
                    continue

                cn_text = result.get("cn_text", "")
                en_text = result.get("en_text", "")

                if not cn_text and not en_text:
                    text = result.get("text", "")
                    translated = result.get("translated", "")
                    display = text if text else translated
                    if display:
                        has_cn = any("\u4e00" <= c <= "\u9fff" for c in display)
                        if has_cn:
                            cn_text = display
                        else:
                            en_text = display

                if cn_text or en_text:
                    self.add_subtitle(cn_text, en_text)
                    direction = result.get("direction", "")
                    status = self._clean_text(cn_text or en_text)
                    prefix = f"{direction} " if direction else ""
                    self.update_status(f"{prefix}{status[:25]}...")
        except queue.Empty:
            pass

        self.root.after(100, self.poll_results, asr_queue, translator_queue)

    def run(self):
        self.root.mainloop()
