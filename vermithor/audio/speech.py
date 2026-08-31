import os
import re
import threading
import time
from math import gcd

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


class SpeechRecognizer:
    """
    Vermithor Speech Recognition Engine

    Compatible with Vermithor core/assistant.py.

    Audio path:

        Microphone
             ↓
        Best input channel
             ↓
        Voice activity detection
             ↓
        Pre-roll
             ↓
        Resample to 16 kHz
             ↓
        Normalize
             ↓
        Faster-Whisper
             ↓
        Clean transcript
    """

    def __init__(
        self,
        state_callback=None,

        model_name="base.en",
        model_size=None,

        device=None,
        compute_device=None,

        compute_type="int8",

        sample_rate=16000,
        channels=1,

        command_max_seconds=12.0,
        command_start_timeout=5.0,
        command_silence_seconds=0.85,

        calibration_seconds=0.8,

        wake_max_seconds=5.0,
        wake_start_timeout=2.5,
        wake_silence_seconds=0.75,

        microphone_device=None,

        max_seconds=None,
        start_timeout=None,
        silence_seconds=None,

        **kwargs,
    ):

        # =========================================================
        # BACKWARD COMPATIBILITY
        # =========================================================

        if max_seconds is not None:
            command_max_seconds = max_seconds

        if start_timeout is not None:
            command_start_timeout = start_timeout

        if silence_seconds is not None:
            command_silence_seconds = silence_seconds

        # =========================================================
        # WHISPER SETTINGS
        # =========================================================

        self.model_name = (
            model_name
            or model_size
            or os.getenv(
                "WHISPER_MODEL",
                "base.en",
            )
        )

        if compute_device:
            self.device = compute_device

        elif device:
            self.device = device

        else:
            self.device = os.getenv(
                "WHISPER_DEVICE",
                "cpu",
            )

        self.compute_device = self.device

        self.compute_type = (
            compute_type
            or os.getenv(
                "WHISPER_COMPUTE",
                "int8",
            )
        )

        self.target_samplerate = 16000
        self.sample_rate = self.target_samplerate

        self.channels = int(channels)

        # =========================================================
        # COMMAND SETTINGS
        # =========================================================

        self.command_max_seconds = float(
            command_max_seconds
        )

        self.command_start_timeout = float(
            command_start_timeout
        )

        self.command_silence_seconds = float(
            command_silence_seconds
        )

        # =========================================================
        # WAKE SETTINGS
        # =========================================================

        self.wake_max_seconds = float(
            wake_max_seconds
        )

        self.wake_start_timeout = float(
            wake_start_timeout
        )

        self.wake_silence_seconds = float(
            wake_silence_seconds
        )

        # =========================================================
        # CALIBRATION
        # =========================================================

        self.calibration_seconds = float(
            calibration_seconds
        )

        # =========================================================
        # MICROPHONE
        # =========================================================

        env_device = os.getenv(
            "VERMITHOR_MIC_DEVICE",
            "",
        ).strip()

        if microphone_device is not None:

            self.input_device = microphone_device

        elif env_device:

            try:
                self.input_device = int(
                    env_device
                )

            except ValueError:
                self.input_device = env_device

        else:
            self.input_device = 1

        self.native_rate = 44100

        self.capture_channels = 1

        self.device_info = None

        # =========================================================
        # STATE
        # =========================================================

        self.model = None

        self.initialized = False
        self.microphone_initialized = False

        self.running = True

        self.state_callback = (
            state_callback
            if callable(state_callback)
            else lambda state: None
        )

        self._lock = threading.RLock()

        self._last_audio_error = 0.0

        # =========================================================
        # AUDIO LEVELS
        # =========================================================

        self.noise_floor = 0.00001

        # Slightly higher start threshold prevents random
        # background audio from activating the recorder.
        self.speech_threshold = 0.0030

        self.minimum_speech_seconds = 0.35

        # Hysteresis prevents the recorder from constantly
        # switching between speech and silence.
        self.continue_threshold = 0.0015

        # =========================================================
        # WAKE WORDS
        # =========================================================

        self.vermithor_variations = {
            "vermithor",
            "vermitor",
            "varmithor",
            "varmithore",
            "vermathor",
            "vermither",
            "vermethor",
            "verminthor",
            "vermithur",
            "vermithore",
            "vermiter",
            "vermetor",
            "vermithar",
            "vermith",
            "vermithole",
            "ver mithor",
            "ver mith or",
            "vermith or",
            "ver mythor",
            "ver myth or",
            "vermitor",
            "vermitho",
            "vermithore",
        }

        self.wake_phrases = (
            "hello vermithor",
            "hey vermithor",
            "hi vermithor",
        )

    # =============================================================
    # STATE
    # =============================================================

    def state(self, value):

        try:
            self.state_callback(value)

        except Exception:
            pass

    # =============================================================
    # INITIALIZATION
    # =============================================================

    def initialize(self):

        with self._lock:

            if self.initialized:
                return True

            try:

                print()
                print(
                    "Loading local Whisper speech engine..."
                )

                print(
                    f"Model: {self.model_name}"
                )

                print(
                    f"Device: {self.device}"
                )

                print(
                    f"Compute: {self.compute_type}"
                )

                self.state("loading")

                self.model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type,
                    cpu_threads=max(
                        2,
                        min(
                            os.cpu_count() or 4,
                            8,
                        ),
                    ),
                    num_workers=1,
                )

                print(
                    "Whisper model loaded."
                )

                if not self.initialize_microphone():

                    self.model = None

                    return False

                self.initialized = True

                print(
                    "Whisper + microphone ready."
                )

                return True

            except Exception as exc:

                self.initialized = False
                self.microphone_initialized = False
                self.model = None

                print(
                    "Voice initialization error: "
                    f"{type(exc).__name__}: {exc}"
                )

                return False

    # =============================================================
    # MICROPHONE INITIALIZATION
    # =============================================================

    def initialize_microphone(self):

        with self._lock:

            if (
                self.microphone_initialized
                and self.device_info is not None
            ):
                return True

            try:

                devices = sd.query_devices()

                candidate = self.input_device

                # -------------------------------------------------
                # DEVICE NAME SEARCH
                # -------------------------------------------------

                if isinstance(candidate, str):

                    found = None

                    for index, device in enumerate(devices):

                        name = str(
                            device.get(
                                "name",
                                "",
                            )
                        )

                        inputs = int(
                            device.get(
                                "max_input_channels",
                                0,
                            )
                        )

                        if (
                            candidate.lower()
                            in name.lower()
                            and inputs > 0
                        ):

                            found = index
                            break

                    candidate = found

                # -------------------------------------------------
                # VALIDATE SELECTED DEVICE
                # -------------------------------------------------

                if candidate is not None:

                    try:

                        candidate = int(
                            candidate
                        )

                        if (
                            candidate < 0
                            or candidate >= len(devices)
                            or int(
                                devices[candidate].get(
                                    "max_input_channels",
                                    0,
                                )
                            ) <= 0
                        ):

                            candidate = None

                    except Exception:

                        candidate = None

                # -------------------------------------------------
                # WINDOWS DEFAULT INPUT
                # -------------------------------------------------

                if candidate is None:

                    try:

                        default_device = (
                            sd.default.device
                        )

                        if (
                            default_device is not None
                            and len(default_device) >= 1
                        ):

                            default_input = (
                                default_device[0]
                            )

                            if default_input is not None:

                                default_input = int(
                                    default_input
                                )

                                if (
                                    0
                                    <= default_input
                                    < len(devices)
                                ):

                                    if int(
                                        devices[
                                            default_input
                                        ].get(
                                            "max_input_channels",
                                            0,
                                        )
                                    ) > 0:

                                        candidate = (
                                            default_input
                                        )

                    except Exception:
                        pass

                # -------------------------------------------------
                # CONEXANT FALLBACK
                # -------------------------------------------------

                if candidate is None:

                    for index, device in enumerate(devices):

                        name = str(
                            device.get(
                                "name",
                                "",
                            )
                        ).lower()

                        inputs = int(
                            device.get(
                                "max_input_channels",
                                0,
                            )
                        )

                        if (
                            inputs > 0
                            and "conexant" in name
                            and "stereo mix" not in name
                        ):

                            candidate = index
                            break

                # -------------------------------------------------
                # GENERIC MICROPHONE FALLBACK
                # -------------------------------------------------

                if candidate is None:

                    for index, device in enumerate(devices):

                        name = str(
                            device.get(
                                "name",
                                "",
                            )
                        ).lower()

                        inputs = int(
                            device.get(
                                "max_input_channels",
                                0,
                            )
                        )

                        if (
                            inputs > 0
                            and "stereo mix" not in name
                        ):

                            candidate = index
                            break

                if candidate is None:

                    raise RuntimeError(
                        "No usable microphone was found."
                    )

                self.input_device = int(
                    candidate
                )

                self.device_info = (
                    sd.query_devices(
                        self.input_device,
                        "input",
                    )
                )

                self.native_rate = int(
                    round(
                        float(
                            self.device_info.get(
                                "default_samplerate",
                                44100,
                            )
                        )
                    )
                )

                available_channels = int(
                    self.device_info.get(
                        "max_input_channels",
                        1,
                    )
                )

                # Use one channel for speech recognition.
                # This avoids phase/channel problems with some
                # Conexant stereo microphone drivers.
                self.capture_channels = 1

                print(
                    "Microphone device: "
                    f"{self.input_device}"
                )

                print(
                    "Microphone: "
                    f"{self.device_info.get('name', '')}"
                )

                print(
                    "Microphone native rate: "
                    f"{self.native_rate}"
                )

                print(
                    "Whisper rate: "
                    f"{self.target_samplerate}"
                )

                print(
                    "Input channels: "
                    f"{available_channels}"
                )

                print(
                    "Capture channels: "
                    f"{self.capture_channels}"
                )

                self._test_microphone()

                self._calibrate()

                self.microphone_initialized = True

                return True

            except Exception as exc:

                self.microphone_initialized = False

                print(
                    "Microphone initialization error: "
                    f"{type(exc).__name__}: {exc}"
                )

                return False

    # =============================================================
    # MICROPHONE TEST
    # =============================================================

    def _test_microphone(self):

        frames = int(
            self.native_rate * 0.5
        )

        try:

            audio = sd.rec(
                frames,
                samplerate=self.native_rate,
                channels=self.capture_channels,
                dtype="float32",
                device=self.input_device,
                blocking=True,
            )

            audio = self._best_channel(
                audio
            )

            rms = self._rms(
                audio
            )

            peak = (
                float(
                    np.max(
                        np.abs(audio)
                    )
                )
                if audio.size
                else 0.0
            )

            print(
                f"Microphone test RMS: "
                f"{rms:.5f}"
            )

            print(
                f"Microphone test peak: "
                f"{peak:.5f}"
            )

            if peak < 0.001:

                print(
                    "WARNING: microphone signal is "
                    "extremely low while idle."
                )

        except Exception as exc:

            raise RuntimeError(
                "Microphone test failed: "
                f"{type(exc).__name__}: {exc}"
            )

    # =============================================================
    # CALIBRATION
    # =============================================================

    def _calibrate(self):

        print(
            "Calibrating microphone..."
        )

        print(
            "Please remain silent during calibration."
        )

        try:

            duration = max(
                0.5,
                self.calibration_seconds,
            )

            frames = int(
                self.native_rate * duration
            )

            audio = sd.rec(
                frames,
                samplerate=self.native_rate,
                channels=self.capture_channels,
                dtype="float32",
                device=self.input_device,
                blocking=True,
            )

            audio = self._best_channel(
                audio
            )

            if audio.size == 0:
                return

            block_size = max(
                256,
                int(
                    self.native_rate * 0.10
                ),
            )

            levels = []

            for start in range(
                0,
                len(audio),
                block_size,
            ):

                block = audio[
                    start:start + block_size
                ]

                if block.size:

                    levels.append(
                        self._rms(
                            block
                        )
                    )

            if levels:

                # Use a high percentile instead of the median.
                # This makes VAD more robust against occasional
                # background noise.
                self.noise_floor = float(
                    np.percentile(
                        levels,
                        80,
                    )
                )

            # The microphone in your log has an extremely low
            # idle level, so don't let calibration make the
            # assistant hypersensitive.
            self.speech_threshold = max(
                self.noise_floor * 5.0,
                0.0025,
            )

            self.speech_threshold = min(
                self.speech_threshold,
                0.0080,
            )

            self.continue_threshold = max(
                self.speech_threshold * 0.45,
                self.noise_floor * 2.5,
                0.0010,
            )

            print(
                f"Noise floor: "
                f"{self.noise_floor:.5f}"
            )

            print(
                f"Speech start threshold: "
                f"{self.speech_threshold:.5f}"
            )

            print(
                f"Speech continue threshold: "
                f"{self.continue_threshold:.5f}"
            )

        except Exception as exc:

            print(
                "Calibration warning: "
                f"{type(exc).__name__}: {exc}"
            )

            self.noise_floor = 0.00001
            self.speech_threshold = 0.0025
            self.continue_threshold = 0.0011

    # =============================================================
    # AUDIO HELPERS
    # =============================================================

    @staticmethod
    def _rms(audio):

        audio = np.asarray(
            audio,
            dtype=np.float32,
        )

        if audio.size == 0:
            return 0.0

        return float(
            np.sqrt(
                np.mean(
                    np.square(
                        audio
                    )
                )
            )
        )

    @staticmethod
    def _best_channel(audio):

        audio = np.asarray(
            audio,
            dtype=np.float32,
        )

        if audio.size == 0:

            return np.empty(
                0,
                dtype=np.float32,
            )

        if audio.ndim == 1:
            return audio

        if audio.shape[1] == 1:
            return audio[:, 0]

        best_index = 0
        best_level = -1.0

        for index in range(
            audio.shape[1]
        ):

            level = (
                SpeechRecognizer._rms(
                    audio[:, index]
                )
            )

            if level > best_level:

                best_level = level
                best_index = index

        return np.asarray(
            audio[:, best_index],
            dtype=np.float32,
        )

    # =============================================================
    # RESAMPLE
    # =============================================================

    @staticmethod
    def _resample(
        audio,
        source_rate,
        target_rate,
    ):

        audio = np.asarray(
            audio,
            dtype=np.float32,
        )

        if audio.size == 0:
            return audio

        source_rate = int(
            source_rate
        )

        target_rate = int(
            target_rate
        )

        if source_rate == target_rate:
            return audio

        try:

            from scipy.signal import resample_poly

            divisor = gcd(
                source_rate,
                target_rate,
            )

            up = (
                target_rate
                // divisor
            )

            down = (
                source_rate
                // divisor
            )

            result = resample_poly(
                audio,
                up,
                down,
            )

            return np.asarray(
                result,
                dtype=np.float32,
            )

        except Exception:

            old_length = len(
                audio
            )

            new_length = int(
                old_length
                * target_rate
                / source_rate
            )

            if new_length <= 1:
                return audio

            old_positions = np.linspace(
                0,
                1,
                old_length,
            )

            new_positions = np.linspace(
                0,
                1,
                new_length,
            )

            result = np.interp(
                new_positions,
                old_positions,
                audio,
            )

            return np.asarray(
                result,
                dtype=np.float32,
            )

    # =============================================================
    # NORMALIZE
    # =============================================================

    def _normalize_audio(self, audio):

        if audio is None:
            return None

        audio = np.asarray(
            audio,
            dtype=np.float32,
        )

        if audio.size == 0:
            return audio

        audio = (
            audio
            - np.mean(audio)
        )

        peak = float(
            np.max(
                np.abs(audio)
            )
        )

        if peak <= 0:
            return audio

        if peak < 0.18:

            gain = min(
                0.65 / peak,
                3.0,
            )

            audio = (
                audio * gain
            )

        elif peak > 0.95:

            audio = (
                audio
                * (
                    0.95 / peak
                )
            )

        return np.clip(
            audio,
            -0.98,
            0.98,
        ).astype(
            np.float32
        )

    # =============================================================
    # RECORD
    # =============================================================

    def _record(
        self,
        max_seconds,
        start_timeout,
        silence_seconds,
    ):

        if not self.microphone_initialized:

            if not self.initialize_microphone():
                return None

        block_seconds = 0.05

        block_frames = max(
            256,
            int(
                self.native_rate
                * block_seconds
            ),
        )

        maximum_blocks = max(
            1,
            int(
                max_seconds
                / block_seconds
            ),
        )

        start_timeout_blocks = max(
            1,
            int(
                start_timeout
                / block_seconds
            ),
        )

        silence_blocks = max(
            1,
            int(
                silence_seconds
                / block_seconds
            ),
        )

        # 400 ms pre-roll.
        pre_roll_blocks = 8

        pre_roll = []
        captured = []

        speech_started = False

        # Number of consecutive blocks that must contain
        # real speech before recording actually begins.
        speech_confirmation_blocks = 2
        speech_confirmation_count = 0

        silence_count = 0
        waiting_count = 0

        # Keep a little audio after the user stops.
        tail_blocks = 3

        self.state(
            "listening"
        )

        try:

            with sd.InputStream(
                samplerate=self.native_rate,
                channels=self.capture_channels,
                dtype="float32",
                device=self.input_device,
                blocksize=block_frames,
                latency="high",
            ) as stream:

                for _ in range(
                    maximum_blocks
                ):

                    data, overflowed = (
                        stream.read(
                            block_frames
                        )
                    )

                    if data is None:
                        continue

                    samples = (
                        self._best_channel(
                            data
                        )
                    )

                    if samples.size == 0:
                        continue

                    level = self._rms(
                        samples
                    )

                    # -------------------------------------------------
                    # WAITING FOR SPEECH
                    # -------------------------------------------------

                    if not speech_started:

                        pre_roll.append(
                            samples.copy()
                        )

                        if (
                            len(pre_roll)
                            > pre_roll_blocks
                        ):

                            pre_roll.pop(
                                0
                            )

                        waiting_count += 1

                        if (
                            level
                            >= self.speech_threshold
                        ):

                            speech_confirmation_count += 1

                        else:

                            speech_confirmation_count = 0

                        # Require actual speech across multiple
                        # blocks before activating.
                        if (
                            speech_confirmation_count
                            >= speech_confirmation_blocks
                        ):

                            speech_started = True

                            captured.extend(
                                pre_roll
                            )

                            # Don't add the same block twice.
                            if not captured or not np.array_equal(
                                captured[-1],
                                samples,
                            ):

                                captured.append(
                                    samples.copy()
                                )

                            silence_count = 0

                        elif (
                            waiting_count
                            >= start_timeout_blocks
                        ):

                            return None

                        continue

                    # -------------------------------------------------
                    # SPEECH ACTIVE
                    # -------------------------------------------------

                    captured.append(
                        samples.copy()
                    )

                    continue_threshold = (
                        self.continue_threshold
                    )

                    if (
                        level
                        < continue_threshold
                    ):

                        silence_count += 1

                    else:

                        silence_count = 0

                    # -------------------------------------------------
                    # END AFTER SILENCE
                    # -------------------------------------------------

                    if (
                        silence_count
                        >= silence_blocks
                    ):

                        # Keep a small amount of audio after the
                        # last spoken word.
                        for _ in range(
                            tail_blocks
                        ):

                            try:

                                tail_data, _ = (
                                    stream.read(
                                        block_frames
                                    )
                                )

                                if (
                                    tail_data
                                    is not None
                                ):

                                    tail_samples = (
                                        self._best_channel(
                                            tail_data
                                        )
                                    )

                                    if (
                                        tail_samples.size
                                    ):

                                        captured.append(
                                            tail_samples
                                        )

                            except Exception:
                                break

                        break

        except Exception as exc:

            now = time.monotonic()

            if (
                now
                - self._last_audio_error
                > 1.0
            ):

                print(
                    "Microphone recording error: "
                    f"{type(exc).__name__}: {exc}"
                )

                self._last_audio_error = now

            self.microphone_initialized = False

            return None

        if not captured:
            return None

        audio = np.concatenate(
            captured
        ).astype(
            np.float32
        )

        if audio.size == 0:
            return None

        audio = self._trim_tail(
            audio
        )

        audio = self._resample(
            audio,
            self.native_rate,
            self.target_samplerate,
        )

        audio = self._normalize_audio(
            audio
        )

        duration = (
            len(audio)
            / self.target_samplerate
        )

        print(
            f"Audio captured: "
            f"{duration:.2f}s | "
            f"RMS: {self._rms(audio):.5f}"
        )

        if (
            duration
            < self.minimum_speech_seconds
        ):

            return None

        return audio

    # =============================================================
    # TRIM SILENT TAIL
    # =============================================================

    def _trim_tail(self, audio):

        if audio is None:
            return audio

        if audio.size == 0:
            return audio

        threshold = max(
            self.continue_threshold * 0.60,
            0.00035,
        )

        block_size = max(
            256,
            int(
                self.native_rate * 0.05
            ),
        )

        last_active = None

        for start in range(
            0,
            len(audio),
            block_size,
        ):

            block = audio[
                start:start + block_size
            ]

            if block.size == 0:
                continue

            level = self._rms(
                block
            )

            if level >= threshold:

                last_active = (
                    start
                    + len(block)
                    - 1
                )

        if last_active is None:
            return audio

        # Keep 350 ms after the final active block.
        after = int(
            self.native_rate * 0.35
        )

        last = min(
            len(audio) - 1,
            last_active + after,
        )

        return audio[
            :last + 1
        ]

    # =============================================================
    # TRANSCRIPTION
    # =============================================================

    def _transcribe(
        self,
        audio,
        wake=False,
    ):

        if self.model is None:
            return ""

        if audio is None:
            return ""

        minimum = int(
            self.target_samplerate
            * 0.35
        )

        if len(audio) < minimum:
            return ""

        try:

            if wake:

                initial_prompt = (
                    "Vermithor. "
                    "Hey Vermithor. "
                    "Hello Vermithor. "
                    "Hi Vermithor."
                )

                beam_size = 5
                best_of = 5

            else:

                initial_prompt = (
                    "A command to a Windows "
                    "desktop assistant named Vermithor."
                )

                beam_size = 5
                best_of = 5

            segments, info = (
                self.model.transcribe(
                    audio,

                    language="en",
                    task="transcribe",

                    beam_size=beam_size,
                    best_of=best_of,
                    patience=1.0,

                    temperature=0.0,

                    condition_on_previous_text=False,

                    suppress_blank=True,

                    without_timestamps=True,

                    vad_filter=True,

                    vad_parameters=dict(
                        min_silence_duration_ms=450,
                        speech_pad_ms=250,
                        min_speech_duration_ms=150,
                    ),

                    no_speech_threshold=0.70,

                    log_prob_threshold=-2.8,

                    compression_ratio_threshold=2.4,

                    initial_prompt=initial_prompt,
                )
            )

            parts = []

            for segment in segments:

                text = str(
                    segment.text or ""
                ).strip()

                if not text:
                    continue

                avg_logprob = getattr(
                    segment,
                    "avg_logprob",
                    None,
                )

                no_speech_prob = getattr(
                    segment,
                    "no_speech_prob",
                    None,
                )

                compression_ratio = getattr(
                    segment,
                    "compression_ratio",
                    None,
                )

                if (
                    avg_logprob is not None
                    and avg_logprob < -2.8
                ):

                    continue

                if (
                    no_speech_prob is not None
                    and no_speech_prob >= 0.90
                ):

                    continue

                if (
                    compression_ratio is not None
                    and compression_ratio >= 2.4
                ):

                    continue

                parts.append(
                    text
                )

            text = " ".join(
                parts
            )

            text = self._clean_text(
                text
            )

            # Correct common Whisper spellings of the assistant
            # name before wake-word matching.
            text = self._repair_vermithor(
                text
            )

            return text

        except Exception as exc:

            print(
                "Whisper transcription error: "
                f"{type(exc).__name__}: {exc}"
            )

            return ""

    # =============================================================
    # VERMITHOR TRANSCRIPT REPAIR
    # =============================================================

    def _repair_vermithor(self, text):

        if not text:
            return ""

        words = text.split()

        repaired = []

        for word in words:

            stripped = word.strip(
                ".,!?;:"
            )

            if self._is_vermithor(
                stripped
            ):

                repaired.append(
                    "Vermithor"
                )

            else:

                repaired.append(
                    word
                )

        return " ".join(
            repaired
        ).strip()

    # =============================================================
    # CLEAN TRANSCRIPT
    # =============================================================

    @staticmethod
    def _clean_text(text):

        if not text:
            return ""

        text = re.sub(
            r"\s+",
            " ",
            str(text),
        ).strip()

        if not text:
            return ""

        words = text.split()

        cleaned = []

        previous = None
        repeat_count = 0

        for word in words:

            normalized = (
                word
                .lower()
                .strip(
                    ".,!?;:"
                )
            )

            if normalized == previous:

                repeat_count += 1

                if repeat_count >= 2:
                    continue

            else:

                repeat_count = 0

            cleaned.append(
                word
            )

            previous = normalized

        text = " ".join(
            cleaned
        )

        lower = text.lower()

        hallucinations = (
            "thanks for watching",
            "thank you for watching",
            "please subscribe",
            "subscribe to my channel",
            "like and subscribe",
            "see you in the next video",
            "thanks for listening",
            "we'll see you next time",
            "we will see you next time",
            "see you next time",
            "thank you",
            "thanks for watching this video",
        )

        if any(
            phrase in lower
            for phrase in hallucinations
        ):

            return ""

        return text.strip()

    # =============================================================
    # NORMALIZATION
    # =============================================================

    @staticmethod
    def _normalize(text):

        text = str(
            text or ""
        ).lower()

        text = text.replace(
            "-",
            " ",
        )

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # =============================================================
    # LEVENSHTEIN
    # =============================================================

    @staticmethod
    def _levenshtein(a, b):

        if a == b:
            return 0

        if not a:
            return len(b)

        if not b:
            return len(a)

        previous = list(
            range(
                len(b) + 1
            )
        )

        for i, ca in enumerate(
            a,
            1,
        ):

            current = [i]

            for j, cb in enumerate(
                b,
                1,
            ):

                insertion = (
                    current[j - 1]
                    + 1
                )

                deletion = (
                    previous[j]
                    + 1
                )

                substitution = (
                    previous[j - 1]
                    + (
                        0
                        if ca == cb
                        else 1
                    )
                )

                current.append(
                    min(
                        insertion,
                        deletion,
                        substitution,
                    )
                )

            previous = current

        return previous[-1]

    # =============================================================
    # VERMITHOR MATCH
    # =============================================================

    def _is_vermithor(
        self,
        word,
    ):

        word = self._normalize(
            word
        )

        if not word:
            return False

        if word == "vermithor":
            return True

        if word in self.vermithor_variations:
            return True

        compact = word.replace(
            " ",
            "",
        )

        # "vermithor" is 9 letters. Requiring a compact form
        # close to that length, plus at most a 1-letter edit
        # distance, keeps genuine mispronunciations working
        # (they're already covered by vermithor_variations
        # above) while stopping ordinary 7-8 letter words
        # picked up by Whisper from being treated as a wake
        # word.

        if len(compact) < 8 or len(compact) > 11:
            return False

        return (
            self._levenshtein(
                compact,
                "vermithor",
            )
            <= 1
        )

    # =============================================================
    # WAKE PHRASE DETECTION
    # =============================================================

    def _is_wake_phrase(
        self,
        text,
    ):

        normalized = self._normalize(
            text
        )

        if not normalized:
            return False

        words = normalized.split()

        greetings = {
            "hello",
            "hey",
            "hi",
        }

        # ---------------------------------------------------------
        # Hello/Hey/Hi Vermithor
        # ---------------------------------------------------------

        for index in range(
            len(words) - 1
        ):

            first = words[index]
            second = words[index + 1]

            if (
                first in greetings
                and self._is_vermithor(
                    second
                )
            ):

                return True

        # ---------------------------------------------------------
        # Vermithor by itself
        # ---------------------------------------------------------

        for word in words:

            if self._is_vermithor(
                word
            ):

                return True

        return False

    # =============================================================
    # EXTRACT WAKE + COMMAND
    # =============================================================

    def _extract_wake_command(
        self,
        text,
    ):

        normalized = self._normalize(
            text
        )

        if not normalized:

            return (
                False,
                "",
            )

        words = normalized.split()

        greetings = {
            "hello",
            "hey",
            "hi",
        }

        # ---------------------------------------------------------
        # Hello Vermithor command
        # ---------------------------------------------------------

        for index in range(
            len(words) - 1
        ):

            if (
                words[index] in greetings
                and self._is_vermithor(
                    words[index + 1]
                )
            ):

                command = " ".join(
                    words[
                        index + 2:
                    ]
                ).strip()

                return (
                    True,
                    command,
                )

        # ---------------------------------------------------------
        # Vermithor command
        # ---------------------------------------------------------

        for index, word in enumerate(
            words
        ):

            if self._is_vermithor(
                word
            ):

                command = " ".join(
                    words[
                        index + 1:
                    ]
                ).strip()

                return (
                    True,
                    command,
                )

        return (
            False,
            "",
        )

    # =============================================================
    # WAKE LISTENER
    # =============================================================

    def wake_listener(
        self,
        *args,
        **kwargs,
    ):

        return self.listen_wake(
            *args,
            **kwargs,
        )

    # =============================================================
    # LISTEN FOR WAKE
    # =============================================================

    def listen_wake(
        self,
        *args,
        **kwargs,
    ):

        if not self.initialized:

            if not self.initialize():
                return ""

        audio = self._record(
            max_seconds=self.wake_max_seconds,
            start_timeout=self.wake_start_timeout,
            silence_seconds=self.wake_silence_seconds,
        )

        if audio is None:
            return ""

        text = self._transcribe(
            audio,
            wake=True,
        )

        if not text:
            return ""

        print(
            f"Wake check: {text}"
        )

        if not self._is_wake_phrase(
            text
        ):

            return ""

        print(
            f"Wake phrase detected: {text}"
        )

        return text

    # =============================================================
    # LISTEN FOR COMMAND
    # =============================================================

    def listen_command(
        self,
        *args,
        **kwargs,
    ):

        if not self.initialized:

            if not self.initialize():
                return ""

        audio = self._record(
            max_seconds=self.command_max_seconds,
            start_timeout=self.command_start_timeout,
            silence_seconds=self.command_silence_seconds,
        )

        if audio is None:
            return ""

        text = self._transcribe(
            audio,
            wake=False,
        )

        if not text:
            return ""

        print(
            f"Heard: {text}"
        )

        return text

    # =============================================================
    # GENERIC LISTEN
    # =============================================================

    def listen(
        self,
        *args,
        **kwargs,
    ):

        return self.listen_command(
            *args,
            **kwargs,
        )

    # =============================================================
    # CLOSE
    # =============================================================

    def close(self):

        with self._lock:

            self.running = False

            self.microphone_initialized = False
            self.initialized = False

            self.device_info = None

            self.model = None

            print(
                "Speech engine closed."
            )