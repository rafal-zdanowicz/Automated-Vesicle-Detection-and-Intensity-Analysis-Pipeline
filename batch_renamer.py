import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def split_filename(path: str):
    """Return (directory, base_name_without_ext, extension)."""
    directory = os.path.dirname(path)
    filename = os.path.basename(path)
    base, ext = os.path.splitext(filename)
    return directory, base, ext


def unique_path(directory: str, filename: str) -> str:
    """
    If target filename exists, append ' (1)', ' (2)', ... before extension.
    Returns a path that does not currently exist.
    """
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    if not os.path.exists(candidate):
        return candidate

    i = 1
    while True:
        new_name = f"{base} ({i}){ext}"
        candidate = os.path.join(directory, new_name)
        if not os.path.exists(candidate):
            return candidate
        i += 1


class BatchRenamerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Batch File Renamer")
        self.geometry("780x520")
        self.minsize(720, 480)

        self.selected_files = []

        # Action choice: 1=prefix, 2=suffix, 3=replace
        self.action_var = tk.IntVar(value=1)

        self.prefix_var = tk.StringVar()
        self.suffix_var = tk.StringVar()
        self.find_var = tk.StringVar()
        self.replace_var = tk.StringVar()

        self._build_ui()
        self._update_action_fields()
        self._update_preview()

    def _build_ui(self):
        # Top controls
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Button(top, text="Select files…", command=self.select_files).pack(side="left")
        ttk.Button(top, text="Clear", command=self.clear_files).pack(side="left", padx=(8, 0))

        self.count_label = ttk.Label(top, text="0 files selected")
        self.count_label.pack(side="left", padx=(12, 0))

        # Action selection
        action_frame = ttk.LabelFrame(self, text="Action", padding=10)
        action_frame.pack(fill="x", padx=10, pady=(0, 10))

        r1 = ttk.Radiobutton(
            action_frame, text="1) Add prefix", variable=self.action_var, value=1,
            command=self._on_action_change
        )
        r2 = ttk.Radiobutton(
            action_frame, text="2) Add suffix", variable=self.action_var, value=2,
            command=self._on_action_change
        )
        r3 = ttk.Radiobutton(
            action_frame, text="3) Replace part of filename", variable=self.action_var, value=3,
            command=self._on_action_change
        )
        r1.grid(row=0, column=0, sticky="w")
        r2.grid(row=0, column=1, sticky="w", padx=(20, 0))
        r3.grid(row=0, column=2, sticky="w", padx=(20, 0))

        # Inputs for actions
        inputs = ttk.Frame(self, padding=(10, 0, 10, 10))
        inputs.pack(fill="x")

        # Prefix
        self.prefix_row = ttk.Frame(inputs)
        ttk.Label(self.prefix_row, text="Prefix:").pack(side="left")
        prefix_entry = ttk.Entry(self.prefix_row, textvariable=self.prefix_var, width=50)
        prefix_entry.pack(side="left", padx=(8, 0), fill="x", expand=True)
        self.prefix_var.trace_add("write", lambda *_: self._update_preview())

        # Suffix
        self.suffix_row = ttk.Frame(inputs)
        ttk.Label(self.suffix_row, text="Suffix:").pack(side="left")
        suffix_entry = ttk.Entry(self.suffix_row, textvariable=self.suffix_var, width=50)
        suffix_entry.pack(side="left", padx=(8, 0), fill="x", expand=True)
        self.suffix_var.trace_add("write", lambda *_: self._update_preview())

        # Replace
        self.replace_row = ttk.Frame(inputs)
        ttk.Label(self.replace_row, text="Find:").pack(side="left")
        find_entry = ttk.Entry(self.replace_row, textvariable=self.find_var, width=25)
        find_entry.pack(side="left", padx=(8, 10))
        ttk.Label(self.replace_row, text="Replace with:").pack(side="left")
        rep_entry = ttk.Entry(self.replace_row, textvariable=self.replace_var, width=25)
        rep_entry.pack(side="left", padx=(8, 0), fill="x", expand=True)
        self.find_var.trace_add("write", lambda *_: self._update_preview())
        self.replace_var.trace_add("write", lambda *_: self._update_preview())

        # Preview + log area
        mid = ttk.Frame(self, padding=(10, 0, 10, 10))
        mid.pack(fill="both", expand=True)

        ttk.Label(mid, text="Preview (old → new):").pack(anchor="w")

        self.preview = tk.Text(mid, height=14, wrap="none")
        self.preview.pack(fill="both", expand=True, pady=(6, 0))

        # Bottom buttons
        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")

        ttk.Button(bottom, text="Rename files", command=self.rename_files).pack(side="right")
        ttk.Button(bottom, text="Exit", command=self.destroy).pack(side="right", padx=(0, 8))

        # Small note
        note = ttk.Label(
            self,
            text="Tip: Rename uses the same folder. If a target name already exists, it will auto-add (1), (2), ...",
            padding=(10, 0, 10, 10)
        )
        note.pack(fill="x")

    def _on_action_change(self):
        self._update_action_fields()
        self._update_preview()

    def _update_action_fields(self):
        # Remove all input rows
        for row in (self.prefix_row, self.suffix_row, self.replace_row):
            row.pack_forget()

        action = self.action_var.get()
        if action == 1:
            self.prefix_row.pack(fill="x")
        elif action == 2:
            self.suffix_row.pack(fill="x")
        else:
            self.replace_row.pack(fill="x")

    def select_files(self):
        files = filedialog.askopenfilenames(title="Select files to rename")
        if not files:
            return
        # keep order but deduplicate
        seen = set(self.selected_files)
        for f in files:
            if f not in seen:
                self.selected_files.append(f)
                seen.add(f)

        self.count_label.config(text=f"{len(self.selected_files)} files selected")
        self._update_preview()

    def clear_files(self):
        self.selected_files = []
        self.count_label.config(text="0 files selected")
        self._update_preview()

    def compute_new_name(self, path: str) -> str:
        directory, base, ext = split_filename(path)
        action = self.action_var.get()

        if action == 1:
            prefix = self.prefix_var.get()
            new_base = f"{prefix}{base}"
        elif action == 2:
            suffix = self.suffix_var.get()
            new_base = f"{base}{suffix}"
        else:
            find = self.find_var.get()
            repl = self.replace_var.get()
            # Replace in the base name only (not extension)
            new_base = base.replace(find, repl)

        new_filename = f"{new_base}{ext}"
        return os.path.join(directory, new_filename)

    def _update_preview(self):
        self.preview.delete("1.0", "end")
        if not self.selected_files:
            self.preview.insert("end", "No files selected.\n")
            return

        for path in self.selected_files[:200]:  # avoid huge UI dumps
            old_name = os.path.basename(path)
            new_path = self.compute_new_name(path)
            new_name = os.path.basename(new_path)
            self.preview.insert("end", f"{old_name}  →  {new_name}\n")

        if len(self.selected_files) > 200:
            self.preview.insert("end", f"\n… and {len(self.selected_files) - 200} more\n")

    def rename_files(self):
        if not self.selected_files:
            messagebox.showwarning("Nothing to do", "Please select files first.")
            return

        action = self.action_var.get()
        if action == 1 and self.prefix_var.get() == "":
            if not messagebox.askyesno("Empty prefix", "Prefix is empty. Continue anyway?"):
                return
        if action == 2 and self.suffix_var.get() == "":
            if not messagebox.askyesno("Empty suffix", "Suffix is empty. Continue anyway?"):
                return
        if action == 3 and self.find_var.get() == "":
            if not messagebox.askyesno("Empty find text", "Find text is empty (this would change nothing). Continue?"):
                return

        # Build plan and validate
        plan = []
        for old_path in self.selected_files:
            if not os.path.exists(old_path):
                plan.append((old_path, None, "Missing"))
                continue

            target_path = self.compute_new_name(old_path)
            directory = os.path.dirname(old_path)
            target_filename = os.path.basename(target_path)

            # If same name, skip
            if os.path.abspath(old_path) == os.path.abspath(target_path):
                plan.append((old_path, target_path, "No change"))
                continue

            # Ensure unique target path if collision
            safe_target = unique_path(directory, target_filename)
            plan.append((old_path, safe_target, "OK"))

        # Show confirmation summary
        ok_count = sum(1 for _, _, status in plan if status == "OK")
        msg = f"About to rename {ok_count} file(s).\n\nProceed?"
        if not messagebox.askyesno("Confirm rename", msg):
            return

        # Execute
        renamed = 0
        skipped = 0
        errors = 0
        error_lines = []

        for old_path, new_path, status in plan:
            if status != "OK":
                skipped += 1
                continue
            try:
                os.rename(old_path, new_path)
                renamed += 1
            except Exception as e:
                errors += 1
                error_lines.append(f"{os.path.basename(old_path)} → ERROR: {e}")

        # Refresh selected file paths to new ones (where renamed)
        new_selected = []
        old_to_new = {old: new for old, new, status in plan if status == "OK"}
        for f in self.selected_files:
            new_selected.append(old_to_new.get(f, f))
        self.selected_files = new_selected

        self.count_label.config(text=f"{len(self.selected_files)} files selected")
        self._update_preview()

        result = f"Renamed: {renamed}\nSkipped: {skipped}\nErrors: {errors}"
        if error_lines:
            result += "\n\n" + "\n".join(error_lines[:12])
            if len(error_lines) > 12:
                result += f"\n… and {len(error_lines) - 12} more"

        messagebox.showinfo("Done", result)


if __name__ == "__main__":
    try:
        app = BatchRenamerApp()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)
