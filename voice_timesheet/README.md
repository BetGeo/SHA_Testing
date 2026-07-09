# Voice Timesheet (trial)

Speak (or type) one timesheet entry at a time — date, project/code, task,
hours — and it gets written straight into the existing Excel `TimeLog`
sheet, at whatever mapped-drive path you point it to. It only ever edits
the Date / Code / Task / Hours cells of the matching row; every formula
column (Project Name, Billed, Week, ...) is left alone.

## Setup

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

Edit `config.yaml`:
- `excel_path` — the mapped-drive path to your real timesheet file.
- `staff_name` — used to disambiguate rows if the sheet ever has multiple
  people on it.
- Column letters, if your layout differs from the default (F=Date,
  G=Code, H=Project Name formula, I=Task, J=Hours).

On Windows, microphone input needs PyAudio, which sometimes needs a
prebuilt wheel:
```bash
pip install pipwin && pipwin install pyaudio
```

## Running it

```bash
python main.py --config config.yaml            # microphone
python main.py --config config.yaml --text-mode  # type answers, no mic needed
python main.py --config config.yaml --dry-run    # parse + match, but don't save
```

Each run walks through: date → project/code → task description → hours →
confirm. Speak the project name loosely (e.g. "astria" or "squamish
landfill") — if it's ambiguous you'll get a numbered pick-list instead of
a silent guess.

If Excel already has an entry for that date on every available row, the
tool refuses to write and tells you to use the sheet's own "Insert New
Row" first — it won't try to insert rows or touch formulas itself in
this trial.

## How matching works

- `data/project_codes.tsv` holds the full name→code list.
- If you say/type an explicit code (`PRJ26031`, `ADM`, `VAC`, ...) it's
  used directly.
- Otherwise your words are fuzzy-matched against project names and the
  top 3 candidates are shown for you to pick from.

## Demo / dry run without the real file

`demo/build_mock_workbook.py` builds a small workbook with the same
layout (including the VLOOKUP formula that auto-populates Project Name)
so you can try the tool end-to-end before pointing it at company data:

```bash
python demo/build_mock_workbook.py
python main.py --config demo/config.demo.yaml --text-mode
```

## Known limitations (trial scope)

- One entry per run, one entry per date+staff combination — a second
  entry on the same day requires manually inserting a row first.
- If the Excel file is open elsewhere (locked), saving retries a few
  times with backoff, then tells you to close it and re-run.
- Speech recognition uses Google's free web API via `SpeechRecognition`
  (needs internet). Swap in a local Whisper model later if audio needs
  to stay off the network.
