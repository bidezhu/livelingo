import tkinter as tk
from tkinter import ttk


SELECTOR_THEME = {
    "window": "#f4f7fb",
    "surface": "#ffffff",
    "surface_alt": "#f8fafc",
    "border": "#d9e4ec",
    "text": "#102a43",
    "muted": "#627d98",
    "accent": "#0f766e",
    "accent_hover": "#115e59",
}


class DeviceSelector:
    def __init__(self, devices, current_id=None, show_system_audio=True):
        self.devices = devices
        self.current_id = current_id
        self.selected_id = None
        self.selected_name = None
        self.selected_type = "microphone"
        self.show_system_audio = show_system_audio

    def show(self, parent=None):
        if parent:
            win = tk.Toplevel(parent)
        else:
            win = tk.Tk()
        win.title("选择音频输入")
        win.geometry("560x460")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.configure(bg=SELECTOR_THEME["window"])
        self._win = win

        header = tk.Frame(win, bg=SELECTOR_THEME["window"])
        header.pack(padx=22, pady=(18, 12), fill="x")
        tk.Label(
            header,
            text="选择音频输入",
            font=("Helvetica", 18, "bold"),
            bg=SELECTOR_THEME["window"],
            fg=SELECTOR_THEME["text"],
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            header,
            text="麦克风适合现场发言，系统音频适合会议软件或视频播放。",
            font=("Helvetica", 11),
            bg=SELECTOR_THEME["window"],
            fg=SELECTOR_THEME["muted"],
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        # 设备列表
        list_frame = tk.Frame(
            win,
            bg=SELECTOR_THEME["surface"],
            highlightbackground=SELECTOR_THEME["border"],
            highlightthickness=1,
        )
        list_frame.pack(padx=22, pady=5, fill="both", expand=True)

        listbox = tk.Listbox(
            list_frame,
            font=("Helvetica", 12),
            height=12,
            bg=SELECTOR_THEME["surface"],
            fg=SELECTOR_THEME["text"],
            selectbackground=SELECTOR_THEME["accent"],
            selectforeground="#ffffff",
            activestyle="none",
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        row_map = {}

        # 添加麦克风设备
        mic_devices = [d for d in self.devices if d.get("type") == "microphone"]
        system_devices = [d for d in self.devices if d.get("type") == "system"]

        if mic_devices:
            listbox.insert(tk.END, "── 麦克风 ──")
            for d in mic_devices:
                label_text = f"  🎤 {d['name']}"
                listbox.insert(tk.END, label_text)
                row_map[listbox.size() - 1] = ("microphone", d)

        if system_devices and self.show_system_audio:
            listbox.insert(tk.END, "")
            listbox.insert(tk.END, "── 系统音频 ──")
            for d in system_devices:
                label_text = f"  🔊 {d['name']}"
                listbox.insert(tk.END, label_text)
                row_map[listbox.size() - 1] = ("system", d)

        if mic_devices and system_devices and self.show_system_audio:
            listbox.insert(tk.END, "")
            listbox.insert(tk.END, "── 麦克风 + 系统音频 ──")
            for d in mic_devices:
                label_text = f"  🎧 {d['name']} + 系统音频"
                listbox.insert(tk.END, label_text)
                row_map[listbox.size() - 1] = ("both", d)

        # 选择默认设备
        default_idx = 0
        if mic_devices:
            default_idx = 1  # 跳过标题

        if default_idx < listbox.size():
            listbox.selection_set(default_idx)
            listbox.see(default_idx)

        # 按钮
        btn_frame = tk.Frame(win, bg=SELECTOR_THEME["window"])
        btn_frame.pack(padx=22, pady=(12, 18), fill="x")

        def on_confirm():
            sel = listbox.curselection()
            if sel:
                idx = sel[0]
                selected_text = listbox.get(idx)
                if idx in row_map:
                    selected_type, device = row_map[idx]
                    self.selected_id = device["id"]
                    self.selected_type = selected_type
                    if selected_type == "both":
                        self.selected_name = f"{device['name']} + 系统音频"
                    else:
                        self.selected_name = device["name"]
                elif "──" in selected_text:
                    return
                elif selected_text.strip().startswith("🎤"):
                    parts = selected_text.strip().split("🎤", 1)
                    if len(parts) > 1:
                        device_name = parts[1].strip()
                        for d in mic_devices:
                            if d["name"] in device_name or device_name in d["name"]:
                                self.selected_id = d["id"]
                                self.selected_name = d["name"]
                                self.selected_type = "microphone"
                                break
                elif selected_text.strip().startswith("🔊"):
                    parts = selected_text.strip().split("🔊", 1)
                    if len(parts) > 1:
                        device_name = parts[1].strip()
                        for d in system_devices:
                            if d["name"] in device_name or device_name in d["name"]:
                                self.selected_id = d["id"]
                                self.selected_name = d["name"]
                                self.selected_type = "system"
                                break

            win.destroy()

        def on_cancel():
            win.destroy()

        confirm_btn = tk.Button(
            btn_frame,
            text="确认",
            command=on_confirm,
            font=("Helvetica", 13, "bold"),
            width=10,
            bg=SELECTOR_THEME["accent"],
            fg="#ffffff",
            activebackground=SELECTOR_THEME["accent_hover"],
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
        )
        confirm_btn.pack(side="right", padx=(10, 0))

        cancel_btn = tk.Button(
            btn_frame,
            text="取消",
            command=on_cancel,
            font=("Helvetica", 13),
            width=10,
            bg=SELECTOR_THEME["surface_alt"],
            fg=SELECTOR_THEME["text"],
            activebackground=SELECTOR_THEME["border"],
            activeforeground=SELECTOR_THEME["text"],
            relief="flat",
            borderwidth=0,
            cursor="hand2",
        )
        cancel_btn.pack(side="right")

        if parent:
            win.grab_set()
            win.wait_window()
        else:
            win.mainloop()

        return self.selected_id, self.selected_name, self.selected_type
