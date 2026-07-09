#!/usr/bin/env python3
"""Voice-to-timesheet trial.

Walks through one timesheet entry per run: date, project/code, task
description, hours worked — captured by voice (or typed, for testing) —
then writes it into the existing Excel TimeLog sheet.

Usage:
    python main.py --config config.yaml            # microphone
    python main.py --config config.yaml --text-mode  # type answers instead
"""
import argparse
import sys
from datetime import date

import yaml

from parse_utils import parse_date, parse_hours
from projects import ProjectMatcher, load_projects
from speech_input import SpeechInput
from timesheet import TimesheetWriter


def resolve_project(matcher: ProjectMatcher, speech: SpeechInput) -> tuple[str, str]:
    """Ask for a project until we get an unambiguous code. Returns (code, display_name)."""
    while True:
        heard = speech.prompt("What project or code is this for?")
        exact, candidates = matcher.resolve(heard)
        if exact:
            return exact.code, f"{exact.name} ({exact.code})"

        if not candidates:
            print("  No matches found — try again.")
            continue

        print("  Did you mean:")
        for i, p in enumerate(candidates, 1):
            print(f"    {i}. {p.name} ({p.code})")
        print(f"    {len(candidates) + 1}. none of these, try again")

        choice = speech.prompt("Pick a number:")
        try:
            idx = int(choice.strip().split()[0]) - 1
        except (ValueError, IndexError):
            print("  Didn't get a number, try again.")
            continue
        if 0 <= idx < len(candidates):
            p = candidates[idx]
            return p.code, f"{p.name} ({p.code})"
        # otherwise loop and ask for the project again


def resolve_date(speech: SpeechInput) -> date:
    while True:
        heard = speech.prompt("What date is this entry for? (say 'today' or a date)")
        parsed = parse_date(heard)
        if parsed:
            return parsed
        print("  Couldn't parse that date, try again (e.g. 'today', 'July 8').")


def resolve_hours(speech: SpeechInput) -> float:
    while True:
        heard = speech.prompt("How many hours?")
        parsed = parse_hours(heard)
        if parsed is not None:
            return parsed
        print("  Couldn't parse a number of hours, try again (e.g. '2.5' or 'two and a half').")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--text-mode", action="store_true", help="Type answers instead of using the microphone")
    parser.add_argument("--dry-run", action="store_true", help="Parse and match everything but don't write the file")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    projects = load_projects()
    matcher = ProjectMatcher(projects)
    speech = SpeechInput(use_mic=not args.text_mode, language=cfg.get("language", "en-CA"))
    writer = TimesheetWriter(
        path=cfg["excel_path"],
        sheet_name=cfg.get("sheet_name", "TimeLog"),
        header_row=cfg.get("header_row", 14),
        date_col=cfg.get("date_col", "F"),
        code_col=cfg.get("code_col", "G"),
        task_col=cfg.get("task_col", "I"),
        hours_col=cfg.get("hours_col", "J"),
        staff_col=cfg.get("staff_col", "E"),
    )

    entry_date = resolve_date(speech)
    code, display_name = resolve_project(matcher, speech)
    task = speech.prompt("What did you do? (task description)")
    hours = resolve_hours(speech)

    print("\n--- Entry summary ---")
    print(f"  Date:    {entry_date}")
    print(f"  Project: {display_name}")
    print(f"  Task:    {task}")
    print(f"  Hours:   {hours}")
    confirm = speech.prompt("Write this to the timesheet? (yes/no)")
    if confirm.strip().lower() not in ("yes", "y"):
        print("Discarded, nothing written.")
        return

    result = writer.write_entry(
        entry_date=entry_date,
        code=code,
        task=task,
        hours=hours,
        staff_name=cfg.get("staff_name"),
        dry_run=args.dry_run,
    )
    print(result.message)
    if not result.ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
