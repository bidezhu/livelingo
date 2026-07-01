import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os

from config import PUBLIC_HEALTH_HOT_WORDS


PANEL_THEME = {
    "window": "#f4f7fb",
    "surface": "#ffffff",
    "surface_alt": "#f8fafc",
    "border": "#d9e4ec",
    "text": "#102a43",
    "muted": "#627d98",
    "accent": "#0f766e",
    "accent_hover": "#115e59",
    "danger": "#b91c1c",
}


# 热词预设库 - 可扩展
HOT_WORD_PRESETS = {
    "公共卫生强化词库": PUBLIC_HEALTH_HOT_WORDS,
    "UNICEF 含糖饮料税 (SSB Tax)": {
        # 组织机构
        "联合国儿童基金会": "UNICEF",
        "联合国": "United Nations",
        "世界卫生组织": "WHO",
        "东盟": "ASEAN",
        # 核心政策术语
        "含糖饮料": "sugar-sweetened beverages (SSBs)",
        "含糖饮料税": "SSB tax",
        "糖税": "sugar tax",
        "健康食品财政政策": "healthy food fiscal policies",
        "财政措施": "fiscal measures",
        "税收政策": "tax policy",
        "财政政策": "fiscal policy",
        "消费税": "consumption tax",
        "增值税": "VAT",
        # 健康术语
        "儿童肥胖": "childhood obesity",
        "儿童超重": "childhood overweight",
        "非传染性疾病": "non-communicable diseases (NCDs)",
        "肥胖率": "obesity rate",
        "膳食风险": "dietary risks",
        "糖摄入": "sugar intake",
        "健康促进": "health promotion",
        "公共健康": "public health",
        "健康不平等": "health inequality",
        "生产力损失": "productivity losses",
        # 政策分析术语
        "循证决策": "evidence-to-policy",
        "政策分析": "policy analysis",
        "政策对话": "policy dialogue",
        "政策路径": "policy pathways",
        "政策窗口": "policy windows",
        "利益相关方": "stakeholders",
        "利益相关方映射": "stakeholder mapping",
        "敏感性分析": "sensitivity analysis",
        "缓解措施": "mitigation approaches",
        "行为经济学": "behavioral economics",
        "社会决定因素": "social determinants",
        "食品环境": "food environment",
        "行业重新配方": "industry reformulation",
        "证据简报": "evidence briefs",
        "技术咨询": "technical consultation",
        "政策路线图": "policy roadmap",
        # 会议相关
        "闭门会": "closed-door consultation",
        "专家对话": "expert dialogue",
        "技术文件": "technical factsheet",
    },
    "通用医学/公共卫生": {
        "临床试验": "clinical trial",
        "随机对照试验": "randomized controlled trial (RCT)",
        "队列研究": "cohort study",
        "荟萃分析": "meta-analysis",
        "系统综述": "systematic review",
        "发病率": "incidence rate",
        "患病率": "prevalence rate",
        "死亡率": "mortality rate",
        "相对风险": "relative risk",
        "优势比": "odds ratio",
        "置信区间": "confidence interval",
        "统计显著性": "statistical significance",
        "因果关系": "causal relationship",
        "相关性": "correlation",
        "干预措施": "intervention",
        "暴露因素": "exposure factor",
        "混杂因素": "confounding factor",
        "亚组分析": "subgroup analysis",
        "敏感性分析": "sensitivity analysis",
        "成本效益分析": "cost-effectiveness analysis",
        "质量调整生命年": "quality-adjusted life year (QALY)",
        "伤残调整生命年": "disability-adjusted life year (DALY)",
    },
    "教育/学术交流": {
        "双一流": "Double First-Class initiative",
        "国家重点实验室": "State Key Laboratory",
        "自然科学基金": "National Natural Science Foundation of China (NSFC)",
        "博士后流动站": "post-doctoral research station",
        "学科评估": "discipline evaluation",
        "产学研合作": "industry-university-research collaboration",
        "学术诚信": "academic integrity",
        "同行评审": "peer review",
        "影响因子": "impact factor",
        "引用次数": "citation count",
        "开放获取": "open access",
        "预印本": "preprint",
    },
}


