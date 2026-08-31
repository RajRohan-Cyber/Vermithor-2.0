import os
import re
import threading
import time
from difflib import SequenceMatcher
from pathlib import Path

from dotenv import load_dotenv

from vermithor.actions.apps import AppActions
from vermithor.actions.automation import AutomationActions
from vermithor.actions.browser import BrowserActions
from vermithor.actions.files import FileActions
from vermithor.actions.system import SystemActions
from vermithor.brain.ai import VermithorAI
from vermithor.audio.speech import SpeechRecognizer
from vermithor.audio.tts import TextToSpeech
from vermithor.core.memory import Memory
from vermithor.core.router import CommandRouter
from vermithor.core.system import SystemManager


load_dotenv()


class Vermithor:

    def __init__(self, event_callback=None):

        self.name = os.getenv(
            "VERMITHOR_NAME",
            "Vermithor"
        )

        self.running = True
        self.voice_mode = True
        self.awake = False
        self.sleeping = False

        self.event_callback = event_callback

        self._voice_thread = None
        self._lock = threading.RLock()
        self._wake_event = threading.Event()

        # =========================================================
        # AUDIO COOLDOWN
        # =========================================================

        self._listen_block_until = 0.0

        # =========================================================
        # MEMORY / AI
        # =========================================================

        self.memory = Memory()

        self.ai = VermithorAI(
            memory=self.memory
        )

        # =========================================================
        # VOICE
        # =========================================================

        self.voice = SpeechRecognizer(

            model_name=os.getenv(
                "WHISPER_MODEL",
                "base.en"
            ),

            device=os.getenv(
                "WHISPER_DEVICE",
                "cpu"
            ),

            compute_type=os.getenv(
                "WHISPER_COMPUTE",
                "int8"
            ),

            sample_rate=16000,
            channels=1,

            # LONG COMMAND SUPPORT
            command_max_seconds=float(
                os.getenv(
                    "VOICE_COMMAND_MAX_SECONDS",
                    "30"
                )
            ),

            command_start_timeout=float(
                os.getenv(
                    "VOICE_COMMAND_START_TIMEOUT",
                    "8"
                )
            ),

            command_silence_seconds=float(
                os.getenv(
                    "VOICE_COMMAND_SILENCE_SECONDS",
                    "1.0"
                )
            ),

            calibration_seconds=float(
                os.getenv(
                    "VOICE_CALIBRATION_SECONDS",
                    "0.8"
                )
            ),

            # LONG WAKE + COMMAND SUPPORT
            wake_max_seconds=float(
                os.getenv(
                    "VOICE_WAKE_MAX_SECONDS",
                    "20"
                )
            ),

            wake_start_timeout=float(
                os.getenv(
                    "VOICE_WAKE_START_TIMEOUT",
                    "5"
                )
            ),

            wake_silence_seconds=float(
                os.getenv(
                    "VOICE_WAKE_SILENCE_SECONDS",
                    "1.0"
                )
            )
        )

        self.tts = TextToSpeech()

        # =========================================================
        # ACTION SYSTEM
        # =========================================================

        self.apps = AppActions()
        self.browser = BrowserActions()
        self.files = FileActions()
        self.system = SystemActions()
        self.automation = AutomationActions()
        self.system_manager = SystemManager()

        self.router = CommandRouter(
            self.apps,
            self.browser,
            self.files,
            self.system,
            self.automation,
            self.system_manager,
            self.memory
        )

        # =========================================================
        # WAKE WORDS
        # =========================================================

        self.wake_words = {
            "vermithor",
            "vermitor",
            "varmithor",
            "vermithore",
            "vermithar",
            "vermithur",
            "vermathor",
            "vermetor",
            "vermiter",
            "varmithole",
            "vermithole",
            "mithor"
        }

        self.hello_words = {
            "hello",
            "hey",
            "hi"
        }

        # =========================================================
        # SLEEP
        # =========================================================

        self.sleep_phrases = {
            "stop listening",
            "stop listening vermithor",
            "go to sleep",
            "sleep vermithor",
            "sleep",
            "goodbye",
            "goodbye vermithor",
            "exit voice mode",
            "leave voice mode",
            "cancel voice mode",
            "stop voice mode"
        }

        # =========================================================
        # EXIT
        # =========================================================

        self.exit_phrases = {
            "exit",
            "quit",
            "shutdown vermithor",
            "shut down vermithor",
            "terminate vermithor",
            "exit vermithor"
        }

        self._emit(
            "status",
            "Starting"
        )

        self.configure_startup()

    # =============================================================
    # UI EVENTS
    # =============================================================

    def _emit(self, kind, value=""):

        callback = self.event_callback

        if callback is None:
            return

        try:
            callback(
                kind,
                value
            )

        except Exception:
            pass

    def set_event_callback(self, callback):

        self.event_callback = callback

    # =============================================================
    # WINDOWS STARTUP
    # =============================================================

    def configure_startup(self):

        if os.getenv(
            "AUTO_START",
            "true"
        ).lower() != "true":

            return

        try:

            project_dir = (
                Path(__file__)
                .resolve()
                .parents[2]
            )

            launcher = (
                project_dir
                / "start_vermithor.pyw"
            )

            startup = (
                Path(
                    os.getenv(
                        "APPDATA",
                        str(Path.home())
                    )
                )
                / "Microsoft"
                / "Windows"
                / "Start Menu"
                / "Programs"
                / "Startup"
            )

            startup.mkdir(
                parents=True,
                exist_ok=True
            )

            startup_launcher = (
                startup
                / "Vermithor.pyw"
            )

            code = (
                launcher.read_text(
                    encoding="utf-8"
                )
                if launcher.exists()
                else (
                    "import os, sys\n"
                    f"os.chdir(r'{project_dir}')\n"
                    f"sys.path.insert(0, r'{project_dir}')\n"
                    "from app import main\n"
                    "main()\n"
                )
            )

            if (
                not startup_launcher.exists()
                or
                startup_launcher.read_text(
                    encoding="utf-8"
                ) != code
            ):

                startup_launcher.write_text(
                    code,
                    encoding="utf-8"
                )

            self._emit(
                "status",
                "Startup ready"
            )

        except Exception as exc:

            self._emit(
                "log",
                f"Startup setup warning: {exc}"
            )

    # =============================================================
    # NORMALIZATION
    # =============================================================

    @staticmethod
    def normalize(text):

        text = str(
            text or ""
        ).lower()

        text = re.sub(
            r"[^\w\s]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # =============================================================
    # WAKE WORD
    # =============================================================

    def _is_wake_word(self, word):

        word = self.normalize(
            word
        )

        if not word:
            return False

        if word in self.wake_words:
            return True

        # Only fuzzy-match against words that are already close
        # in length to "vermithor" (9 letters), and require a
        # tighter similarity score. Without this, short or
        # unrelated words heard by Whisper could randomly score
        # above the old 0.84 threshold and wake the assistant
        # even though nobody said "Vermithor".
        if len(word) < 7:
            return False

        for wake in self.wake_words:

            if len(wake) < 7:
                continue

            score = SequenceMatcher(
                None,
                word,
                wake
            ).ratio()

            if score >= 0.90:
                return True

        return False

    def extract_wake_command(self, text):

        normalized = self.normalize(
            text
        )

        if not normalized:
            return False, ""

        words = normalized.split()

        if not words:
            return False, ""

        # ---------------------------------------------------------
        # hello/hey/hi + Vermithor
        # ---------------------------------------------------------

        for index in range(
            len(words) - 1
        ):

            if (
                words[index] in self.hello_words
                and
                self._is_wake_word(
                    words[index + 1]
                )
            ):

                command = " ".join(
                    words[
                        index + 2:
                    ]
                ).strip()

                return True, command

        # ---------------------------------------------------------
        # Vermithor anywhere in sentence
        # ---------------------------------------------------------

        for index, word in enumerate(words):

            if self._is_wake_word(word):

                command = " ".join(
                    words[
                        index + 1:
                    ]
                ).strip()

                return True, command

        return False, ""

    # =============================================================
    # SLEEP / EXIT
    # =============================================================

    def is_sleep(self, text):

        value = self.normalize(
            text
        )

        return value in self.sleep_phrases

    def is_exit(self, text):

        value = self.normalize(
            text
        )

        return value in self.exit_phrases

    # =============================================================
    # RESULT NORMALIZATION
    # =============================================================

    @staticmethod
    def result_to_text(result):

        if result is None:
            return ""

        if isinstance(
            result,
            tuple
        ):

            if len(result) >= 2:

                handled = result[0]
                value = result[1]

                if handled:

                    return Vermithor.result_to_text(
                        value
                    )

                return ""

        if isinstance(
            result,
            dict
        ):

            value = (
                result.get("response")
                or result.get("message")
                or result.get("text")
                or result.get("result")
                or ""
            )

            return str(
                value
            ).strip()

        return str(
            result
        ).strip()

    # =============================================================
    # SPEAK
    # =============================================================

    def speak(self, text):

        text = self.result_to_text(
            text
        )

        if not text:
            return

        self._emit(
            "response",
            text
        )

        self._emit(
            "status",
            "Speaking"
        )

        try:

            self.tts.speak(
                text
            )

        except Exception as exc:

            self._emit(
                "log",
                f"TTS error: {type(exc).__name__}: {exc}"
            )

        finally:

            # Let speaker/browser audio settle before reopening the mic.
            # This prevents Vermithor's own response or newly-started
            # YouTube audio from becoming the next wake transcript.
            self._listen_block_until = (
                time.monotonic()
                + 2.0
            )

    # =============================================================
    # COMMAND EXECUTION
    # =============================================================

    def execute(self, command):

        command = str(
            command or ""
        ).strip()

        if not command:
            return ""

        wake, stripped = (
            self.extract_wake_command(
                command
            )
        )

        if wake:

            if stripped:

                command = stripped

            else:

                self.speak(
                    "Yes, Rohan?"
                )

                return ""

        self._emit(
            "command",
            command
        )

        # ---------------------------------------------------------
        # EXIT
        # ---------------------------------------------------------

        if self.is_exit(command):

            self.shutdown(
                speak=True
            )

            return ""

        # ---------------------------------------------------------
        # SLEEP
        # ---------------------------------------------------------

        if self.is_sleep(command):

            self.sleeping = True
            self.awake = False

            self._emit(
                "status",
                "Sleeping"
            )

            self.speak(
                "Going to sleep. Say Vermithor when you need me."
            )

            return ""

        # ---------------------------------------------------------
        # ROUTER
        # ---------------------------------------------------------

        try:

            result = self.router.route(
                command
            )

        except Exception as exc:

            self._emit(
                "log",
                f"Router error: {type(exc).__name__}: {exc}"
            )

            result = None

        response = ""

        if isinstance(
            result,
            tuple
        ):

            if (
                len(result) >= 2
                and result[0]
            ):

                response = self.result_to_text(
                    result[1]
                )

        elif result is not None:

            response = self.result_to_text(
                result
            )

        # ---------------------------------------------------------
        # AI FALLBACK
        # ---------------------------------------------------------

        if not response:

            try:

                response = self.result_to_text(
                    self.ai.ask(
                        command
                    )
                )

            except Exception as exc:

                self._emit(
                    "log",
                    f"AI error: {type(exc).__name__}: {exc}"
                )

                response = (
                    "I couldn't process that command."
                )

        # ---------------------------------------------------------
        # MEMORY
        # ---------------------------------------------------------

        if response:

            try:

                if hasattr(
                    self.memory,
                    "add_conversation"
                ):

                    self.memory.add_conversation(
                        command,
                        response
                    )

            except Exception:
                pass

            self.speak(
                response
            )

        self.awake = False

        if (
            self.running
            and
            not self.sleeping
        ):

            self._emit(
                "status",
                "Standby — say Vermithor"
            )

        return response

    # =============================================================
    # WAKE LISTENER
    # =============================================================

    def _listen_for_wake(self):

        remaining = (
            self._listen_block_until
            - time.monotonic()
        )

        if remaining > 0:

            time.sleep(
                remaining
            )

        try:

            return str(
                self.voice.listen_wake()
                or ""
            ).strip()

        except KeyboardInterrupt:

            raise

        except Exception as exc:

            self._emit(
                "log",
                f"Wake listener error: {type(exc).__name__}: {exc}"
            )

            time.sleep(
                0.15
            )

            return ""

    # =============================================================
    # COMMAND LISTENER
    # =============================================================

    def _listen_for_command(self):

        self._emit(
            "status",
            "Listening for command"
        )

        try:

            return str(
                self.voice.listen_command()
                or ""
            ).strip()

        except KeyboardInterrupt:

            raise

        except Exception as exc:

            self._emit(
                "log",
                f"Command listener error: {type(exc).__name__}: {exc}"
            )

            return ""

    # =============================================================
    # VOICE COMMAND WORKER
    # =============================================================

    def _execute_voice_command(
        self,
        command
    ):

        try:

            self.execute(
                command
            )

        except Exception as exc:

            self._emit(
                "log",
                f"Command execution error: "
                f"{type(exc).__name__}: {exc}"
            )

    # =============================================================
    # VOICE ENGINE
    # =============================================================

    def run_voice(self):

        self.voice_mode = True

        self._emit(
            "status",
            "Loading voice engine"
        )

        try:

            if not self.voice.initialize():

                self._emit(
                    "status",
                    "Voice engine failed"
                )

                return

        except Exception as exc:

            self._emit(
                "log",
                f"Voice initialization error: "
                f"{type(exc).__name__}: {exc}"
            )

            self._emit(
                "status",
                "Voice unavailable"
            )

            return

        self._emit(
            "status",
            "Standby — say Vermithor"
        )

        self.speak(
            "Vermithor is online."
        )

        # =========================================================
        # ALWAYS-ON LOOP
        # =========================================================

        while self.running:

            try:

                # -------------------------------------------------
                # SLEEP
                # -------------------------------------------------

                if self.sleeping:

                    # Sleeping disables command execution, not wake detection.
                    # Keep the microphone wake listener alive so
                    # "Hello Vermithor" can wake the assistant again.
                    self._emit(
                        "status",
                        "Sleeping — say Vermithor"
                    )

                    text = self._listen_for_wake()

                    if not text:
                        continue

                    wake, command = self.extract_wake_command(text)

                    if not wake:
                        continue

                    self.sleeping = False
                    self.awake = True

                    self._emit("heard", text)

                    if command:
                        self._execute_voice_command(command)
                    else:
                        self.speak("Yes, Rohan?")
                        command = self._listen_for_command()
                        if command:
                            self._execute_voice_command(command)

                    self.awake = False
                    if self.running:
                        self._emit("status", "Standby — say Vermithor")
                    continue

                # -------------------------------------------------
                # WAKE
                # -------------------------------------------------

                text = self._listen_for_wake()

                if not text:
                    continue

                wake, command = (
                    self.extract_wake_command(
                        text
                    )
                )

                if not wake:
                    continue

                self._emit(
                    "heard",
                    text
                )

                self.awake = True

                # -------------------------------------------------
                # WAKE + COMPLETE COMMAND
                # -------------------------------------------------

                if command:

                    self._emit(
                        "status",
                        "Processing command"
                    )

                    # IMPORTANT:
                    # Execute synchronously.  The old background thread
                    # allowed the wake listener to start again while a
                    # command was still speaking, so Whisper heard
                    # Vermithor's own TTS and created false wake phrases.
                    self._execute_voice_command(command)

                    self.awake = False

                    if self.running:

                        self._emit(
                            "status",
                            "Standby — say Vermithor"
                        )

                    continue

                # -------------------------------------------------
                # WAKE WORD ONLY
                # -------------------------------------------------

                self._emit(
                    "status",
                    "Awaiting command"
                )

                self.speak(
                    "Yes, Rohan?"
                )

                if self.running:

                    time.sleep(
                        0.15
                    )

                # -------------------------------------------------
                # LISTEN FOR COMPLETE COMMAND
                # -------------------------------------------------

                command = (
                    self._listen_for_command()
                )

                if not command:

                    self.awake = False

                    if self.running:

                        self._emit(
                            "status",
                            "Standby — say Vermithor"
                        )

                    continue

                self._emit(
                    "heard",
                    command
                )

                # -------------------------------------------------
                # EXECUTE BEFORE LISTENING AGAIN
                # -------------------------------------------------
                # Keep the microphone idle while actions and TTS are
                # running.  This prevents speaker feedback from being
                # transcribed as a new command or wake phrase.

                self._execute_voice_command(command)

                self.awake = False

                if self.running:

                    self._emit(
                        "status",
                        "Standby — say Vermithor"
                    )

            except KeyboardInterrupt:

                self._emit(
                    "log",
                    "Voice listener interrupted."
                )

                self.awake = False

                try:

                    self.voice.microphone_initialized = False

                except Exception:
                    pass

                break

            except Exception as exc:

                self._emit(
                    "log",
                    f"Voice loop error: "
                    f"{type(exc).__name__}: {exc}"
                )

                self.awake = False

                try:

                    self.voice.microphone_initialized = False

                except Exception:
                    pass

                time.sleep(
                    0.25
                )

        self.voice_mode = False

    # =============================================================
    # BACKGROUND START
    # =============================================================

    def start_voice_background(self):

        with self._lock:

            if (
                self._voice_thread
                and
                self._voice_thread.is_alive()
            ):

                return

            self.running = True
            self.voice_mode = True
            self.sleeping = False

            self._voice_thread = threading.Thread(
                target=self.run_voice,
                name="VermithorVoice",
                daemon=True
            )

            self._voice_thread.start()

    # =============================================================
    # MANUAL WAKE
    # =============================================================

    def wake(self):

        self.sleeping = False
        self.awake = False

        self._wake_event.set()

        self._emit(
            "status",
            "Standby — say Vermithor"
        )

    # =============================================================
    # SHUTDOWN
    # =============================================================

    def shutdown(self, speak=False):

        with self._lock:

            if not self.running:
                return

            if speak:

                try:

                    self.speak(
                        "Shutting down Vermithor."
                    )

                except Exception:
                    pass

            self.running = False
            self.voice_mode = False
            self.awake = False
            self.sleeping = True

            self._wake_event.set()

            try:

                self.voice.close()

            except Exception:
                pass

            try:

                self.tts.stop()

            except Exception:
                pass

            self._emit(
                "status",
                "Offline"
            )

    # =============================================================
    # COMPATIBILITY
    # =============================================================

    def run(self):

        self.start_voice_background()

        while self.running:

            time.sleep(
                0.25
            )

        self.shutdown()