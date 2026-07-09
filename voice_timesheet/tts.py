"""Offline text-to-speech via pyttsx3 (SAPI5 on Windows, no internet needed)."""

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        import pyttsx3  # optional dependency, imported lazily

        _engine = pyttsx3.init()
        _engine.setProperty("rate", 175)
    return _engine


def speak(text: str):
    """Speak `text` and block until done. Only ever call this from one
    thread at a time — pyttsx3's engine isn't safe to drive concurrently."""
    engine = _get_engine()
    engine.say(text)
    engine.runAndWait()
