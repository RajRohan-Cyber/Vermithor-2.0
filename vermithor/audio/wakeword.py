import os
import re
from difflib import SequenceMatcher

from dotenv import load_dotenv

load_dotenv()


class WakeWord:

    def __init__(self):

        self.primary_name = "vermithor"

        configured = os.getenv(
            "WAKE_WORDS",
            "vermithor,vermitor,vermithar,vermithur,vermithole,"
            "varmithor,varmithole,vermithore,vermiform,mithor"
        )

        self.wake_words = {
            self.normalize(item)
            for item in configured.split(",")
            if self.normalize(item)
        }

        self.wake_words.add("vermithor")

        self.hello_enabled = (
            os.getenv("HELLO_WAKE", "true").lower()
            in {"1", "true", "yes", "on"}
        )

        self.hello_words = {
            "hello",
            "hey"
        }

        # Common Whisper mistakes for Vermithor.
        self.common_variants = {
            "vermithor",
            "vermitor",
            "vermithar",
            "vermithur",
            "vermithole",
            "vermithore",
            "varmithor",
            "varmithole",
            "vermiform",
            "mithor",
            "vermentor",
            "vermitor"
        }

    @staticmethod
    def normalize(text):

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            (text or "").lower()
        )

        return re.sub(
            r"\s+",
            " ",
            text
        ).strip()

    def _similarity(self, a, b):

        return SequenceMatcher(
            None,
            a,
            b
        ).ratio()

    def _is_name_variant(self, word):

        word = self.normalize(word)

        if not word:
            return False

        if word in self.common_variants:
            return True

        if word == "vermithor":
            return True

        # Keep fuzzy matching conservative enough
        # that ordinary words aren't accidentally
        # treated as the assistant's name.
        score = self._similarity(
            word,
            "vermithor"
        )

        return score >= 0.70

    def _is_hello(self, word):

        return (
            self.hello_enabled
            and
            self.normalize(word)
            in self.hello_words
        )

    def detected(self, text):

        normalized = self.normalize(text)

        if not normalized:
            return False

        words = normalized.split()

        # "hello" / "hey"
        if any(
            self._is_hello(word)
            for word in words
        ):
            return True

        # Vermithor and Whisper variants
        if any(
            self._is_name_variant(word)
            for word in words
        ):
            return True

        # Multi-word configured wake phrases
        for wake in self.wake_words:

            if " " in wake and wake in normalized:
                return True

        return False

    def is_wake_only(self, text):

        if not self.detected(text):
            return False

        return not self.remove_wake_word(text)

    def remove_wake_word(self, text):

        original = (text or "").strip()

        if not original:
            return ""

        words = original.split()
        result = []

        for word in words:

            normalized = self.normalize(word)

            if not normalized:
                continue

            if self._is_hello(normalized):
                continue

            if self._is_name_variant(normalized):
                continue

            result.append(word)

        cleaned = " ".join(result)

        # Remove configured multi-word phrases.
        for wake in sorted(
            self.wake_words,
            key=len,
            reverse=True
        ):

            if " " not in wake:
                continue

            cleaned = re.sub(
                rf"\b{re.escape(wake)}\b",
                " ",
                cleaned,
                flags=re.IGNORECASE
            )

        return re.sub(
            r"\s+",
            " ",
            cleaned
        ).strip(" ,.!?")

    def extract_command(self, text):

        """
        Returns:

            (wake_detected, command)

        Examples:

            Hello
            -> (True, "")

            Hello Vermithor
            -> (True, "")

            Hello Vermithor open Chrome
            -> (True, "open Chrome")

            Varmithole play Believer
            -> (True, "play Believer")
        """

        if not self.detected(text):
            return False, ""

        return True, self.remove_wake_word(text)