import tkinter as tk
from tkinter import ttk


class SettingsPanel:
    def __init__(self, cfg, on_apply=None):
        self.cfg = cfg
        self.on_apply = on_apply

    def show(self, parent=None):
        if parent:
            win = tk.Toplevel(parent)
        else:
            win = tk.Tk()
        win.title("设置")
        win.geometry("460x580")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        self._win = win

        canvas = tk.Canvas(win, highlightthickness=0)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frame = tk.Frame(scroll_frame, padx=20, pady=15)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="API 设置", font=("Helvetica", 16, "bold")).pack(anchor="w")
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(5, 10))

        tk.Label(frame, text="API Key", font=("Helvetica", 12), anchor="w").pack(anchor="w")
        api_key_var = tk.StringVar(value=self.cfg.get("api_key", ""))
        api_entry = tk.Entry(frame, textvariable=api_key_var, font=("Helvetica", 11),
                             show="*", width=50)
        api_entry.pack(fill="x", pady=(2, 5))

        tk.Label(frame, text="百炼控制台: bailian.console.aliyun.com",
                 font=("Helvetica", 10), fg="#666666").pack(anchor="w")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(15, 10))

        tk.Label(frame, text="字幕设置", font=("Helvetica", 16, "bold")).pack(anchor="w")
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(5, 10))

        row1 = tk.Frame(frame)
        row1.pack(fill="x", pady=5)
        tk.Label(row1, text="中文字号", font=("Helvetica", 13), width=12, anchor="w").pack(side="left")
        cn_size_var = tk.IntVar(value=self.cfg["font_size_cn"])
        tk.Scale(row1, from_=16, to=48, orient="horizontal",
                 variable=cn_size_var, length=220).pack(side="left", fill="x", expand=True)

        row2 = tk.Frame(frame)
        row2.pack(fill="x", pady=5)
        tk.Label(row2, text="英文字号", font=("Helvetica", 13), width=12, anchor="w").pack(side="left")
        en_size_var = tk.IntVar(value=self.cfg["font_size_en"])
        tk.Scale(row2, from_=12, to=36, orient="horizontal",
                 variable=en_size_var, length=220).pack(side="left", fill="x", expand=True)

        row3 = tk.Frame(frame)
        row3.pack(fill="x", pady=5)
        tk.Label(row3, text="字幕行数", font=("Helvetica", 13), width=12, anchor="w").pack(side="left")
        lines_var = tk.IntVar(value=self.cfg["max_subtitle_lines"])
        tk.Scale(row3, from_=1, to=8, orient="horizontal",
                 variable=lines_var, length=220).pack(side="left", fill="x", expand=True)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(10, 10))

        tk.Label(frame, text="识别设置", font=("Helvetica", 16, "bold")).pack(anchor="w")
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(5, 10))

        row4 = tk.Frame(frame)
        row4.pack(fill="x", pady=5)
        tk.Label(row4, text="断句静音(秒)", font=("Helvetica", 13), width=12, anchor="w").pack(side="left")
        silence_var = tk.DoubleVar(value=self.cfg.get("silence_timeout", 1.5))
        tk.Scale(row4, from_=0.5, to=5.0, resolution=0.5,
                 orient="horizontal", variable=silence_var, length=220).pack(side="left", fill="x", expand=True)

        row5 = tk.Frame(frame)
        row5.pack(fill="x", pady=5)
        tk.Label(row5, text="窗口高度", font=("Helvetica", 13), width=12, anchor="w").pack(side="left")
        height_var = tk.IntVar(value=self.cfg.get("window_height", 220))
        tk.Scale(row5, from_=120, to=500, orient="horizontal",
                 variable=height_var, length=220).pack(side="left", fill="x", expand=True)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill="x", pady=(20, 0))

        def on_apply():
            self.cfg["api_key"] = api_key_var.get().strip()
            self.cfg["font_size_cn"] = cn_size_var.get()
            self.cfg["font_size_en"] = en_size_var.get()
            self.cfg["max_subtitle_lines"] = lines_var.get()
            self.cfg["silence_timeout"] = silence_var.get()
            self.cfg["window_height"] = height_var.get()
            if self.on_apply:
                self.on_apply(self.cfg)
            win.destroy()

        def on_cancel():
            win.destroy()

        tk.Button(btn_frame, text="应用", command=on_apply,
                  font=("Helvetica", 13), width=10).pack(side="right", padx=(10, 0))
        tk.Button(btn_frame, text="取消", command=on_cancel,
                  font=("Helvetica", 13), width=10).pack(side="right")

        if parent:
            win.grab_set()
            win.wait_window()
        else:
            win.mainloop()
