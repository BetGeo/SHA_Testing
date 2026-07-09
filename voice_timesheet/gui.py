#!/usr/bin/env python3
"""Sperling Hansen Voice Timesheet — minimal desktop GUI.

Settings pane to point at the real Excel file, then one entry form
(date / project / task / hours) with a mic button per field. Reuses the
same matching + writing logic as the CLI trial (main.py).
"""
import threading
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox

import yaml

import theme
from parse_utils import parse_date, parse_hours
from paths import app_dir
from projects import Project, ProjectMatcher, load_projects
from speech_input import listen_once
from timesheet import TimesheetWriter

CONFIG_PATH = app_dir() / "config.yaml"

DEFAULT_CONFIG = {
    "excel_path": "",
    "sheet_name": "TimeLog",
    "staff_name": "",
    "language": "en-CA",
    "header_row": 14,
    "date_col": "F",
    "code_col": "G",
    "task_col": "I",
    "hours_col": "J",
    "staff_col": "E",
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            saved = yaml.safe_load(f) or {}
        cfg.update(saved)
    return cfg


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)


class MicButton(tk.Button):
    """A small round-ish mic button that runs speech capture on a background
    thread (so the window doesn't freeze) and hands the transcript back to
    the caller on the main thread."""

    def __init__(self, master, language: str, on_result, **kwargs):
        super().__init__(
            master,
            text="\U0001F3A4",
            font=(theme.FONT_FAMILY, 12),
            bg=theme.LEAF,
            fg="white",
            activebackground=theme.FOREST_DARK,
            activeforeground="white",
            relief="flat",
            width=3,
            cursor="hand2",
            command=self._start,
            **kwargs,
        )
        self.language = language
        self.on_result = on_result

    def _start(self):
        self.config(state="disabled", bg=theme.FOREST_DARK)

        def worker():
            try:
                text = listen_once(language=self.language)
                error = None
            except RuntimeError as exc:
                text = None
                error = str(exc)
            self.after(0, lambda: self._finish(text, error))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, text, error):
        self.config(state="normal", bg=theme.LEAF)
        self.on_result(text, error)


