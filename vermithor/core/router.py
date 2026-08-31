import os
import re

from datetime import datetime


class CommandRouter:

    def __init__(
        self,
        apps,
        browser,
        files,
        system,
        automation,
        system_manager,
        memory
    ):
        self.apps = apps
        self.browser = browser
        self.files = files
        self.system = system
        self.automation = automation
        self.system_manager = system_manager
        self.memory = memory

    # =========================================================
    # CLEAN COMMAND
    # =========================================================

    @staticmethod
    def _clean(text):

        text = re.sub(
            r"\s+",
            " ",
            (text or "").strip()
        )

        text = re.sub(
            r"^(please|can you|could you|"
            r"would you|will you)\s+",
            "",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\s+(please|for me)\s*$",
            "",
            text,
            flags=re.IGNORECASE
        )

        return text.strip(
            " .,!?"
        )

    # =========================================================
    # YOUTUBE QUERY CLEANER
    # =========================================================

    @staticmethod
    def _clean_youtube_query(query):

        query = re.sub(
            r"\s+",
            " ",
            (query or "").strip()
        )

        if not query:
            return ""

        # Remove trailing YouTube wording.

        query = re.sub(
            r"\s+(?:on|in)\s+you\s*tube\s*$",
            "",
            query,
            flags=re.IGNORECASE
        )

        # Remove polite filler.

        query = re.sub(
            r"^(?:please\s+)+",
            "",
            query,
            flags=re.IGNORECASE
        )

        query = re.sub(
            r"\s+(?:please|for me)\s*$",
            "",
            query,
            flags=re.IGNORECASE
        )

        # Only remove media descriptors at the END.

        query = re.sub(
            r"\s+(?:song|music|track|video)\s*$",
            "",
            query,
            flags=re.IGNORECASE
        )

        query = re.sub(
            r"\s+",
            " ",
            query
        ).strip()

        return query.strip(
            " .,!?"
        )

    # =========================================================
    # ROUTE
    # =========================================================

    def route(
        self,
        text
    ):

        raw = self._clean(
            text
        )

        command = raw.lower()

        if not command:
            return None

        # =====================================================
        # MEMORY
        # =====================================================

        if re.match(
            r"^(remember|remember that)\s+",
            command
        ):

            fact = re.sub(
                r"^(remember|remember that)\s+",
                "",
                raw,
                flags=re.IGNORECASE
            ).strip()

            self.memory.remember(
                fact
            )

            return (
                "I'll remember that."
            )

        if command in {
            "what do you remember",
            "what do you know about me",
            "remembered facts"
        }:

            facts = (
                self.memory.get_facts()
            )

            if not facts:

                return (
                    "I don't have anything "
                    "saved yet."
                )

            return (
                "I remember: "
                +
                "; ".join(
                    facts
                )
            )

        if command in {
            "clear memory",
            "forget everything",
            "forget what you remember"
        }:

            self.memory.clear()

            return (
                "My stored memory has been cleared."
            )

        # =====================================================
        # TIME
        # =====================================================

        if (
            "what time is it" in command
            or
            "what is the time" in command
            or
            "what's the time" in command
            or
            "tell me the time" in command
            or
            command == "current time"
        ):

            return datetime.now().strftime(
                "It is %I:%M %p."
            )

        # =====================================================
        # DATE
        # =====================================================

        if (
            "what is today's date" in command
            or
            "what's today's date" in command
            or
            "what is the date" in command
            or
            "what's the date" in command
            or
            command == "today's date"
        ):

            return datetime.now().strftime(
                "Today is %A, %B %d, %Y."
            )

        # =====================================================
        # COMMON WEBSITES
        # =====================================================

        if command in {
            "open google",
            "launch google",
            "start google"
        }:

            return self.browser.open_google()

        if command in {
            "open youtube",
            "launch youtube",
            "start youtube"
        }:

            return self.browser.open_youtube()

        if command in {
            "open gmail",
            "open google mail"
        }:

            return self.browser.open_url(
                "https://mail.google.com"
            )

        if command in {
            "open github",
            "open git hub"
        }:

            return self.browser.open_url(
                "https://github.com"
            )

        if command in {
            "open chatgpt",
            "open chat gpt"
        }:

            return self.browser.open_url(
                "https://chatgpt.com"
            )

        # =====================================================
        # URL
        # =====================================================

        match = re.match(
            r"(?:open|go to|visit)\s+"
            r"(https?://\S+|www\.\S+)$",
            raw,
            re.IGNORECASE
        )

        if match:

            return self.browser.open_url(
                match.group(1)
            )

        # =====================================================
        # YOUTUBE PLAY
        # =====================================================

        youtube_play_patterns = [

            r"^(?:please\s+)?play\s+(.+)$",

            r"^(?:please\s+)?listen\s+to\s+(.+)$",

            r"^(?:please\s+)?put\s+on\s+(.+)$",

            r"^(?:please\s+)?start\s+(.+)$",

        ]

        for pattern in youtube_play_patterns:

            match = re.match(
                pattern,
                raw,
                re.IGNORECASE
            )

            if not match:

                continue

            query = (
                match.group(1)
                .strip()
            )

            query = (
                self._clean_youtube_query(
                    query
                )
            )

            if not query:

                return (
                    "Which song or video "
                    "should I play?"
                )

            return (
                self.browser.play_youtube(
                    query
                )
            )

        # =====================================================
        # YOUTUBE SEARCH
        #
        # Search is deliberately AFTER play.
        #
        # "play Bairan on YouTube"
        # must NEVER become a search command.
        # =====================================================

        youtube_search_patterns = [

            r"^(?:search|find|look up)\s+"
            r"(?:for\s+)?"
            r"(.+?)\s+"
            r"(?:on|in)\s+youtube$",

            r"^search\s+youtube\s+for\s+(.+)$",

            r"^youtube\s+search\s+"
            r"(?:for\s+)?(.+)$",

        ]

        for pattern in youtube_search_patterns:

            match = re.match(
                pattern,
                command,
                re.IGNORECASE
            )

            if not match:
                continue

            query = (
                match.group(1)
                .strip()
            )

            if query:

                return (
                    self.browser.search_youtube(
                        query
                    )
                )

        # =====================================================
        # GENERIC SONG REQUEST
        # =====================================================

        generic_song = re.match(
            r"^(?:can you |could you |would you )?"
            r"(?:please )?"
            r"(?:play|put on|start)"
            r"(?:\s+(?:a|some|any))?"
            r"\s+(?:song|music|something)"
            r"(?:\s+for me)?$",
            command,
            re.IGNORECASE
        )

        if generic_song:

            return (
                "Sure. Tell me the name "
                "of the song or video "
                "you want to play."
            )

        # =====================================================
        # GOOGLE SEARCH
        # =====================================================

        google_patterns = [

            r"(?:search|find)\s+"
            r"(?:for\s+)?"
            r"(.+?)\s+"
            r"(?:in|on)\s+google$",

            r"google\s+search\s+"
            r"(?:for\s+)?(.+)$",

            r"search\s+google\s+for\s+(.+)$",

            r"google\s+(.+)$"

        ]

        for pattern in google_patterns:

            match = re.match(
                pattern,
                command,
                re.IGNORECASE
            )

            if match:

                query = (
                    match.group(1)
                    .strip()
                )

                if query:

                    return (
                        self.browser.search_google(
                            query
                        )
                    )

        # =====================================================
        # APPLICATIONS
        # =====================================================

        for key in sorted(
            self.apps.ALIASES,
            key=len,
            reverse=True
        ):

            open_pattern = (
                rf"^(?:open|launch|start|run)"
                rf"\s+{re.escape(key)}$"
            )

            if re.match(
                open_pattern,
                command
            ):

                return (
                    self.apps.open_app(
                        key
                    )
                )

            close_pattern = (
                rf"^(?:close|quit|exit|kill)"
                rf"\s+{re.escape(key)}$"
            )

            if re.match(
                close_pattern,
                command
            ):

                return (
                    self.apps.close_app(
                        key
                    )
                )

        # =====================================================
        # GENERIC APP OPEN
        # =====================================================

        match = re.match(
            r"^(?:open|launch|start|run)\s+(.+)$",
            raw,
            re.IGNORECASE
        )

        if match:

            target = (
                match.group(1)
                .strip()
            )

            if target.lower() not in {
                "a file",
                "something",
                "it"
            }:

                return (
                    self.apps.open_app(
                        target
                    )
                )

        # =====================================================
        # FOLDERS
        # =====================================================

        folder_map = {

            "downloads":
                os.path.join(
                    os.path.expanduser("~"),
                    "Downloads"
                ),

            "documents":
                os.path.join(
                    os.path.expanduser("~"),
                    "Documents"
                ),

            "desktop":
                os.path.join(
                    os.path.expanduser("~"),
                    "Desktop"
                ),

            "pictures":
                os.path.join(
                    os.path.expanduser("~"),
                    "Pictures"
                ),

            "music":
                os.path.join(
                    os.path.expanduser("~"),
                    "Music"
                ),

            "videos":
                os.path.join(
                    os.path.expanduser("~"),
                    "Videos"
                )

        }

        for name, path in folder_map.items():

            if command in {

                f"open {name}",

                f"go to {name}",

                f"open my {name}",

                f"go to my {name}"

            }:

                return (
                    self.files.open_path(
                        path
                    )
                )

        # =====================================================
        # CREATE FOLDER
        # =====================================================

        match = re.match(
            r"(?:create|make)\s+"
            r"(?:a\s+)?folder\s+"
            r"(?:called|named)?\s*(.+)$",
            raw,
            re.IGNORECASE
        )

        if match:

            return (
                self.files.create_folder(
                    match.group(1).strip()
                )
            )

        # =====================================================
        # LIST FILES
        # =====================================================

        match = re.match(
            r"(?:list|show)\s+"
            r"(?:the\s+)?files"
            r"(?:\s+in\s+(.+))?$",
            raw,
            re.IGNORECASE
        )

        if match:

            path = (
                match.group(1)
                or
                "."
            ).strip()

            return (
                self.files.list_directory(
                    path
                )
            )

        # =====================================================
        # SCREENSHOT
        # =====================================================

        if command in {

            "screenshot",
            "take a screenshot",
            "take screenshot",
            "capture screenshot"

        }:

            return (
                self.automation.screenshot()
            )

        # =====================================================
        # TYPE
        # =====================================================

        match = re.match(
            r"type\s+(.+)$",
            raw,
            re.IGNORECASE
        )

        if match:

            return (
                self.automation.type_text(
                    match.group(1)
                )
            )

        # =====================================================
        # PRESS KEY
        # =====================================================

        match = re.match(
            r"press\s+(.+)$",
            raw,
            re.IGNORECASE
        )

        if match:

            return (
                self.automation.press(
                    match.group(1).strip()
                )
            )

        # =====================================================
        # MEDIA
        #
        # Generic "play" remains here only when there is no
        # song/video target.
        #
        # YouTube play requests were already handled above.
        # =====================================================

        media = {

            "play":
                "play",

            "pause":
                "pause",

            "next":
                "next",

            "next track":
                "next",

            "previous":
                "previous",

            "previous track":
                "previous",

            "volume up":
                "volume up",

            "turn volume up":
                "volume up",

            "increase volume":
                "volume up",

            "volume down":
                "volume down",

            "turn volume down":
                "volume down",

            "decrease volume":
                "volume down",

            "mute":
                "mute",

            "mute volume":
                "mute"

        }

        if command in media:

            return (
                self.automation.media(
                    media[command]
                )
            )

        # =====================================================
        # WINDOWS
        # =====================================================

        if command in {

            "lock",
            "lock computer",
            "lock the computer",
            "lock my computer"

        }:

            return self.system.lock()

        if command in {

            "restart",
            "restart computer",
            "restart the computer"

        }:

            return self.system.restart()

        if command in {

            "shutdown",
            "shut down",
            "shutdown computer",
            "shut down computer"

        }:

            return self.system.shutdown()

        if command in {

            "cancel shutdown",
            "cancel restart",
            "cancel shutdown or restart"

        }:

            return self.system.cancel_shutdown()

        # =====================================================
        # SYSTEM INFORMATION
        # =====================================================

        if command in {

            "system info",
            "computer info",
            "computer specifications",
            "my computer specs",
            "pc specs"

        }:

            return (
                self.system_manager.get_system_info()
            )

        # =====================================================
        # WEB SEARCH
        # =====================================================

        match = re.match(
            r"(?:search the web for|"
            r"search online for|"
            r"look up online)\s+(.+)$",
            raw,
            re.IGNORECASE
        )

        if match:

            return (
                self.browser.search_google(
                    match.group(1).strip()
                )
            )

        # =====================================================
        # UNKNOWN
        # =====================================================

        return None