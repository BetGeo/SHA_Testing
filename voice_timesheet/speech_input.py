"""Speech capture, with a typed fallback for testing without a microphone."""


class SpeechInput:
    """Wraps SpeechRecognition so the rest of the app doesn't care whether
    input came from a microphone or was typed for a dry run."""

    def __init__(self, use_mic: bool = False, language: str = "en-CA"):
        self.use_mic = use_mic
        self.language = language
        self._recognizer = None
        self._mic = None
        if use_mic:
            import speech_recognition as sr  # imported lazily: optional dependency

            self._recognizer = sr.Recognizer()
            self._mic = sr.Microphone()

    def prompt(self, question: str) -> str:
        if not self.use_mic:
            return input(f"{question} ").strip()

        import speech_recognition as sr

        print(f"{question} (listening...)")
        with self._mic as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = self._recognizer.listen(source)
        try:
            text = self._recognizer.recognize_google(audio, language=self.language)
            print(f"  heard: {text}")
            return text
        except sr.UnknownValueError:
            print("  (didn't catch that, please type it instead)")
            return input(f"{question} ").strip()
        except sr.RequestError as exc:
            print(f"  (speech service error: {exc}; please type it instead)")
            return input(f"{question} ").strip()
