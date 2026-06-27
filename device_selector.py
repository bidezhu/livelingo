import tkinter as tk
from tkinter import ttk


class DeviceSelector:
    def __init__(self, devices, current_id=None):
        self.devices = devices
        self.current_id = current_id
        self.selected_id = None
        self.selected_name = None

    def show(self, parent=None):
        if parent:
            win = tk.Toplevel(parent)
        else:
            win = tk.Tk()
        win.title("选择麦克风")
        win.geometry("500x350")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        self._win = win

        label = tk.Label(win, text="请选择输入设备（麦克风）：",
                         font=("Helvetica", 14), anchor="w")
        label.pack(padx=20, pady=(20, 10), fill="x")

        listbox = tk.Listbox(win, font=("Helvetica", 12), height=10)
        listbox.pack(padx=20, pady=5, fill="both", expand=True)

        scrollbar = tk.Scrollbar(listbox, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        default_idx = 0
        for i, d in enumerate(self.devices):
            label_text = f"[{d['id']}] {d['name']}  ({d['channels']}ch)"
            listbox.insert(tk.END, label_text)
            if d["id"] == self.current_id:
                default_idx = i

        listbox.selection_set(default_idx)
        listbox.see(default_idx)

        btn_frame = tk.Frame(win)
        btn_frame.pack(padx=20, pady=(10, 20), fill="x")

        def on_confirm():
            sel = listbox.curselection()
            if sel:
                d = self.devices[sel[0]]
                self.selected_id = d["id"]
                self.selected_name = d["name"]
            win.destroy()

        def on_cancel():
            win.destroy()

        confirm_btn = tk.Button(btn_frame, text="确认", command=on_confirm,
                                font=("Helvetica", 13), width=10)
        confirm_btn.pack(side="right", padx=(10, 0))

        cancel_btn = tk.Button(btn_frame, text="取消", command=on_cancel,
                               font=("Helvetica", 13), width=10)
        cancel_btn.pack(side="right")

        if parent:
            win.grab_set()
            win.wait_window()
        else:
            win.mainloop()

        return self.selected_id, self.selected_name
