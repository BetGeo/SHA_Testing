"""Fully spoken data-entry flow: the app prompts by voice, listens for each
field, reads the whole entry back, and only writes it after a spoken yes —
with a spoken or on-screen way to fix any one field first.

Runs entirely on a background thread. The callbacks it's given
(`on_field_update`, `on_status`, `ask_user_to_pick`) are the only points of
contact with the GUI, so the GUI is responsible for making them thread-safe.
"""
from parse_utils import (
    parse_choice,
    parse_date,
    parse_field_to_change,
    parse_hours,
    parse_yes_no,
)
from projects import Project, ProjectMatcher
from speech_input import listen_once
from timesheet import TimesheetWriter
from tts import speak

MAX_FIELD_ATTEMPTS = 3


class VoiceEntryFlow:
    def __init__(
        self,
        matcher: ProjectMatcher,
        writer: TimesheetWriter,
        language: str,
        staff_name: str | None,
        on_field_update,
        on_status,
        ask_user_to_pick,
    ):
        self.matcher = matcher
        self.writer = writer
        self.language = language
        self.staff_name = staff_name
        self.on_field_update = on_field_update
        self.on_status = on_status
        self.ask_user_to_pick = ask_user_to_pick

        self.entry_date = None
        self.code = None
        self.project_name = None
        self.task = None
        self.hours = None

    # ---------- low-level IO ----------

    def _say(self, text: str):
        speak(text)

    def _listen(self) -> str | None:
        try:
            return listen_once(language=self.language)
        except RuntimeError as exc:
            self._say(str(exc))
            return None

    # ---------- top-level run ----------

    def run(self):
        self._say("Let's log a timesheet entry.")
        if not self._get_date():
            return self._cancel()
        if not self._get_project():
            return self._cancel()
        if not self._get_task():
            return self._cancel()
        if not self._get_hours():
            return self._cancel()
        self._confirm_loop()

    def _cancel(self, message: str = "Okay, cancelled."):
        self._say(message)
        self.on_status(message, False)

    # ---------- field collection ----------

    def _get_date(self, prompt: str = "What date is this entry for?") -> bool:
        self._say(prompt)
        for attempt in range(MAX_FIELD_ATTEMPTS):
            heard = self._listen()
            if heard is None:
                return False
            parsed = parse_date(heard)
            if parsed:
                self.entry_date = parsed
                self.on_field_update("date", parsed.isoformat())
                return True
            self._say("Sorry, I didn't understand that date. Try something like today, or July 8th.")
        self._say("I couldn't get a date after a few tries.")
        return False

    def _get_project(self, prompt: str = "What project or code did you work on?") -> bool:
        self._say(prompt)
        for attempt in range(MAX_FIELD_ATTEMPTS):
            heard = self._listen()
            if heard is None:
                return False
            exact, candidates = self.matcher.resolve(heard)
            if exact:
                self.code, self.project_name = exact.code, exact.name
                self.on_field_update("project", f"{exact.name} ({exact.code})")
                self._say(f"Got it, {exact.name}.")
                return True
            if not candidates:
                self._say("I couldn't find that project. Try again.")
                continue
            picked = self._disambiguate(candidates)
            if picked:
                self.code, self.project_name = picked.code, picked.name
                self.on_field_update("project", f"{picked.name} ({picked.code})")
                return True
            self._say("Let's try the project again.")
        self._say("I couldn't pin down the project after a few tries.")
        return False

    def _disambiguate(self, candidates: list[Project]) -> Project | None:
        names = ". ".join(f"{i + 1}, {p.name}" for i, p in enumerate(candidates))
        self._say(f"I found a few matches. {names}. Which number, or say none of these?")
        heard = self._listen()
        if heard:
            idx = parse_choice(heard, len(candidates))
            if idx is not None:
                return candidates[idx]
        self._say("I'll show the options on screen, please pick one there.")
        picked = self.ask_user_to_pick(candidates)
        if picked:
            self._say(f"Got it, {picked.name}.")
        else:
            self._say("No pick made.")
        return picked

    def _get_task(self, prompt: str = "What did you do?") -> bool:
        self._say(prompt)
        for attempt in range(MAX_FIELD_ATTEMPTS):
            heard = self._listen()
            if heard:
                self.task = heard
                self.on_field_update("task", heard)
                return True
            self._say("Didn't catch that, try again.")
        self._say("I couldn't get a description after a few tries.")
        return False

    def _get_hours(self, prompt: str = "How many hours?") -> bool:
        self._say(prompt)
        for attempt in range(MAX_FIELD_ATTEMPTS):
            heard = self._listen()
            if heard is None:
                return False
            parsed = parse_hours(heard)
            if parsed is not None:
                self.hours = parsed
                self.on_field_update("hours", str(parsed))
                return True
            self._say("Sorry, I didn't get a number of hours. Try something like two and a half.")
        self._say("I couldn't get the hours after a few tries.")
        return False

    # ---------- read-back / confirm / correct ----------

    def _confirm_loop(self):
        while True:
            month_day = f"{self.entry_date.strftime('%B')} {self.entry_date.day}"
            self._say(
                f"Here's the entry: {month_day}, {self.project_name}, {self.task}, "
                f"{self.hours} hours. Say yes to save, no to cancel, or say what to "
                "change: date, project, task, or hours."
            )
            heard = self._listen()
            if heard is None:
                return self._cancel()

            yn = parse_yes_no(heard)
            if yn is True:
                return self._write()
            if yn is False:
                return self._cancel()

            field = parse_field_to_change(heard)
            ok = True
            if field == "date":
                ok = self._get_date("Okay, what's the date?")
            elif field == "project":
                ok = self._get_project("Okay, what project?")
            elif field == "task":
                ok = self._get_task("Okay, what did you do?")
            elif field == "hours":
                ok = self._get_hours("Okay, how many hours?")
            else:
                self._say("Sorry, I didn't catch that.")
                continue
            if not ok:
                return self._cancel()
            # loop back around and read the (possibly updated) entry back again

    def _write(self):
        try:
            result = self.writer.write_entry(
                entry_date=self.entry_date,
                code=self.code,
                task=self.task,
                hours=self.hours,
                staff_name=self.staff_name,
            )
        except Exception as exc:  # noqa: BLE001 — surface any write failure by voice too
            self._say(f"I couldn't save that. {exc}")
            self.on_status(str(exc), False)
            return
        self._say("Saved." if result.ok else result.message)
        self.on_status(result.message, result.ok)
