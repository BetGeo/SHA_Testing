#!/usr/bin/env python3
"""Builds a small workbook that mimics the real TimeLog layout, for testing
the voice-to-timesheet tool without touching a real company file.

Sheet 'TimeLog': headers on row 14, data from row 15.
  A=Week  D=Period  E=Staff  F=Date  G=Code  H=Project Name (VLOOKUP)
  I=Task Completed  J=Hours Worked
Sheet 'Projects': lookup table used by the VLOOKUP in column H, so the
"auto-populate project name" behaviour can be verified too.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent.parent))
from projects import load_projects  # noqa: E402

OUT_PATH = Path(__file__).parent / "mock_timesheet.xlsx"
STAFF = "Gabriel Betten"


def build(out_path: Path = OUT_PATH):
    wb = openpyxl.Workbook()

    # --- Projects lookup sheet (subset, real one has ~880 rows) ---
    proj_ws = wb.active
    proj_ws.title = "Projects"
    proj_ws.append(["Code", "Name"])
    sample_projects = load_projects()[:50]
    for p in sample_projects:
        proj_ws.append([p.code, p.name])

    # --- TimeLog sheet ---
    ws = wb.create_sheet("TimeLog")
    headers = {
        "A": "Week", "D": "Period", "E": "Staff", "F": "Date",
        "G": "SHA/LFCI Proj#", "H": "Project Name", "I": "Task Completed",
        "J": "Hours Worked",
    }
    header_row = 14
    for col, label in headers.items():
        ws[f"{col}{header_row}"] = label

    start = date(2026, 6, 29)
    row = header_row + 1
    # A couple of days already have a filled entry (simulating history).
    filled_days = {
        start: ("PRJ26031", "Astria Building Design Services", "Slab / concrete review", 4.0),
    }
    for i in range(10):
        d = start + timedelta(days=i)
        ws[f"A{row}"] = d.isocalendar().week
        ws[f"E{row}"] = STAFF
        ws[f"F{row}"] = d
        ws[f"H{row}"] = f'=IFERROR(VLOOKUP(G{row},Projects!A:B,2,FALSE),"")'
        if d in filled_days:
            code, _, task, hours = filled_days[d]
            ws[f"G{row}"] = code
            ws[f"I{row}"] = task
            ws[f"J{row}"] = hours
        else:
            ws[f"J{row}"] = 0  # blank template row, like the real sheet's pre-filled future days
        row += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    print(f"Wrote mock workbook to {out_path}")


if __name__ == "__main__":
    build()