class SettingsPanel:
    def __init__(self, cfg, on_apply=None, on_device_change=None):
        self.cfg = cfg
        self.on_apply = on_apply
        self.on_device_change = on_device_change
        self._load_custom_presets()

    def _load_custom_presets(self):
        try:
            preset_file = os.path.expanduser("~/.livelingo/hot_word_presets.json")
            if os.path.exists(preset_file):
                with open(preset_file, "r", encoding="utf-8") as f:
                    HOT_WORD_PRESETS.update(json.load(f))
        except Exception as e:
            print(f"加载自定义预设失败: {e}", flush=True)

    def _style_ttk(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=PANEL_THEME["window"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(16, 8),
            font=("Helvetica", 12),
            background=PANEL_THEME["surface_alt"],
            foreground=PANEL_THEME["muted"],
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", PANEL_THEME["surface"])],
            foreground=[("selected", PANEL_THEME["accent"])],
        )
        style.configure("TSeparator", background=PANEL_THEME["border"])

    def _tab(self, notebook):
        frame = tk.Frame(notebook, bg=PANEL_THEME["surface"], padx=22, pady=18)
        return frame

    def _section_title(self, parent, title, subtitle=None):
        tk.Label(
            parent,
            text=title,
            font=("Helvetica", 16, "bold"),
            bg=PANEL_THEME["surface"],
            fg=PANEL_THEME["text"],
        ).pack(anchor="w")
        if subtitle:
            tk.Label(
                parent,
                text=subtitle,
                font=("Helvetica", 11),
                bg=PANEL_THEME["surface"],
                fg=PANEL_THEME["muted"],
            ).pack(anchor="w", pady=(4, 14))
        else:
            ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(8, 14))

    def _entry(self, parent, variable, show=None):
        entry = tk.Entry(
            parent,
            textvariable=variable,
            show=show,
            font=("Helvetica", 12),
            bg=PANEL_THEME["surface_alt"],
            fg=PANEL_THEME["text"],
            insertbackground=PANEL_THEME["accent"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=PANEL_THEME["border"],
            highlightcolor=PANEL_THEME["accent"],
        )
        entry.pack(fill="x", pady=(4, 10), ipady=6)
        return entry

    def _button(self, parent, text, command, primary=False, danger=False):
        bg = PANEL_THEME["accent"] if primary else PANEL_THEME["surface_alt"]
        fg = "#ffffff" if primary else PANEL_THEME["text"]
        active = PANEL_THEME["accent_hover"] if primary else PANEL_THEME["border"]
        if danger:
            fg = PANEL_THEME["danger"]
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground="#ffffff" if primary else fg,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Helvetica", 12, "bold" if primary else "normal"),
            padx=14,
            pady=7,
        )
        return btn

    def _scale_row(self, parent, label, variable, start, end, resolution=1, value_suffix=""):
        row = tk.Frame(parent, bg=PANEL_THEME["surface"])
        row.pack(fill="x", pady=8)
        value_label = tk.Label(
            row,
            text=f"{variable.get()}{value_suffix}",
            width=8,
            anchor="e",
            bg=PANEL_THEME["surface"],
            fg=PANEL_THEME["muted"],
            font=("Helvetica", 11),
        )
        tk.Label(
            row,
            text=label,
            width=14,
            anchor="w",
            bg=PANEL_THEME["surface"],
            fg=PANEL_THEME["text"],
            font=("Helvetica", 12),
        ).pack(side="left")
        scale = tk.Scale(
            row,
            from_=start,
            to=end,
            resolution=resolution,
            orient="horizontal",
            variable=variable,
            bg=PANEL_THEME["surface"],
            fg=PANEL_THEME["muted"],
            troughcolor=PANEL_THEME["border"],
            activebackground=PANEL_THEME["accent"],
            highlightthickness=0,
            relief="flat",
            showvalue=False,
        )
        scale.pack(side="left", fill="x", expand=True, padx=10)
        value_label.pack(side="right")

        def update_value(*_args):
            value = variable.get()
            if isinstance(value, float):
                value = round(value, 1)
            value_label.configure(text=f"{value}{value_suffix}")

        variable.trace_add("write", update_value)
        return scale

    def show(self, parent=None):
        win = tk.Toplevel(parent) if parent else tk.Tk()
        self._style_ttk()
        win.title("LiveLingo 设置")
        win.geometry("680x720")
        win.resizable(True, True)
        win.attributes("-topmost", True)
        win.configure(bg=PANEL_THEME["window"])

        root = tk.Frame(win, bg=PANEL_THEME["window"], padx=16, pady=16)
        root.pack(fill="both", expand=True)

        header = tk.Frame(root, bg=PANEL_THEME["window"])
        header.pack(fill="x", pady=(0, 12))
        tk.Label(
            header,
            text="LiveLingo 设置",
            font=("Helvetica", 20, "bold"),
            bg=PANEL_THEME["window"],
            fg=PANEL_THEME["text"],
        ).pack(anchor="w")
        tk.Label(
            header,
            text="API、音频来源、字幕显示和翻译分段都可以在这里调整。",
            font=("Helvetica", 11),
            bg=PANEL_THEME["window"],
            fg=PANEL_THEME["muted"],
        ).pack(anchor="w", pady=(3, 0))

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        api_key_var = tk.StringVar(value=self.cfg.get("api_key", ""))
        engine_var = tk.StringVar(value=self.cfg.get("engine_type", "livetranslate"))
        model_var = tk.StringVar(value=self.cfg.get("livetranslate_model", "qwen3.5-livetranslate-flash-realtime"))
        language_mode_var = tk.StringVar(value=self.cfg.get("language_mode", "auto"))
        show_key_var = tk.BooleanVar(value=False)

        api_tab = self._tab(notebook)
        notebook.add(api_tab, text="API")
        self._section_title(api_tab, "API 与模型", "更换百炼 API Key 后会自动重启同传引擎。")
        tk.Label(api_tab, text="DashScope / 百炼 API Key", bg=PANEL_THEME["surface"], fg=PANEL_THEME["text"], font=("Helvetica", 12)).pack(anchor="w")
        api_entry = self._entry(api_tab, api_key_var, show="*")

        def toggle_key():
            api_entry.configure(show="" if show_key_var.get() else "*")

        tk.Checkbutton(
            api_tab,
            text="显示 API Key",
            variable=show_key_var,
            command=toggle_key,
            bg=PANEL_THEME["surface"],
            fg=PANEL_THEME["text"],
            activebackground=PANEL_THEME["surface"],
            selectcolor=PANEL_THEME["surface"],
            font=("Helvetica", 11),
        ).pack(anchor="w", pady=(0, 12))
        tk.Label(api_tab, text="实时同传模型", bg=PANEL_THEME["surface"], fg=PANEL_THEME["text"], font=("Helvetica", 12)).pack(anchor="w")
        self._entry(api_tab, model_var)
        tk.Radiobutton(api_tab, text="实时同传 qwen3.5-livetranslate-flash-realtime", variable=engine_var, value="livetranslate", bg=PANEL_THEME["surface"], fg=PANEL_THEME["text"], activebackground=PANEL_THEME["surface"], selectcolor=PANEL_THEME["surface"]).pack(anchor="w")
        tk.Radiobutton(api_tab, text="传统 ASR+翻译（保留兼容）", variable=engine_var, value="legacy", bg=PANEL_THEME["surface"], fg=PANEL_THEME["text"], activebackground=PANEL_THEME["surface"], selectcolor=PANEL_THEME["surface"]).pack(anchor="w")

        ttk.Separator(api_tab, orient="horizontal").pack(fill="x", pady=(16, 14))
        tk.Label(api_tab, text="发言语言", bg=PANEL_THEME["surface"], fg=PANEL_THEME["text"], font=("Helvetica", 12, "bold")).pack(anchor="w")
        for label, value in (
            ("智能中英互译（双通道）", "auto"),
            ("中文发言为主（中译英，更稳）", "zh"),
            ("英文发言为主（英译中，更稳）", "en"),
        ):
            tk.Radiobutton(
                api_tab,
                text=label,
                variable=language_mode_var,
                value=value,
                bg=PANEL_THEME["surface"],
                fg=PANEL_THEME["text"],
                activebackground=PANEL_THEME["surface"],
                selectcolor=PANEL_THEME["surface"],
                font=("Helvetica", 11),
            ).pack(anchor="w", pady=(4, 0))
        tk.Label(
            api_tab,
            text="单语为主模式只开启一个实时会话，英文报告或中文报告会更顺滑，也更不容易触发限流。",
            bg=PANEL_THEME["surface"],
            fg=PANEL_THEME["muted"],
            font=("Helvetica", 11),
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        audio_tab = self._tab(notebook)
        notebook.add(audio_tab, text="音频")
        self._section_title(audio_tab, "音频来源", "可在会议中切换麦克风、系统音频或混合输入。")
        mode_text = {"microphone": "麦克风", "system": "系统音频", "both": "麦克风+系统音频"}
        device_label = tk.Label(
            audio_tab,
            text=f"当前来源：{self.cfg.get('device_name', '未选择')} / {mode_text.get(self.cfg.get('capture_mode', 'microphone'), '麦克风')}",
            bg=PANEL_THEME["surface_alt"],
            fg=PANEL_THEME["text"],
            font=("Helvetica", 13),
            padx=14,
            pady=12,
            anchor="w",
        )
        device_label.pack(fill="x", pady=(0, 12))

        def change_device():
            if self.on_device_change:
                def refresh_label(_success=False):
                    device_label.configure(
                        text=f"当前来源：{self.cfg.get('device_name', '未选择')} / {mode_text.get(self.cfg.get('capture_mode', 'microphone'), '麦克风')}"
                    )

                try:
                    self.on_device_change(parent=win, on_done=refresh_label)
                except TypeError:
                    self.on_device_change()

        self._button(audio_tab, "选择音频来源", change_device, primary=True).pack(anchor="w")
        tk.Label(
            audio_tab,
            text="提示：如果播放线上会议声音，请选择系统音频；如果同时需要现场发言和电脑声音，可选择混合输入。",
            bg=PANEL_THEME["surface"],
            fg=PANEL_THEME["muted"],
            font=("Helvetica", 11),
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(14, 0))

        font_size_cn_var = tk.IntVar(value=self.cfg.get("font_size_cn", 30))
        font_size_en_var = tk.IntVar(value=self.cfg.get("font_size_en", 24))
        display_segments_var = tk.IntVar(value=self.cfg.get("display_segments", self.cfg.get("max_subtitle_lines", 2)))
        window_height_var = tk.IntVar(value=self.cfg.get("window_height", 360))
        fullscreen_scale_var = tk.DoubleVar(value=self.cfg.get("fullscreen_font_scale", 1.25))
        subtitle_max_chars_var = tk.IntVar(value=self.cfg.get("subtitle_max_chars", 520))
        show_labels_var = tk.BooleanVar(value=self.cfg.get("show_language_labels", False))
        clean_fillers_var = tk.BooleanVar(value=self.cfg.get("clean_fillers", True))
        vertical_align_var = tk.DoubleVar(value=self.cfg.get("subtitle_vertical_align", 0.5))

        display_tab = self._tab(notebook)
        notebook.add(display_tab, text="显示")
        self._section_title(display_tab, "字幕显示", "最新段落更醒目，上一段会自动弱化作为上下文。")
        self._scale_row(display_tab, "中文字号", font_size_cn_var, 18, 56)
        self._scale_row(display_tab, "英文字号", font_size_en_var, 14, 44)
        self._scale_row(display_tab, "显示段落", display_segments_var, 1, 3)
        self._scale_row(display_tab, "段落长度", subtitle_max_chars_var, 260, 900, 20, " 字")
        self._scale_row(display_tab, "窗口高度", window_height_var, 180, 620, 10)
        self._scale_row(display_tab, "全屏缩放", fullscreen_scale_var, 1.0, 1.6, 0.05, "x")
        self._scale_row(display_tab, "垂直位置", vertical_align_var, 0.35, 0.65, 0.01)
        tk.Checkbutton(
            display_tab,
            text="过滤口气词",
            variable=clean_fillers_var,
            bg=PANEL_THEME["surface"],
            fg=PANEL_THEME["text"],
            activebackground=PANEL_THEME["surface"],
            selectcolor=PANEL_THEME["surface"],
            font=("Helvetica", 12),
        ).pack(anchor="w", pady=(12, 0))
        tk.Checkbutton(
            display_tab,
            text="显示中文 / English 标签",
            variable=show_labels_var,
            bg=PANEL_THEME["surface"],
            fg=PANEL_THEME["text"],
            activebackground=PANEL_THEME["surface"],
            selectcolor=PANEL_THEME["surface"],
            font=("Helvetica", 12),
        ).pack(anchor="w", pady=(12, 0))

        segment_sentences_var = tk.IntVar(value=self.cfg.get("segment_sentences", 3))
        min_segment_var = tk.DoubleVar(value=self.cfg.get("min_segment_seconds", 3.0))
        max_segment_var = tk.DoubleVar(value=self.cfg.get("max_segment_seconds", 20.0))
        silence_var = tk.DoubleVar(value=self.cfg.get("silence_timeout", 1.2))

        segment_tab = self._tab(notebook)
        notebook.add(segment_tab, text="分段")
        self._section_title(segment_tab, "翻译分段", "句数和最长时长越大，每段字幕越长，延迟也会略高。")
        self._scale_row(segment_tab, "每段句数", segment_sentences_var, 2, 5)
        self._scale_row(segment_tab, "最短时长", min_segment_var, 2.0, 8.0, 0.5, " 秒")
        self._scale_row(segment_tab, "最长时长", max_segment_var, 10.0, 40.0, 1.0, " 秒")
        self._scale_row(segment_tab, "静音断句", silence_var, 0.5, 3.0, 0.1, " 秒")

        hot_words_tab = self._tab(notebook)
        notebook.add(hot_words_tab, text="热词")
        self._section_title(hot_words_tab, "热词与术语", "每行一个：源词=目标词。保存后会重启同传引擎。")

        preset_row = tk.Frame(hot_words_tab, bg=PANEL_THEME["surface"])
        preset_row.pack(fill="x", pady=(0, 10))
        preset_var = tk.StringVar(value="选择预设...")
        preset_combo = ttk.Combobox(
            preset_row,
            textvariable=preset_var,
            values=list(HOT_WORD_PRESETS.keys()),
            state="readonly",
            width=36,
        )
        preset_combo.pack(side="left")

        hot_words_text = tk.Text(
            hot_words_tab,
            height=14,
            font=("Helvetica", 11),
            bg=PANEL_THEME["surface_alt"],
            fg=PANEL_THEME["text"],
            insertbackground=PANEL_THEME["accent"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=PANEL_THEME["border"],
            highlightcolor=PANEL_THEME["accent"],
        )
        hot_words_text.pack(fill="both", expand=True)

        if self.cfg.get("hot_words"):
            hot_words_text.insert("1.0", "\n".join(f"{k}={v}" for k, v in self.cfg.get("hot_words", {}).items()))

        def load_preset():
            selected = preset_var.get()
            if selected in HOT_WORD_PRESETS:
                current_text = hot_words_text.get("1.0", tk.END).strip()
                new_text = "\n".join(f"{k}={v}" for k, v in HOT_WORD_PRESETS[selected].items())
                hot_words_text.delete("1.0", tk.END)
                hot_words_text.insert("1.0", f"{current_text}\n{new_text}".strip())

        def clear_hot_words():
            if messagebox.askyesno("确认", "确定要清空所有热词吗？", parent=win):
                hot_words_text.delete("1.0", tk.END)

        def save_as_preset():
            name = simpledialog.askstring("保存预设", "请输入预设名称：", parent=win)
            if not name:
                return
            preset = self._parse_hot_words(hot_words_text.get("1.0", tk.END))
            if preset:
                HOT_WORD_PRESETS[name] = preset
                preset_combo["values"] = list(HOT_WORD_PRESETS.keys())
                preset_file = os.path.expanduser("~/.livelingo/hot_word_presets.json")
                os.makedirs(os.path.dirname(preset_file), exist_ok=True)
                with open(preset_file, "w", encoding="utf-8") as f:
                    json.dump(HOT_WORD_PRESETS, f, ensure_ascii=False, indent=2)

        hot_btn_row = tk.Frame(hot_words_tab, bg=PANEL_THEME["surface"])
        hot_btn_row.pack(fill="x", pady=(12, 0))
        self._button(hot_btn_row, "加载预设", load_preset).pack(side="left", padx=(0, 8))
        self._button(hot_btn_row, "清空热词", clear_hot_words, danger=True).pack(side="left", padx=(0, 8))
        self._button(hot_btn_row, "保存为预设", save_as_preset).pack(side="left")

        footer = tk.Frame(root, bg=PANEL_THEME["window"])
        footer.pack(fill="x", pady=(12, 0))

        def on_apply():
            new_cfg = dict(self.cfg)
            new_cfg["api_key"] = api_key_var.get().strip()
            new_cfg["engine_type"] = engine_var.get()
            new_cfg["livetranslate_model"] = model_var.get().strip() or "qwen3.5-livetranslate-flash-realtime"
            new_cfg["language_mode"] = language_mode_var.get()
            new_cfg["font_size_cn"] = font_size_cn_var.get()
            new_cfg["font_size_en"] = font_size_en_var.get()
            new_cfg["display_segments"] = display_segments_var.get()
            new_cfg["max_subtitle_lines"] = display_segments_var.get()
            new_cfg["window_height"] = window_height_var.get()
            new_cfg["fullscreen_font_scale"] = fullscreen_scale_var.get()
            new_cfg["subtitle_max_chars"] = subtitle_max_chars_var.get()
            new_cfg["clean_fillers"] = clean_fillers_var.get()
            new_cfg["subtitle_vertical_align"] = vertical_align_var.get()
            new_cfg["show_language_labels"] = show_labels_var.get()
            new_cfg["segment_sentences"] = segment_sentences_var.get()
            new_cfg["min_segment_seconds"] = min_segment_var.get()
            new_cfg["max_segment_seconds"] = max_segment_var.get()
            new_cfg["silence_timeout"] = silence_var.get()
            new_cfg["hot_words"] = self._parse_hot_words(hot_words_text.get("1.0", tk.END))
            if self.on_apply:
                self.on_apply(new_cfg)
            self.cfg.update(new_cfg)
            win.destroy()

        self._button(footer, "取消", win.destroy).pack(side="right", padx=(8, 0))
        self._button(footer, "应用设置", on_apply, primary=True).pack(side="right")

        if parent:
            win.transient(parent)
            win.lift()
            win.focus_force()
        else:
            win.mainloop()
        return win

    @staticmethod
    def _parse_hot_words(raw_text):
        hot_words = {}
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                hot_words[key] = value
        return hot_words
