# Voice Timesheet (trial)

Speak (or type) one timesheet entry at a time — date, project/code, task,
hours — and it gets written straight into the existing Excel `TimeLog`
sheet, at whatever mapped-drive path you point it to. It only ever edits
the Date / Code / Task / Hours cells of the matching row; every formula
column (Project Name, Billed, Week, ...) is left alone.

There are two ways to run it: a terminal CLI (`main.py`) and a desktop
GUI (`gui.py`), which is also the one packaged into a standalone `.exe`.

## GUI (recommended)

```bash
pip install -r requirements.txt
python gui.py
```

First run: paste or **Browse…** to your timesheet file's mapped-drive
path and your staff name in the Settings panel at the top, click **Save**.
That writes `config.yaml` next to the app so you don't have to re-enter
it next time.

Then, per entry: fill in (or click the mic button 🎤 next to) Date,
Project / code, task description, and hours, and press **Write to
Timesheet**. If the project reference is ambiguous you'll get a
pick-list dialog instead of a silent guess. A status line at the bottom
shows success (green) or a reason it couldn't write (red) — including
the "already has an entry for that date" and "file is open elsewhere"
cases described below.

## Building a standalone .exe

The GUI can be packaged with PyInstaller into a single file that runs on
a machine with no Python installed. **This has to be built on the same
OS you'll run it on** — build on Windows for a `.exe`, macOS for a Mac
binary (PyInstaller does not cross-compile).

```bash
pip install -r build_requirements.txt
pyinstaller voice_timesheet.spec
```

The result is `dist/SperlingHansenVoiceTimesheet(.exe)` — a single
double-clickable file with the project code list baked in. It still
reads/writes `config.yaml` next to itself, so Settings persist between
runs without rebuilding.

On Windows, if PyAudio fails to install for the mic (`pip install -r
requirements.txt` errors on it), run:
```bash
pip install pipwin && pipwin install pyaudio
```
then re-run the PyInstaller build.

## Setup (CLI)

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

For the GUI, run `python gui.py`, then point Settings at
`demo/mock_timesheet.xlsx` instead of the real file.

## Branding

Colours/fonts live in `theme.py` — swap in real Sperling Hansen brand
values there. The header currently uses a 🦌 emoji as a placeholder logo;
drop in the real logo image when you have an asset.

## Known limitations (trial scope)

- One entry per run, one entry per date+staff combination — a second
  entry on the same day requires manually inserting a row first.
- If the Excel file is open elsewhere (locked), saving retries a few
  times with backoff, then tells you to close it and re-run.
- Speech recognition uses Google's free web API via `SpeechRecognition`
  (needs internet). Swap in a local Whisper model later if audio needs
  to stay off the network.
