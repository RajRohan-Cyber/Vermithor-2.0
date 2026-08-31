import base64
import queue
import subprocess
import threading
import time

import pythoncom
import win32com.client


class TextToSpeech:
    """
    Vermithor Windows Text-To-Speech engine.

    Primary:
        Windows SAPI.SpVoice through pywin32.

    Fallback:
        Windows PowerShell System.Speech.Synthesis.

    The fallback is intentionally included so that Vermithor
    can still speak if the SAPI COM interface has a problem.

    Speech is serialized through one worker thread so Vermithor
    never starts listening while it is speaking.
    """

    def __init__(self):
        self._queue = queue.Queue()
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._speaking = threading.Event()

        self._speaker = None
        self._com_initialized = False

        self._thread = threading.Thread(
            target=self._worker,
            name="Vermithor-TTS",
            daemon=True,
        )

        self._thread.start()

        if not self._ready.wait(timeout=15):
            print("⚠️ TTS engine did not initialize within 15 seconds.")
        else:
            print("🔊 Windows TTS engine ready.")

    # ==========================================================
    # WORKER
    # ==========================================================

    def _worker(self):
        """
        Dedicated TTS thread.

        All COM/SAPI operations happen inside this thread.
        """

        try:
            pythoncom.CoInitialize()
            self._com_initialized = True

            self._initialize_sapi()

        except Exception as exc:
            print(
                "⚠️ SAPI initialization failed: "
                f"{type(exc).__name__}: {exc}"
            )

        finally:
            self._ready.set()

        # ------------------------------------------------------
        # Speech queue
        # ------------------------------------------------------

        while not self._stop.is_set():

            try:
                item = self._queue.get(timeout=0.2)

            except queue.Empty:
                continue

            if item is None:
                self._queue.task_done()
                break

            text, finished = item

            try:
                self._speak_internal(text)

            except Exception as exc:
                print(
                    "⚠️ TTS error: "
                    f"{type(exc).__name__}: {exc}"
                )

                # ------------------------------------------------
                # Guaranteed fallback.
                # ------------------------------------------------

                try:
                    self._powershell_speak(text)

                except Exception as fallback_exc:
                    print(
                        "❌ Windows fallback TTS also failed: "
                        f"{type(fallback_exc).__name__}: "
                        f"{fallback_exc}"
                    )

            finally:

                self._speaking.clear()

                if finished is not None:
                    finished.set()

                self._queue.task_done()

        # ------------------------------------------------------
        # Release SAPI.
        # ------------------------------------------------------

        self._speaker = None

        if self._com_initialized:

            try:
                pythoncom.CoUninitialize()

            except Exception:
                pass

            self._com_initialized = False

    # ==========================================================
    # INITIALIZE SAPI
    # ==========================================================

    def _initialize_sapi(self):

        try:

            # DispatchEx creates an independent COM instance.
            self._speaker = win32com.client.DispatchEx(
                "SAPI.SpVoice"
            )

            self._speaker.Volume = 100
            self._speaker.Rate = 0

            # --------------------------------------------------
            # Make sure a usable voice exists.
            # --------------------------------------------------

            voices = self._speaker.GetVoices()

            if voices.Count > 0:

                # Prefer a Microsoft English voice if available.
                selected = None

                for i in range(voices.Count):

                    voice = voices.Item(i)

                    try:
                        description = str(
                            voice.GetDescription()
                        ).lower()

                    except Exception:
                        description = ""

                    if (
                        "david" in description
                        or "zira" in description
                        or "mark" in description
                        or "aria" in description
                        or "guy" in description
                    ):
                        selected = voice
                        break

                if selected is None:
                    selected = voices.Item(0)

                try:
                    self._speaker.Voice = selected

                except Exception:
                    pass

            # --------------------------------------------------
            # Use normal system audio output.
            # --------------------------------------------------

            try:

                outputs = self._speaker.GetAudioOutputs()

                if outputs.Count > 0:

                    self._speaker.AudioOutput = (
                        outputs.Item(0)
                    )

            except Exception:
                # Default Windows audio output is fine if
                # enumeration is unavailable.
                pass

            # --------------------------------------------------
            # Give SAPI enough time if another application is
            # temporarily using the audio device.
            # --------------------------------------------------

            try:
                self._speaker.SynchronousSpeakTimeout = 30000

            except Exception:
                pass

            print("✅ SAPI voice initialized.")

        except Exception:
            self._speaker = None
            raise

    # ==========================================================
    # INTERNAL SPEECH
    # ==========================================================

    def _speak_internal(self, text):

        if not text:
            return

        text = str(text).strip()

        if not text:
            return

        self._speaking.set()

        print(f"🔊 Speaking: {text}")

        # ------------------------------------------------------
        # Primary SAPI engine.
        # ------------------------------------------------------

        if self._speaker is not None:

            try:

                # Synchronous speech.
                #
                # Vermithor will not continue until Windows has
                # finished speaking this response.
                self._speaker.Speak(
                    text
                )

                return

            except Exception as exc:

                print(
                    "⚠️ SAPI Speak failed: "
                    f"{type(exc).__name__}: {exc}"
                )

                # ------------------------------------------------
                # Recreate SAPI once.
                # ------------------------------------------------

                try:

                    self._speaker = None

                    self._initialize_sapi()

                    self._speaker.Speak(
                        text
                    )

                    return

                except Exception as retry_exc:

                    print(
                        "⚠️ SAPI retry failed: "
                        f"{type(retry_exc).__name__}: "
                        f"{retry_exc}"
                    )

        # ------------------------------------------------------
        # If SAPI is unavailable, use PowerShell.
        # ------------------------------------------------------

        self._powershell_speak(text)

    # ==========================================================
    # POWERSHELL FALLBACK
    # ==========================================================

    def _powershell_speak(self, text):

        """
        Windows-native fallback.

        Uses System.Speech.Synthesis through PowerShell.

        The PowerShell command is sent as an encoded command,
        avoiding all quotation/escaping problems in PowerShell.
        """

        text = str(text).strip()

        if not text:
            return

        print("🔊 Using Windows speech fallback.")

        script = r"""
Add-Type -AssemblyName System.Speech

$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer

try {
    $speaker.Volume = 100
    $speaker.Rate = 0

    $speaker.Speak($env:VERMITHOR_TTS_TEXT)
}
finally {
    $speaker.Dispose()
}
"""

        encoded = base64.b64encode(
            script.encode("utf-16le")
        ).decode("ascii")

        environment = None

        try:
            import os

            environment = os.environ.copy()

            # Environment variables avoid shell quotation issues.
            environment[
                "VERMITHOR_TTS_TEXT"
            ] = text

            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-EncodedCommand",
                    encoded,
                ],
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:

                error = (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or "Unknown PowerShell TTS error"
                )

                raise RuntimeError(error)

        except subprocess.TimeoutExpired:

            raise RuntimeError(
                "Windows speech engine timed out."
            )

    # ==========================================================
    # PUBLIC SPEAK
    # ==========================================================

    def speak(self, text):

        if text is None:
            return

        text = str(text).strip()

        if not text:
            return

        # ------------------------------------------------------
        # Wait for TTS initialization.
        # ------------------------------------------------------

        if not self._ready.wait(timeout=15):

            print(
                "⚠️ TTS engine is not ready."
            )

            return

        if self._stop.is_set():
            return

        # ------------------------------------------------------
        # Queue speech.
        # ------------------------------------------------------

        finished = threading.Event()

        self._queue.put(
            (
                text,
                finished,
            )
        )

        # ------------------------------------------------------
        # IMPORTANT:
        #
        # Wait until Vermithor has actually finished speaking.
        #
        # This prevents:
        #
        #     SPEAK
        #         ↓
        #     LISTEN
        #
        # happening at the same time.
        # ------------------------------------------------------

        finished.wait()

    # ==========================================================
    # STATUS
    # ==========================================================

    def is_speaking(self):

        return self._speaking.is_set()

    # ==========================================================
    # STOP
    # ==========================================================

    def stop(self):

        """
        Stop accepting new speech.
        """

        if self._stop.is_set():
            return

        self._stop.set()

        try:

            self._queue.put_nowait(None)

        except Exception:
            pass

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(self):

        if self._stop.is_set():
            return

        self._stop.set()

        try:

            self._queue.put_nowait(None)

        except Exception:
            pass

        # ------------------------------------------------------
        # Wait for worker to exit.
        # ------------------------------------------------------

        if (
            threading.current_thread()
            is not self._thread
        ):

            try:

                self._thread.join(
                    timeout=5
                )

            except Exception:
                pass

        self._speaker = None

    # ==========================================================
    # DESTRUCTOR
    # ==========================================================

    def __del__(self):

        try:
            self.shutdown()

        except Exception:
            pass