class ProjectPickerDialog(tk.Toplevel):
    """Shown when a spoken/typed project reference is ambiguous."""

    def __init__(self, master, candidates: list[Project], on_pick):
        super().__init__(master)
        self.title("Which project?")
        self.configure(bg=theme.CARD)
        self.geometry("420x260")
        self.on_pick = on_pick
        self.transient(master)
        self.grab_set()

        tk.Label(
            self, text="Did you mean:", bg=theme.CARD, fg=theme.TEXT,
            font=theme.FONT_LABEL,
        ).pack(anchor="w", padx=16, pady=(16, 4))

        listbox = tk.Listbox(
            self, font=theme.FONT_ENTRY, height=8, activestyle="none",
            selectbackground=theme.LEAF, selectforeground="white",
        )
        for p in candidates:
            listbox.insert(tk.END, f"{p.name}  ({p.code})")
        listbox.pack(fill="both", expand=True, padx=16, pady=4)
        listbox.bind("<Double-Button-1>", lambda e: self._pick(listbox, candidates))

        button_row = tk.Frame(self, bg=theme.CARD)
        button_row.pack(fill="x", padx=16, pady=12)
        tk.Button(
            button_row, text="Use selected", font=theme.FONT_BUTTON,
            bg=theme.LEAF, fg="white", relief="flat",
            command=lambda: self._pick(listbox, candidates),
        ).pack(side="left")
        tk.Button(
            button_row, text="None of these", font=theme.FONT_LABEL,
            bg=theme.CARD, fg=theme.TEXT_MUTED, relief="flat",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _pick(self, listbox, candidates):
        sel = listbox.curselection()
        if not sel:
            return
        self.on_pick(candidates[sel[0]])
        self.destroy()


class VoiceTimesheetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sperling Hansen — Voice Timesheet")
        self.configure(bg=theme.BACKGROUND)
        self.geometry("560x680")
        self.minsize(520, 620)

        self.cfg = load_config()
        self.matcher = ProjectMatcher(load_projects())
        self.resolved_code: str | None = None
        self.resolved_name: str | None = None

        self._build_header()
        self._build_settings()
        self._build_entry_form()
        self._build_status_bar()

    # ---------- layout ----------

    def _build_header(self):
        header = tk.Frame(self, bg=theme.FOREST, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text="\U0001F98C  SPERLING HANSEN",
            font=theme.FONT_HEADER, bg=theme.FOREST, fg="white",
        ).pack(side="left", padx=18, pady=12)
        tk.Label(
            header, text="Voice Timesheet",
            font=(theme.FONT_FAMILY, 11), bg=theme.FOREST, fg=theme.LEAF_LIGHT,
        ).pack(side="left", pady=12)

    def _build_settings(self):
        card = tk.Frame(self, bg=theme.CARD, highlightbackground=theme.BORDER, highlightthickness=1)
        card.pack(fill="x", padx=16, pady=(16, 8))

        tk.Label(card, text="Settings", font=theme.FONT_LABEL, bg=theme.CARD, fg=theme.TEXT_MUTED).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(10, 2)
        )

        tk.Label(card, text="Timesheet file:", font=theme.FONT_LABEL, bg=theme.CARD, fg=theme.TEXT).grid(
            row=1, column=0, sticky="w", padx=12
        )
        self.excel_path_var = tk.StringVar(value=self.cfg.get("excel_path", ""))
        tk.Entry(card, textvariable=self.excel_path_var, font=theme.FONT_ENTRY, width=36).grid(
            row=1, column=1, sticky="ew", padx=6, pady=6
        )
        tk.Button(
            card, text="Browse…", font=theme.FONT_LABEL, bg=theme.LEAF_LIGHT, fg=theme.FOREST,
            relief="flat", command=self._browse_excel,
        ).grid(row=1, column=2, padx=(0, 12))

        tk.Label(card, text="Staff name:", font=theme.FONT_LABEL, bg=theme.CARD, fg=theme.TEXT).grid(
            row=2, column=0, sticky="w", padx=12
        )
        self.staff_name_var = tk.StringVar(value=self.cfg.get("staff_name", ""))
        tk.Entry(card, textvariable=self.staff_name_var, font=theme.FONT_ENTRY, width=36).grid(
            row=2, column=1, sticky="ew", padx=6, pady=(0, 10)
        )
        tk.Button(
            card, text="Save", font=theme.FONT_LABEL, bg=theme.LEAF_LIGHT, fg=theme.FOREST,
            relief="flat", command=self._save_settings,
        ).grid(row=2, column=2, padx=(0, 12), pady=(0, 10))

        card.grid_columnconfigure(1, weight=1)

    def _build_entry_form(self):
        card = tk.Frame(self, bg=theme.CARD, highlightbackground=theme.BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True, padx=16, pady=8)

        # Date
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self._field_row(card, 0, "Date", self.date_var, mic=True)

        # Project
        self.project_var = tk.StringVar()
        self._field_row(card, 1, "Project / code", self.project_var, mic=True,
                         on_change=self._on_project_text_changed)
        self.project_match_label = tk.Label(
            card, text="", font=(theme.FONT_FAMILY, 9, "italic"), bg=theme.CARD, fg=theme.TEXT_MUTED,
        )
        self.project_match_label.grid(row=2, column=1, sticky="w", padx=12)

        # Task
        tk.Label(card, text="What did you do", font=theme.FONT_LABEL, bg=theme.CARD, fg=theme.TEXT).grid(
            row=3, column=0, sticky="nw", padx=12, pady=(16, 0)
        )
        self.task_text = tk.Text(card, font=theme.FONT_ENTRY, height=4, wrap="word",
                                  highlightbackground=theme.BORDER, highlightthickness=1)
        self.task_text.grid(row=3, column=1, sticky="ew", padx=6, pady=(16, 0))
        MicButton(card, self.cfg.get("language", "en-CA"), self._on_task_mic).grid(
            row=3, column=2, sticky="n", padx=(0, 12), pady=(16, 0)
        )

        # Hours
        self.hours_var = tk.StringVar()
        self._field_row(card, 4, "Hours worked", self.hours_var, mic=True, pady=(16, 0))

        card.grid_columnconfigure(1, weight=1)

        tk.Button(
            card, text="Write to Timesheet", font=theme.FONT_BUTTON, bg=theme.LEAF, fg="white",
            relief="flat", height=2, command=self._write_entry,
        ).grid(row=5, column=0, columnspan=3, sticky="ew", padx=12, pady=20)

    def _field_row(self, card, row, label, var, mic=False, on_change=None, pady=(8, 0)):
        tk.Label(card, text=label, font=theme.FONT_LABEL, bg=theme.CARD, fg=theme.TEXT).grid(
            row=row, column=0, sticky="w", padx=12, pady=pady
        )
        entry = tk.Entry(card, textvariable=var, font=theme.FONT_ENTRY,
                          highlightbackground=theme.BORDER, highlightthickness=1)
        entry.grid(row=row, column=1, sticky="ew", padx=6, pady=pady)
        if on_change:
            var.trace_add("write", lambda *_: on_change())
        if mic:
            MicButton(
                card, self.cfg.get("language", "en-CA"),
                lambda text, error, v=var: self._fill_var(v, text, error),
            ).grid(row=row, column=2, padx=(0, 12), pady=pady)
        return entry

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Ready.")
        self.status_label = tk.Label(
            self, textvariable=self.status_var, font=theme.FONT_LABEL,
            bg=theme.BACKGROUND, fg=theme.TEXT_MUTED, anchor="w",
        )
        self.status_label.pack(fill="x", padx=18, pady=(0, 12))

    # ---------- behaviour ----------

    def _browse_excel(self):
        path = filedialog.askopenfilename(
            title="Select the timesheet Excel file",
            filetypes=[("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")],
        )
        if path:
            self.excel_path_var.set(path)

    def _save_settings(self):
        self.cfg["excel_path"] = self.excel_path_var.get().strip()
        self.cfg["staff_name"] = self.staff_name_var.get().strip()
        save_config(self.cfg)
        self._set_status("Settings saved.", ok=True)

    def _fill_var(self, var: tk.StringVar, text, error):
        if error:
            self._set_status(error, ok=False)
            return
        var.set(text)

    def _on_task_mic(self, text, error):
        if error:
            self._set_status(error, ok=False)
            return
        self.task_text.delete("1.0", tk.END)
        self.task_text.insert("1.0", text)

    def _on_project_text_changed(self):
        self.resolved_code = None
        self.resolved_name = None
        self.project_match_label.config(text="")

    def _resolve_project(self, text: str) -> bool:
        """Resolve project text to a code, prompting via dialog if ambiguous.
        Returns True once resolved (dialog resolution happens async, so a
        write triggered from mic input may need the user to press the
        button again after picking)."""
        exact, candidates = self.matcher.resolve(text)
        if exact:
            self.resolved_code = exact.code
            self.resolved_name = exact.name
            self.project_match_label.config(text=f"✓ {exact.name} ({exact.code})")
            return True
        if not candidates:
            self._set_status("No matching project found — try different words.", ok=False)
            return False

        def on_pick(p: Project):
            self.resolved_code = p.code
            self.resolved_name = p.name
            self.project_match_label.config(text=f"✓ {p.name} ({p.code})")

        ProjectPickerDialog(self, candidates, on_pick)
        return False

    def _write_entry(self):
        if not self.cfg.get("excel_path"):
            self._set_status("Set the timesheet file path in Settings first.", ok=False)
            return

        entry_date = parse_date(self.date_var.get())
        if not entry_date:
            self._set_status("Couldn't understand the date.", ok=False)
            return

        if not self.resolved_code:
            project_text = self.project_var.get().strip()
            if not project_text:
                self._set_status("Enter or say a project.", ok=False)
                return
            if not self._resolve_project(project_text):
                return  # dialog is open, or no match — user needs to retry

        task = self.task_text.get("1.0", tk.END).strip()
        if not task:
            self._set_status("Enter a task description.", ok=False)
            return

        hours = parse_hours(self.hours_var.get())
        if hours is None:
            self._set_status("Couldn't understand the hours.", ok=False)
            return

        writer = TimesheetWriter(
            path=self.cfg["excel_path"],
            sheet_name=self.cfg.get("sheet_name", "TimeLog"),
            header_row=self.cfg.get("header_row", 14),
            date_col=self.cfg.get("date_col", "F"),
            code_col=self.cfg.get("code_col", "G"),
            task_col=self.cfg.get("task_col", "I"),
            hours_col=self.cfg.get("hours_col", "J"),
            staff_col=self.cfg.get("staff_col", "E"),
        )
        try:
            result = writer.write_entry(
                entry_date=entry_date,
                code=self.resolved_code,
                task=task,
                hours=hours,
                staff_name=self.cfg.get("staff_name") or None,
            )
        except Exception as exc:  # noqa: BLE001 — surface any write failure to the user
            self._set_status(str(exc), ok=False)
            return

        self._set_status(result.message, ok=result.ok)
        if result.ok:
            self._clear_entry_form()

    def _clear_entry_form(self):
        self.project_var.set("")
        self.task_text.delete("1.0", tk.END)
        self.hours_var.set("")
        self.resolved_code = None
        self.resolved_name = None
        self.project_match_label.config(text="")

    def _set_status(self, message: str, ok: bool):
        self.status_var.set(message)
        self.status_label.config(fg=theme.FOREST if ok else theme.ERROR)


def main():
    app = VoiceTimesheetApp()
    app.mainloop()


if __name__ == "__main__":
    main()
