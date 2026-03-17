import tkinter as tk
from tkinter import filedialog, ttk
import subprocess, tempfile, os, sys

SCRIPT_INFOS = [
    ("patent_cleaner.py", "データ整理"),
    ("ipc_main_group.py", "筆頭IPCメイングループ"),
    ("ipc_summary.py", "公報IPC集計"),
    ("application_trend.py", "出願件数推移グラフ"),
    ("citation_map.py", "被引用ポジショニングマップ"),
    ("cited_applications.py", "被引用出願"),
    ("entry_exit_chart.py", "参入撤退チャート"),
    ("applicant_count.py", "筆頭出願人件数"),
    ("applicant_total.py", "総出願人カウント"),
    ("ipczogen.py", "出願増減率"),
    ("ipc_growth.py", "公報IPC増減率"),
]

def extract_and_run(script_name, args):
    try:
        if hasattr(sys, "_MEIPASS"):
            script_path = os.path.join(sys._MEIPASS, "scripts", script_name)
        else:
            script_path = os.path.join("scripts", script_name)
        with open(script_path, "rb") as f:
            data = f.read()
        with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".py") as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        result = subprocess.run(["python", tmp_path, *args], capture_output=True, text=True,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0:
            output_text.insert(tk.END, f"❌ 実行失敗: {dict(SCRIPT_INFOS)[script_name]}\n")
            output_text.insert(tk.END, result.stderr + "\n")
        else:
            output_text.insert(tk.END, f"✅ 完了: {dict(SCRIPT_INFOS)[script_name]}\n")
        output_text.see(tk.END)
        root.update()
    except Exception as e:
        output_text.insert(tk.END, f"❌ 例外発生: {e}\n")
        output_text.see(tk.END)
        root.update()

def run_selected_scripts():
    import shutil, os
    excel = excel_path_var.get()
    base = base_year_var.get()
    start = start_year_var.get()
    end = end_year_var.get()
    if not os.path.isfile(excel):
        output_text.insert(tk.END, '❌ ファイルが見つかりません\n')
        return
    dirname, filename = os.path.split(excel)
    basename, ext = os.path.splitext(filename)
    work_excel = os.path.join(dirname, basename + '_作業用' + ext)
    final_excel = os.path.join(dirname, basename + '_整理済み' + ext)
    shutil.copyfile(excel, work_excel)
    excel = work_excel

    output_text.delete(1.0, tk.END)
    complete_label.config(text="")
    selected = [s for s, v in script_vars.items() if v.get()]
    progress_bar["maximum"] = len(selected)
    progress_bar["value"] = 0
    for fname in selected:
        display_name = dict(SCRIPT_INFOS)[fname]
        output_text.insert(tk.END, f"● 実行中: {display_name}\n")
        output_text.see(tk.END)
        root.update()
        args = [excel]
        if "applicant" in fname or "ipczogen" in fname or "ipc_growth" in fname:
            if "total" in fname or "count" in fname:
                args += [start, end]
            else:
                args += [base]
        extract_and_run(fname, args)
        progress_bar["value"] += 1
        root.update()
    try:
        os.rename(excel, final_excel)
        output_text.insert(tk.END, f'✅ 整理済みファイルを保存しました: {final_excel}\n')
    except Exception as e:
        output_text.insert(tk.END, f'⚠️ ファイルのリネームに失敗しました: {e}\n')
    output_text.insert(tk.END, "🎉 全て完了しました！\n")
    complete_label.config(text="✅ 完了")

root = tk.Tk()
root.title("スクロール対応スクリプト実行GUI")
root.geometry("580x800")
canvas = tk.Canvas(root)
scroll_frame = tk.Frame(canvas)
vsb = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=vsb.set)
vsb.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)
canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

excel_path_var = tk.StringVar()
base_year_var = tk.StringVar()
start_year_var = tk.StringVar()
end_year_var = tk.StringVar()
script_vars = {}

tk.Label(scroll_frame, text="Excelファイルパス:").pack()
tk.Entry(scroll_frame, textvariable=excel_path_var, width=60).pack()
tk.Button(scroll_frame, text="参照", command=lambda: excel_path_var.set(filedialog.askopenfilename())).pack(pady=2)
tk.Label(scroll_frame, text="基準年:").pack()
tk.Entry(scroll_frame, textvariable=base_year_var).pack()
tk.Label(scroll_frame, text="開始年:").pack()
tk.Entry(scroll_frame, textvariable=start_year_var).pack()
tk.Label(scroll_frame, text="終了年:").pack()
tk.Entry(scroll_frame, textvariable=end_year_var).pack()
tk.Label(scroll_frame, text="実行するスクリプト:").pack(pady=5)

btn_frame = tk.Frame(scroll_frame)
tk.Button(btn_frame, text="すべて選択", command=lambda: [v.set(True) for v in script_vars.values()]).pack(side="left", padx=5)
tk.Button(btn_frame, text="すべて解除", command=lambda: [v.set(False) for v in script_vars.values()]).pack(side="left", padx=5)
btn_frame.pack()

for fname, label in SCRIPT_INFOS:
    var = tk.BooleanVar(value=True)
    tk.Checkbutton(scroll_frame, text=label, variable=var).pack(anchor="w")
    script_vars[fname] = var

progress_bar = ttk.Progressbar(scroll_frame, orient="horizontal", length=400, mode="determinate")
progress_bar.pack()
complete_label = tk.Label(scroll_frame, text="", fg="green")
complete_label.pack()
tk.Button(scroll_frame, text="実行開始", command=run_selected_scripts).pack(pady=10)
output_text = tk.Text(scroll_frame, height=20, width=80)
output_text.pack()

root.mainloop()
